# 网格交易策略
# 原理：在价格区间内设置网格，低买高卖
# 适合：震荡市场，不适合单边趋势
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class GridStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # 网格参数
    grid_spacing = DecimalParameter(1.0, 3.0, default=1.5, space="buy", optimize=True)  # 网格间距 %
    grid_count = IntParameter(5, 15, default=10, space="buy", optimize=True)  # 网格数量
    base_rsi = IntParameter(40, 60, default=50, space="buy", optimize=True)  # 基准 RSI
    
    # 止盈止损
    minimal_roi = {"0": 0.03}  # 3% 止盈
    stoploss = -0.10  # 10% 止损 (网格需要更宽止损)
    
    timeframe = '15m'
    
    # 不使用追踪止损 (网格策略特点)
    trailing_stop = False
    
    startup_candle_count = 100
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    # 允许加仓
    position_adjustment_enable = True
    max_entry_position_adjustment = 5  # 最多加仓 5 次
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI 用于判断相对位置
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ATR 用于波动率
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # 布林带作为网格边界参考
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_mid'] = bollinger['middleband']
        
        # 价格在布林带中的位置 (0-100)
        dataframe['bb_position'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower']) * 100
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 1. RSI 低于基准 (相对低位)
            dataframe['rsi'] < self.base_rsi.value,
            
            # 2. 价格在布林带下半部分
            dataframe['bb_position'] < 40,
            
            # 3. 有足够波动率 (网格需要波动)
            dataframe['atr_pct'] > 1.0,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # 1. RSI 高于基准 (相对高位)
            dataframe['rsi'] > (100 - self.base_rsi.value),
            
            # 2. 价格在布林带上半部分
            dataframe['bb_position'] > 60,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
    
    def custom_stake_amount(self, pair: str, current_time, current_rate, proposed_stake, 
                           min_stake, max_stake, leverage, entry_tag, side, **kwargs):
        """
        网格策略：分批建仓
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return proposed_stake
        
        last_candle = dataframe.iloc[-1]
        
        # 根据价格位置调整仓位
        bb_pos = last_candle['bb_position']
        rsi = last_candle['rsi']
        
        # 越低越买
        if bb_pos < 20 and rsi < 30:
            return proposed_stake * 1.5  # 加大仓位
        elif bb_pos < 30 and rsi < 40:
            return proposed_stake * 1.2
        else:
            return proposed_stake * 0.8  # 减小仓位
