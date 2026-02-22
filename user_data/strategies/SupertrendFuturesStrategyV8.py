# SupertrendFuturesStrategyV8 - 多因子温和版
# 基于V7.1验证结果，结合V4优势

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


class SupertrendFuturesStrategyV8(IStrategy):
    """
    V8: 多因子温和版
    
    结合V4的核心优势 + V7.1的多因子验证
    
    改进:
    1. 保持V4的核心趋势跟踪
    2. 添加Alpha#101温和过滤（已验证有效）
    3. RSI温和过滤（不极端）
    4. 成交量温和确认（1.2倍均值，不是1.5倍）
    
    目标:
    - 收益: 7-8%
    - 胜率: 65-67%
    - 回撤: 4-5%
    - 夏普: > 1.0
    """
    
    INTERFACE_VERSION = 3

    # V4最优参数
    atr_period = IntParameter(5, 30, default=11, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=2.884, space="buy")
    ema_fast = IntParameter(5, 50, default=48, space="buy")
    ema_slow = IntParameter(20, 200, default=151, space="buy")
    adx_threshold_long = IntParameter(20, 35, default=33, space="buy")
    adx_threshold_short = IntParameter(15, 30, default=23, space="buy")
    
    # V8新增参数
    alpha_threshold = DecimalParameter(0.05, 0.3, default=0.1, space="buy")  # Alpha#101阈值

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
        
        # === V8 新增：多因子指标 ===
        
        # 1. Alpha#101: 日内趋势强度（V7.1验证有效）
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
        
        # 4. 趋势强度评分
        dataframe['trend_score'] = 0
        dataframe.loc[dataframe['adx'] > 30, 'trend_score'] += 1
        dataframe.loc[dataframe['adx'] > 35, 'trend_score'] += 1
        dataframe.loc[abs(dataframe['alpha_54']) > 0.05, 'trend_score'] += 1
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - V8多因子温和版"""
        dataframe.loc[:, 'enter_long'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_long.value,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
            
            # === V8 温和多因子 ===
            
            # 1. RSI温和过滤（不极端）
            (dataframe['rsi'] > 40) & (dataframe['rsi'] < 75),
            
            # 2. Alpha#101温和过滤（V7.1验证有效）
            dataframe['alpha_101'] > self.alpha_threshold.value,
            
            # 3. 成交量温和确认（1.2倍均值，不是1.5倍）
            dataframe['volume'] > dataframe['volume_ma'] * 1.2,
            
            # 4. 趋势强度评分（至少1分）
            dataframe['trend_score'] >= 1,
            
            # 5. 波动率正常（非极端）
            dataframe['volatility_ratio'] < 0.05,
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
        """做空 - V8多因子温和版"""
        dataframe.loc[:, 'enter_short'] = 0

        conditions = [
            # === V4 核心条件 ===
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_short.value,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
            
            # === V8 温和多因子 ===
            (dataframe['rsi'] > 25) & (dataframe['rsi'] < 60),
            dataframe['alpha_101'] < -self.alpha_threshold.value,
            dataframe['volume'] > dataframe['volume_ma'] * 1.2,
            dataframe['trend_score'] >= 1,
            dataframe['volatility_ratio'] < 0.05,
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


# === 预期表现 ===
"""
基于V4和V7.1的组合:

V4 (当前最优):
- 收益: +7.47%
- 胜率: 63.6%
- 回撤: 5.35%

V7.1 (已验证):
- 收益: +6.44%
- 胜率: 63.6%
- 回撤: 3.79%
- 夏普: 1.17

V8 (预期):
- 收益: 7-8% (V4基础 + V7.1风险控制)
- 胜率: 65-67% (温和过滤提升)
- 回撤: 4-5% (V7.1经验)
- 夏普: > 1.0

关键改进:
1. Alpha#101温和过滤（已验证提升夏普）
2. RSI温和范围（避免极端）
3. 趋势评分（信号质量提升）
4. 波动率控制（降低风险）
"""
