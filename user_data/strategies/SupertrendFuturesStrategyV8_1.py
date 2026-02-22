# SupertrendFuturesStrategyV8_1 - 交易频率优化版
# 基于V8，适度放宽过滤条件

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from functools import reduce
import logging

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta

logger = logging.getLogger(__name__)


class SupertrendFuturesStrategyV8_1(IStrategy):
    """
    V8.1: 交易频率优化版
    
    基于V8，适度放宽过滤条件：
    
    V8问题：
    - 交易次数从55降到36 (-35%)
    - 过滤条件过严
    
    V8.1调整：
    1. Alpha#101阈值: 0.1 → 0.05 (更宽松)
    2. RSI范围: 40-75 → 35-80 (更宽松)
    3. 成交量确认: 1.2倍 → 1.1倍 (更宽松)
    4. 趋势评分: >= 1分 → >= 0分 (移除)
    5. 波动率控制: < 0.05 → < 0.06 (更宽松)
    
    目标:
    - 交易次数: 36 → 50+ (接近V4的55)
    - 收益: 保持8%+
    - 胜率: 保持65%+
    """
    
    INTERFACE_VERSION = 3

    # V4最优参数
    atr_period = IntParameter(5, 30, default=11, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=2.884, space="buy")
    ema_fast = IntParameter(5, 50, default=48, space="buy")
    ema_slow = IntParameter(20, 200, default=151, space="buy")
    adx_threshold_long = IntParameter(20, 35, default=33, space="buy")
    adx_threshold_short = IntParameter(15, 30, default=23, space="buy")
    
    # V8.1优化参数
    alpha_threshold = DecimalParameter(0.02, 0.15, default=0.05, space="buy")  # V8: 0.1

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
        # === V4 核心指标 ===
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
        
        # === V8.1 优化指标 ===
        
        # 1. Alpha#101: 日内趋势强度
        dataframe['alpha_101'] = (
            (dataframe['close'] - dataframe['open']) / 
            (dataframe['high'] - dataframe['low'] + 0.001)
        )
        
        # 2. Alpha#54: 收益动量
        dataframe['alpha_54'] = (
            (dataframe['close'] - dataframe['close'].shift(5)) / 
            dataframe['close'].shift(5)
        )
        
        # 3. 波动率标准化
        dataframe['volatility_ratio'] = (
            dataframe['atr'] / dataframe['close']
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - V8.1频率优化版"""
        dataframe.loc[:, 'enter_long'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_long.value,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
            
            # === V8.1 宽松多因子 ===
            
            # 1. RSI范围放宽 (V8: 40-75 → V8.1: 35-80)
            (dataframe['rsi'] > 35) & (dataframe['rsi'] < 80),
            
            # 2. Alpha#101阈值降低 (V8: 0.1 → V8.1: 0.05)
            dataframe['alpha_101'] > self.alpha_threshold.value,
            
            # 3. 成交量确认降低 (V8: 1.2倍 → V8.1: 1.1倍)
            dataframe['volume'] > dataframe['volume_ma'] * 1.1,
            
            # 4. 波动率控制放宽 (V8: 0.05 → V8.1: 0.06)
            dataframe['volatility_ratio'] < 0.06,
            
            # 5. 移除趋势评分要求 (V8: >= 1分 → V8.1: 移除)
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
        """做空 - V8.1频率优化版"""
        dataframe.loc[:, 'enter_short'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_short.value,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
            
            # === V8.1 宽松多因子 ===
            (dataframe['rsi'] > 20) & (dataframe['rsi'] < 65),
            dataframe['alpha_101'] < -self.alpha_threshold.value,
            dataframe['volume'] > dataframe['volume_ma'] * 1.1,
            dataframe['volatility_ratio'] < 0.06,
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


# === 调整说明 ===
"""
V8.1 vs V8 过滤条件对比:

指标                V8        V8.1      变化
----------------------------------------------------
Alpha#101阈值      0.1       0.05      放宽50%
RSI范围           40-75     35-80      扩大10%
成交量确认        1.2倍     1.1倍      降低8%
波动率控制        0.05      0.06       放宽20%
趋势评分          >= 1分    移除       完全移除

预期效果:
- 交易次数: 36 → 50+ (接近V4的55)
- 收益: 保持8%+
- 胜率: 65%+ (略低于V8的69.4%)
- 回撤: 保持5%以内

目标:
保持V8的优势（收益高、风险低），同时提升交易频率
"""
