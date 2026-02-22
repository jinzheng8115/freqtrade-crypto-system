# SupertrendFuturesStrategyV7_1 - 温和多因子版
# 更新时间: 2026-02-22 13:10
# 基于: V4 (30m 周期，+7.47% 收益)
# 优化: 温和多因子确认（放宽条件）

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from functools import reduce
import logging

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from freqtrade.persistence import Trade
import talib.abstract as ta

logger = logging.getLogger(__name__)


class SupertrendFuturesStrategyV7_1(IStrategy):
    """
    Supertrend + EMA 趋势跟踪策略 (合约版 V7.1)
    
    V7.1 优化 (2026-02-22):
    - 基于 V4 (最优版本)
    - ✅ WorldQuant Alpha 因子（温和版）:
      - Alpha#101: 日内趋势强度（放宽阈值）
    - ✅ RSI 过滤加强（70 → 75）
    - ❌ 移除过度过滤:
      - 移除 Alpha#4, Alpha#6（太严格）
      - 移除 Turbulence（太严格）
    
    目标: 在保持交易频率的同时提升胜率
    """
    
    INTERFACE_VERSION = 3

    # 参数 - 保持 V4 最优参数
    atr_period = IntParameter(5, 30, default=11, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=2.884, space="buy")
    ema_fast = IntParameter(5, 50, default=48, space="buy")
    ema_slow = IntParameter(20, 200, default=151, space="buy")

    # ADX 参数
    adx_threshold_long = IntParameter(20, 35, default=33, space="buy")
    adx_threshold_short = IntParameter(15, 30, default=23, space="buy")
    
    # Alpha 因子参数 - 放宽
    alpha_101_threshold = DecimalParameter(0.0, 0.3, default=0.1, space="buy")  # V7: 0.2 → 0.1
    
    # RSI 参数 - 放宽
    rsi_upper_limit = IntParameter(65, 80, default=75, space="buy")  # V4: 70 → 75
    rsi_lower_limit = IntParameter(20, 35, default=25, space="buy")  # V4: 30 → 25

    minimal_roi = {"0": 0.06}
    stoploss = -0.03

    timeframe = '30m'

    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    startup_candle_count = 200

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    can_short: bool = True
    leverage_default = 2

    def supertrend(self, dataframe, period=14, multiplier=3):
        df = dataframe.copy()
        hl2 = (df['high'] + df['low']) / 2
        atr = ta.ATR(df, timeperiod=period)
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)
        supertrend = [0] * len(df)
        direction = [1] * len(df)
        for i in range(1, len(df)):
            if df['close'].iloc[i] > upperband.iloc[i-1]:
                direction[i] = 1
            elif df['close'].iloc[i] < lowerband.iloc[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
            supertrend[i] = lowerband.iloc[i] if direction[i] == 1 else upperband.iloc[i]
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        return min(self.leverage_default, max_leverage)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 现有指标
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value
        )
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_pos'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['adx_neg'] = ta.MINUS_DI(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['is_uptrend'] = dataframe['close'] > dataframe['ema_200']
        dataframe['is_downtrend'] = dataframe['close'] < dataframe['ema_200']
        
        # Alpha#101: 日内趋势强度
        dataframe['alpha_101'] = (dataframe['close'] - dataframe['open']) / (dataframe['high'] - dataframe['low'] + 0.001)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        做多 - V7.1 温和多因子版
        
        V4 条件 (8个):
        1. Supertrend 方向向上
        2. EMA 快线 > 慢线
        3. ADX > 33
        4. ADX+ > ADX-
        5. RSI < 70 → 75 (放宽)
        6. 成交量 > 均值
        7. 价格 > Supertrend
        8. 大趋势向上
        
        V7.1 新增 (1个):
        9. Alpha#101 > 0.1 (温和阈值)
        """
        dataframe.loc[:, 'enter_long'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_long.value,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            dataframe['rsi'] < self.rsi_upper_limit.value,  # 放宽到 75
            dataframe['rsi'] > 20,
            dataframe['volume'] > dataframe['volume_ma'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
            
            # === V7.1 Alpha 因子（温和）===
            dataframe['alpha_101'] > self.alpha_101_threshold.value,  # 放宽到 0.1
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        conditions = [dataframe['st_dir'] == -1]
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        return dataframe

    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        做空 - V7.1 温和多因子版
        """
        dataframe.loc[:, 'enter_short'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_short.value,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            dataframe['rsi'] > self.rsi_lower_limit.value,  # 放宽到 25
            dataframe['rsi'] < 80,
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
            
            # === V7.1 Alpha 因子（温和）===
            dataframe['alpha_101'] < -self.alpha_101_threshold.value,  # 放宽到 -0.1
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1

        return dataframe

    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_short'] = 0
        conditions = [dataframe['st_dir'] == 1]
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_short'] = 1
        return dataframe
