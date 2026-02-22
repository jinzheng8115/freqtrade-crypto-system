# SupertrendFuturesStrategyV5_2 - 保守优化版
# 优化：
# 1. 多时间框架趋势（仅用于确认，不强制要求）
# 2. 动态止损（ATR 倍数）
# 3. 更严格的信号强度（5分制，需>=4分）
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from functools import reduce

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta


class SupertrendFuturesStrategyV5_2(IStrategy):
    INTERFACE_VERSION = 3
    
    # 基础参数
    atr_period = IntParameter(10, 30, default=14, space="buy")
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy")
    ema_fast = IntParameter(5, 20, default=9, space="buy")
    ema_slow = IntParameter(20, 50, default=21, space="buy")
    
    minimal_roi = {"0": 0.06}
    stoploss = -0.07  # 7% 固定止损
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.035
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
        # === 基础指标 ===
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Supertrend
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value
        )
        
        # 动量指标
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        
        # 波动率
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = dataframe['atr'] / dataframe['close'] * 100
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # 趋势判断
        dataframe['is_uptrend'] = dataframe['close'] > dataframe['ema_200']
        dataframe['is_downtrend'] = dataframe['close'] < dataframe['ema_200']
        
        # === 信号强度评分 (更严格) ===
        # 做多评分 (满分5分，需要4分)
        long_score = 0
        long_score += (dataframe['st_dir'] == 1).astype(int) * 1  # 1分
        long_score += (dataframe['ema_fast'] > dataframe['ema_slow']).astype(int) * 1  # 1分
        long_score += (dataframe['adx'] > 20).astype(int) * 1  # 1分
        long_score += (dataframe['rsi'] < 65).astype(int) * 1  # 1分（更严格）
        long_score += (dataframe['volume_ratio'] > 1.2).astype(int) * 1  # 1分（更严格）
        
        dataframe['long_score'] = long_score
        
        # 做空评分 (满分5分，需要3分，放宽)
        short_score = 0
        short_score += (dataframe['st_dir'] == -1).astype(int) * 1
        short_score += (dataframe['ema_fast'] < dataframe['ema_slow']).astype(int) * 1
        short_score += (dataframe['adx'] > 15).astype(int) * 1
        short_score += (dataframe['rsi'] > 35).astype(int) * 1
        short_score += (dataframe['volume_ratio'] > 1.0).astype(int) * 1
        
        dataframe['short_score'] = short_score
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - 需要4分 + 趋势确认"""
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            dataframe['long_score'] >= 4,  # 至少4分
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],  # 必须在上涨趋势
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
        """做空 - 需要3分"""
        dataframe.loc[:, 'enter_short'] = 0
        
        conditions = [
            dataframe['short_score'] >= 3,
            dataframe['close'] < dataframe['supertrend'],
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
