# 组合策略 - 多指标确认
# 结合 Supertrend + RSI + ADX + 成交量
# 只有多个指标同时确认才入场
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
import numpy as np
from functools import reduce

class CombinedStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # Supertrend 参数
    atr_period = IntParameter(10, 30, default=14, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy", optimize=True)
    
    # RSI 参数
    rsi_period = IntParameter(10, 20, default=14, space="buy", optimize=True)
    rsi_lower = IntParameter(25, 40, default=35, space="buy", optimize=True)
    rsi_upper = IntParameter(60, 75, default=65, space="sell", optimize=True)
    
    # ADX 参数
    adx_threshold = IntParameter(20, 35, default=25, space="buy", optimize=True)
    
    minimal_roi = {"0": 0.08}
    stoploss = -0.05
    
    timeframe = '15m'
    
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
            
            if direction[i] == 1:
                supertrend[i] = lowerband.iloc[i]
            else:
                supertrend[i] = upperband.iloc[i]
        
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Supertrend
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value
        )
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        
        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        
        # EMA
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 1. Supertrend 看涨
            dataframe['st_dir'] == 1,
            
            # 2. RSI 不超买
            dataframe['rsi'] < self.rsi_upper.value,
            
            # 3. ADX 显示趋势
            dataframe['adx'] > self.adx_threshold.value,
            
            # 4. 成交量确认
            dataframe['volume'] > dataframe['volume_ma'] * 1.1,
            
            # 5. 价格在 EMA50 之上
            dataframe['close'] > dataframe['ema_50'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # Supertrend 转空 OR RSI 超买
            (dataframe['st_dir'] == -1) | (dataframe['rsi'] > 75),
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_long'] = 1
        
        return dataframe
