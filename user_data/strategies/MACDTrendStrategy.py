# MACD 趋势策略
# 原理：MACD 金叉买入，死叉卖出
# 适合：趋势市场
from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class MACDTrendStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # 可优化参数
    macd_fast = IntParameter(8, 16, default=12, space="buy", optimize=True)
    macd_slow = IntParameter(20, 30, default=26, space="buy", optimize=True)
    macd_signal = IntParameter(7, 12, default=9, space="buy", optimize=True)
    
    # 止盈止损
    minimal_roi = {"0": 0.10}
    stoploss = -0.06
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True
    
    startup_candle_count = 100
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        macd = ta.MACD(dataframe, fastperiod=self.macd_fast.value, slowperiod=self.macd_slow.value, signalperiod=self.macd_signal.value)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # MACD 金叉
            dataframe['macd'] > dataframe['macd_signal'],
            dataframe['macd'].shift(1) <= dataframe['macd_signal'].shift(1),
            # MACD 在零轴上方更佳
            dataframe['macd'] > 0,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # MACD 死叉
            dataframe['macd'] < dataframe['macd_signal'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
