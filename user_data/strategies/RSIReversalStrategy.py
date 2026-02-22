# RSI 均值回归策略
# 原理：RSI 超卖买入，超买卖出
# 适合：震荡市场
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class RSIReversalStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # 可优化参数
    rsi_period = IntParameter(7, 21, default=14, space="buy", optimize=True)
    rsi_oversold = IntParameter(20, 35, default=30, space="buy", optimize=True)
    rsi_overbought = IntParameter(65, 80, default=70, space="sell", optimize=True)
    
    # 止盈止损
    minimal_roi = {"0": 0.06}
    stoploss = -0.05
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.035
    trailing_only_offset_is_reached = True
    
    startup_candle_count = 100
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        dataframe['rsi_ma'] = ta.SMA(dataframe['rsi'], timeperiod=14)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # RSI 超卖反弹
            dataframe['rsi'] < self.rsi_oversold.value,
            # RSI 开始上升
            dataframe['rsi'] > dataframe['rsi'].shift(1),
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            dataframe['rsi'] > self.rsi_overbought.value,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
