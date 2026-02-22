# SupertrendFuturesStrategyV5_1 - 平衡优化版
# 更新时间: 2026-02-22 12:00
# 优化数据: 90 天 30m 数据
# 改进: 放宽过滤、延后止盈、平衡动态仓位

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


class SupertrendFuturesStrategyV5_1(IStrategy):
    """
    Supertrend + EMA 趋势跟踪策略 (合约版 V5.1)
    
    V5.1 优化 (2026-02-22):
    - 基于 V5 回测反馈调整
    - 放宽 RSI 过滤 (70→75, 30→25)
    - 调整动态仓位阈值 (更容易正常仓位)
    - 延后止盈 (3%→5%, 5%→8%, 10%→15%)
    
    目标：
    - 保持胜率 (68%+)
    - 提升收益 (目标 10%+)
    - 降低回撤 (目标 <8%)
    """
    
    INTERFACE_VERSION = 3

    # 参数 - 30m 优化后
    atr_period = IntParameter(5, 30, default=11, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=2.884, space="buy")
    ema_fast = IntParameter(5, 50, default=48, space="buy")
    ema_slow = IntParameter(20, 200, default=151, space="buy")

    # ADX 参数
    adx_threshold_long = IntParameter(20, 35, default=33, space="buy")
    adx_threshold_short = IntParameter(15, 30, default=23, space="buy")
    
    # RSI 参数 - 放宽
    rsi_upper_limit = IntParameter(65, 80, default=75, space="buy")  # V5: 70 → 75
    rsi_lower_limit = IntParameter(20, 35, default=25, space="buy")  # V5: 30 → 25
    
    # 止盈参数 - 延后
    tp_level_1 = DecimalParameter(0.03, 0.07, default=0.05, space="sell")  # V5: 3% → 5%
    tp_level_2 = DecimalParameter(0.06, 0.10, default=0.08, space="sell")  # V5: 5% → 8%
    tp_level_3 = DecimalParameter(0.10, 0.20, default=0.15, space="sell")  # V5: 10% → 15%
    
    # 动态仓位参数 - 调整
    atr_low_threshold = DecimalParameter(0.015, 0.035, default=0.025, space="buy")   # V5: 0.03 → 0.025
    atr_high_threshold = DecimalParameter(0.045, 0.07, default=0.06, space="buy")    # V5: 0.05 → 0.06

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
        dataframe['atr_ratio'] = dataframe['atr'] / dataframe['close']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0

        conditions = [
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_long.value,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            # RSI 放宽到 75
            dataframe['rsi'] < self.rsi_upper_limit.value,
            dataframe['rsi'] > 20,
            dataframe['volume'] > dataframe['volume_ma'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
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
        dataframe.loc[:, 'enter_short'] = 0

        conditions = [
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_short.value,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            # RSI 放宽到 25
            dataframe['rsi'] > self.rsi_lower_limit.value,
            dataframe['rsi'] < 80,
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
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
    
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: Optional[float], max_stake: float,
                           entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        动态仓位管理 - 调整后
        
        更容易使用正常仓位:
        - 高波动 (ATR > 6%) → 小仓位 (60%)
        - 中波动 (ATR 2.5-6%) → 中仓位 (80%)
        - 低波动 (ATR < 2.5%) → 正常仓位 (100%)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return proposed_stake
        
        atr_ratio = dataframe['atr_ratio'].iloc[-1]
        
        if atr_ratio > self.atr_high_threshold.value:
            stake = proposed_stake * 0.6  # V5: 0.5 → 0.6
        elif atr_ratio > self.atr_low_threshold.value:
            stake = proposed_stake * 0.8  # V5: 0.75 → 0.8
        else:
            stake = proposed_stake
        
        if min_stake is not None and stake < min_stake:
            return min_stake
        
        return stake
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, 
                   current_rate: float, current_profit: float, **kwargs) -> Optional[str]:
        """
        分批止盈 - 延后版
        
        让利润跑更远:
        - 5% 利润 → 部分止盈
        - 8% 利润 → 加速止盈
        - 15% 利润 → 全部平仓
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return None
        
        profit_pct = current_profit
        
        # 延后止盈
        if profit_pct >= self.tp_level_3.value:
            return f'profit_{int(self.tp_level_3.value*100)}pct'
        elif profit_pct >= self.tp_level_2.value:
            return f'profit_{int(self.tp_level_2.value*100)}pct'
        elif profit_pct >= self.tp_level_1.value:
            return f'profit_{int(self.tp_level_1.value*100)}pct'
        
        # RSI 反转信号
        last_candle = dataframe.iloc[-1]
        if trade.is_short:
            if last_candle['rsi'] < 25:  # V5: 30 → 25
                return 'rsi_oversold_exit'
        else:
            if last_candle['rsi'] > 75:  # V5: 70 → 75
                return 'rsi_overbought_exit'
        
        return None
