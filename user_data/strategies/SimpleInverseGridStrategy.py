# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, DecimalParameter
import talib.abstract as ta
from functools import reduce


class SimpleInverseGridStrategy(IStrategy):
    """
    简化版合约反向网格策略
    
    做空逻辑：价格下跌时做空
    平仓逻辑：反弹时止盈
    """
    
    INTERFACE_VERSION = 3
    
    # 参数
    grid_spacing = DecimalParameter(0.003, 0.01, default=0.005, space="buy")
    
    # 止盈止损
    minimal_roi = {"0": 0.01}  # 1% 止盈
    stoploss = -0.02  # 2% 止损
    
    # 时间框架
    timeframe = '5m'
    
    # 追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.008
    
    startup_candle_count = 50
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 成交量均线
        dataframe['volume_mean'] = dataframe['volume'].rolling(10).mean()
        
        # 前一根K线低点
        dataframe['prev_low'] = dataframe['low'].shift(1)
        dataframe['prev_high'] = dataframe['high'].shift(1)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        做多信号（传统网格逻辑，但我们会在配置中设置为做空模式）
        这里用做多信号，但实际执行时做空
        """
        dataframe.loc[:, 'enter_long'] = 0
        
        # 条件：价格跌破前低
        conditions = [
            dataframe['close'] < dataframe['prev_low'],  # 跌破前低
            dataframe['volume'] > dataframe['volume_mean'],  # 成交量放大
            dataframe['rsi'] > 30,  # RSI 不过低
            dataframe['rsi'] < 70,  # RSI 不过高
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """平仓信号"""
        dataframe.loc[:, 'exit_long'] = 0
        
        # 条件：价格反弹
        conditions = [
            dataframe['close'] > dataframe['prev_high'],  # 反弹超过前高
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_long'] = 1
        
        return dataframe
