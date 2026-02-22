# SupertrendFuturesStrategyV3 - 合约优化版
# 改进：降低做空门槛，让多空更平衡
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from functools import reduce

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta


class SupertrendFuturesStrategyV3(IStrategy):
    INTERFACE_VERSION = 3
    
    # 参数
    atr_period = IntParameter(10, 30, default=14, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy", optimize=True)
    ema_fast = IntParameter(5, 20, default=9, space="buy", optimize=True)
    ema_slow = IntParameter(20, 50, default=21, space="buy", optimize=True)
    
    # 做多条件（稍严格）
    adx_long = IntParameter(20, 30, default=22, space="buy", optimize=True)
    rsi_long_max = IntParameter(65, 75, default=68, space="buy", optimize=True)
    
    # 做空条件（放宽）
    adx_short = IntParameter(12, 20, default=15, space="buy", optimize=True)  # 降低ADX要求
    rsi_short_min = IntParameter(25, 40, default=35, space="sell", optimize=True)  # 放宽RSI
    
    minimal_roi = {"0": 0.08}
    stoploss = -0.05  # 5%止损
    
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
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value
        )
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        # 价格变化率
        dataframe['price_change'] = dataframe['close'].pct_change()
        dataframe['price_change_ma'] = dataframe['price_change'].rolling(10).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - 稍严格"""
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_long.value,
            dataframe['rsi'] < self.rsi_long_max.value,
            dataframe['volume'] > dataframe['volume_ma'],
            dataframe['close'] > dataframe['supertrend'],
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
        """做空 - 放宽条件"""
        dataframe.loc[:, 'enter_short'] = 0
        
        conditions = [
            # 1. Supertrend 看空
            dataframe['st_dir'] == -1,
            
            # 2. EMA 空头 OR 价格下跌趋势
            (dataframe['ema_fast'] < dataframe['ema_slow']) | (dataframe['price_change_ma'] < 0),
            
            # 3. ADX 较低即可（放宽）
            dataframe['adx'] > self.adx_short.value,
            
            # 4. RSI > 35 (放宽)
            dataframe['rsi'] > self.rsi_short_min.value,
            
            # 5. 价格在 Supertrend 之下
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
