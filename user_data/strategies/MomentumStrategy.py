# 动量策略 - Momentum + RSI
# 原理：动量向上且 RSI 确认时买入
# 适合：趋势启动阶段
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class MomentumStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # 参数
    momentum_period = IntParameter(5, 15, default=10, space="buy", optimize=True)
    rsi_threshold = IntParameter(50, 70, default=60, space="buy", optimize=True)
    
    minimal_roi = {"0": 0.08}
    stoploss = -0.05
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.035
    
    startup_candle_count = 100
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Momentum
        dataframe['momentum'] = ta.MOM(dataframe, timeperiod=self.momentum_period.value)
        dataframe['momentum_ma'] = ta.SMA(dataframe['momentum'], timeperiod=10)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ROC (Rate of Change)
        dataframe['roc'] = ta.ROC(dataframe, timeperiod=10)
        
        # Volume
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 动量向上
            dataframe['momentum'] > 0,
            dataframe['momentum'] > dataframe['momentum_ma'],
            # RSI 确认
            dataframe['rsi'] > 50,
            dataframe['rsi'] < self.rsi_threshold.value,
            # 成交量
            dataframe['volume'] > dataframe['volume_ma'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # 动量转负
            dataframe['momentum'] < 0,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
