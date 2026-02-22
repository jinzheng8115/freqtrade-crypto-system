# SupertrendFuturesStrategyV4_1 - 市场环境优化版
# 基于Walk-Forward验证发现，添加市场环境识别

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


class SupertrendFuturesStrategyV4_1(IStrategy):
    """
    Supertrend + EMA 趋势跟踪策略 (合约版 V4.1)
    
    V4.1 优化 (2026-02-22):
    - 基于 Walk-Forward 验证发现
    - ✅ 添加市场环境识别
    - ✅ 避免 Segment 2 类型的市场环境
    
    改进:
    1. 计算市场环境评分
    2. 评分 < 0 时暂停交易
    3. 高波动 + 弱趋势 → 不交易
    """
    
    INTERFACE_VERSION = 3

    # 参数 - 保持 V4 最优参数
    atr_period = IntParameter(5, 30, default=11, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=2.884, space="buy")
    ema_fast = IntParameter(5, 50, default=48, space="buy")
    ema_slow = IntParameter(20, 200, default=151, space="buy")
    adx_threshold_long = IntParameter(20, 35, default=33, space="buy")
    adx_threshold_short = IntParameter(15, 30, default=23, space="buy")

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
        
        # === V4.1 新增：市场环境指标 ===
        
        # 1. 波动率 (20日)
        dataframe['volatility_20d'] = dataframe['close'].pct_change().rolling(20).std()
        
        # 2. 波动率状态
        dataframe['volatility_state'] = 'medium'
        dataframe.loc[dataframe['volatility_20d'] < 0.02, 'volatility_state'] = 'low'
        dataframe.loc[dataframe['volatility_20d'] > 0.04, 'volatility_state'] = 'high'
        dataframe.loc[dataframe['volatility_20d'] > 0.06, 'volatility_state'] = 'extreme'
        
        # 3. 趋势强度状态
        dataframe['trend_state'] = 'weak'
        dataframe.loc[dataframe['adx'] > 25, 'trend_state'] = 'moderate'
        dataframe.loc[dataframe['adx'] > 35, 'trend_state'] = 'strong'
        
        # 4. 市场环境评分
        # +1: low/medium 波动率
        # -1: high/extreme 波动率
        # +1: moderate/strong 趋势
        # -1: weak 趋势
        dataframe['regime_score'] = 0
        
        # 波动率评分
        dataframe.loc[dataframe['volatility_state'].isin(['low', 'medium']), 'regime_score'] += 1
        dataframe.loc[dataframe['volatility_state'].isin(['high', 'extreme']), 'regime_score'] -= 1
        
        # 趋势评分
        dataframe.loc[dataframe['trend_state'].isin(['moderate', 'strong']), 'regime_score'] += 1
        dataframe.loc[dataframe['trend_state'] == 'weak', 'regime_score'] -= 1
        
        # 5. 是否可以交易
        # 评分 >= 0 可以交易
        # 评分 < 0 暂停交易
        dataframe['can_trade'] = dataframe['regime_score'] >= 0
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - 添加市场环境过滤"""
        dataframe.loc[:, 'enter_long'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_long.value,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            dataframe['rsi'] < 70,
            dataframe['volume'] > dataframe['volume_ma'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
            
            # === V4.1 新增：市场环境过滤 ===
            dataframe['can_trade'],  # 市场环境评分 >= 0
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
        """做空 - 添加市场环境过滤"""
        dataframe.loc[:, 'enter_short'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_short.value,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            dataframe['rsi'] > 30,
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
            
            # === V4.1 新增：市场环境过滤 ===
            dataframe['can_trade'],  # 市场环境评分 >= 0
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
