# 突破策略 - Donchian Channel
# 原理：价格突破 N 日高点买入，跌破 N 日低点卖出
# 适合：趋势市场
from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class BreakoutStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # 突破周期
    breakout_period = IntParameter(10, 30, default=20, space="buy", optimize=True)
    
    minimal_roi = {"0": 0.10}
    stoploss = -0.05
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    
    startup_candle_count = 100
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        period = self.breakout_period.value
        
        # Donchian Channel
        dataframe['don_high'] = dataframe['high'].rolling(period).max()
        dataframe['don_low'] = dataframe['low'].rolling(period).min()
        dataframe['don_mid'] = (dataframe['don_high'] + dataframe['don_low']) / 2
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # Volume
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 价格突破上轨
            dataframe['close'] > dataframe['don_high'].shift(1),
            # 成交量确认
            dataframe['volume'] > dataframe['volume_ma'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # 价格跌破下轨
            dataframe['close'] < dataframe['don_low'].shift(1),
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
