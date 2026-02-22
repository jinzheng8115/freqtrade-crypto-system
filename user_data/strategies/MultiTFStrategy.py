# 多时间框架策略
# 原理：用更高时间框架确认趋势，低时间框架入场
# 适合：趋势市场，减少假信号
from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class MultiTFStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # 参数
    ema_fast = IntParameter(5, 15, default=9, space="buy", optimize=True)
    ema_slow = IntParameter(20, 40, default=21, space="buy", optimize=True)
    
    minimal_roi = {"0": 0.10}
    stoploss = -0.05
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    
    startup_candle_count = 200
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    def informative_pairs(self):
        # 1小时时间框架用于趋势确认
        return [
            ("BTC/USDT", "1h"),
            ("ETH/USDT", "1h"),
            ("SOL/USDT", "1h"),
            ("DOGE/USDT", "1h"),
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 15m 指标
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        # 获取 1h 数据
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1h')
        
        if informative is not None and len(informative) > 0:
            # 1h 趋势
            informative['ema_50'] = ta.EMA(informative, timeperiod=50)
            informative['ema_200'] = ta.EMA(informative, timeperiod=200)
            last_1h = informative.iloc[-1]
            trend_up = last_1h['ema_50'] > last_1h['ema_200']
        else:
            trend_up = True  # 默认允许
        
        conditions = [
            # 15m EMA 多头
            dataframe['ema_fast'] > dataframe['ema_slow'],
            # RSI 不超买
            dataframe['rsi'] < 70,
            # ADX 有趋势
            dataframe['adx'] > 20,
            # 成交量
            dataframe['volume'] > dataframe['volume_ma'],
        ]
        
        if conditions and trend_up:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # EMA 死叉
            dataframe['ema_fast'] < dataframe['ema_slow'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
