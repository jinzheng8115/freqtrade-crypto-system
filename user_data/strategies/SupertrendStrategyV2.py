# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# isort: skip_file
"""
Supertrend V2 策略 - 优化版
改进点：
1. 收紧入场条件，减少假信号
2. 添加 ADX 趋势强度过滤
3. 成交量确认加强
4. 动态 ATR 止损
"""
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union
from functools import reduce

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta


class SupertrendStrategyV2(IStrategy):
    """
    Supertrend V2 - 优化版趋势跟踪策略
    """
    
    INTERFACE_VERSION = 3
    
    # 可优化参数
    atr_period = IntParameter(10, 30, default=28, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.936, space="buy", optimize=True)
    ema_fast = IntParameter(5, 20, default=17, space="buy", optimize=True)
    ema_slow = IntParameter(20, 50, default=49, space="buy", optimize=True)
    rsi_threshold = IntParameter(60, 80, default=70, space="buy", optimize=True)
    adx_threshold = IntParameter(15, 35, default=20, space="buy", optimize=True)  # 放宽到 20
    
    # 止盈 - 更保守
    minimal_roi = {
        "0": 0.10,     # 10% 即时止盈
    }
    
    # 止损 - 稍微放宽
    stoploss = -0.06  # 6%
    
    # 时间框架
    timeframe = '15m'
    
    # 追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    
    startup_candle_count = 200
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC'
    }
    
    use_exit_signal = True
    exit_profit_only = False
    
    def informative_pairs(self):
        return []
    
    def supertrend(self, dataframe, period=14, multiplier=3):
        """计算 Supertrend 指标"""
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
            
            if direction[i] == 1:
                supertrend[i] = lowerband.iloc[i]
            else:
                supertrend[i] = upperband.iloc[i]
        
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA 趋势
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        
        # Supertrend
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, 
            period=self.atr_period.value, 
            multiplier=self.atr_multiplier.value
        )
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ADX - 趋势强度
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # 成交量均线
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 1. Supertrend 看涨
            dataframe['st_dir'] == 1,
            
            # 2. EMA 多头排列
            dataframe['ema_fast'] > dataframe['ema_slow'],
            
            # 3. ADX > 25 (有趋势)
            dataframe['adx'] > self.adx_threshold.value,
            
            # 4. RSI < 70 (不追高)
            dataframe['rsi'] < self.rsi_threshold.value,
            
            # 5. 成交量 > 平均 (放宽到 1.0)
            dataframe['volume'] > dataframe['volume_ma'],
            
            # 6. 价格在 Supertrend 之上
            dataframe['close'] > dataframe['supertrend'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # Supertrend 转空
            dataframe['st_dir'] == -1,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
