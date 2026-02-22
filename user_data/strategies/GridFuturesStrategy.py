# 双向网格策略 (合约)
# 支持做多和做空，适合震荡市场
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class GridFuturesStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # 网格参数
    grid_spacing = DecimalParameter(0.5, 2.0, default=1.0, space="buy", optimize=True)
    base_rsi = IntParameter(45, 55, default=50, space="buy", optimize=True)
    
    # 止盈止损
    minimal_roi = {"0": 0.025}  # 2.5% 快速止盈
    stoploss = -0.05  # 5% 止损
    
    timeframe = '15m'
    
    trailing_stop = False
    
    startup_candle_count = 100
    
    can_short: bool = True
    leverage_default = 1  # 网格策略降低杠杆
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, 
                 entry_tag, side, **kwargs):
        return min(self.leverage_default, max_leverage)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # 布林带
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_mid'] = bollinger['middleband']
        dataframe['bb_position'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower']) * 100
        
        # EMA 趋势
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多：价格在低位"""
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            dataframe['rsi'] < 40,
            dataframe['bb_position'] < 30,
            dataframe['atr_pct'] > 0.8,  # 有波动
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多平仓"""
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            dataframe['rsi'] > 60,
            dataframe['bb_position'] > 50,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
    
    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空：价格在高位"""
        dataframe.loc[:, 'enter_short'] = 0
        
        conditions = [
            dataframe['rsi'] > 60,
            dataframe['bb_position'] > 70,
            dataframe['atr_pct'] > 0.8,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空平仓"""
        dataframe.loc[:, 'exit_short'] = 0
        
        conditions = [
            dataframe['rsi'] < 40,
            dataframe['bb_position'] < 50,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_short'] = 1
        
        return dataframe
