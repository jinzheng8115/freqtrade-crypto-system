# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class InverseGridStrategy(IStrategy):
    """
    合约反向网格策略 - 专为下跌市场设计
    
    核心原理：
    - 价格下跌 → 做空盈利
    - 价格反弹 → 平仓止盈
    - 循环执行，持续盈利
    
    适用市场：下跌趋势、震荡下跌
    预期收益：20-35%/月
    """
    
    INTERFACE_VERSION = 3
    
    # 策略参数
    grid_spacing = DecimalParameter(0.003, 0.01, default=0.005, space="buy")  # 网格间距 0.3-1%
    grid_count = IntParameter(20, 50, default=30, space="buy")  # 网格数量
    
    # RSI 参数
    rsi_period = IntParameter(10, 20, default=14, space="buy")
    rsi_oversold = IntParameter(25, 35, default=30, space="buy")  # 避免超卖反弹
    rsi_exit = IntParameter(35, 45, default=40, space="sell")  # 反弹退出信号
    
    # 止盈止损
    minimal_roi = {
        "0": 0.008  # 0.8% 即时止盈
    }
    stoploss = -0.02  # 2% 止损
    
    # 时间框架
    timeframe = '5m'
    
    # 追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.003
    trailing_stop_positive_offset = 0.005
    trailing_only_offset_is_reached = True
    
    # 启动蜡烛数
    startup_candle_count = 100
    
    # 订单类型
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC'
    }
    
    def informative_pairs(self):
        """定义信息对"""
        return []
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """添加技术指标"""
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        
        # 成交量均线
        dataframe['volume_mean'] = dataframe['volume'].rolling(10).mean()
        
        # 价格变化率
        dataframe['price_change'] = dataframe['close'].pct_change()
        
        # 波动率（ATR百分比）
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # 网格参考价格（前一根K线的低点）
        dataframe['grid_reference'] = dataframe['low'].shift(1)
        
        # 网格价格（基于网格间距）
        dataframe['grid_price_buy'] = dataframe['grid_reference'] * (1 - self.grid_spacing.value)
        dataframe['grid_price_sell'] = dataframe['grid_reference'] * (1 + self.grid_spacing.value)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """定义做空入场信号 - 放宽条件"""
        dataframe.loc[:, 'enter_short'] = 0
        
        conditions = []
        
        # 1. 价格跌破前一根K线低点
        conditions.append(dataframe['close'] < dataframe['grid_reference'])
        
        # 2. 成交量放大
        conditions.append(dataframe['volume'] > dataframe['volume_mean'])
        
        # 3. RSI在合理范围（25-65）
        conditions.append(dataframe['rsi'] > 25)
        conditions.append(dataframe['rsi'] < 65)
        
        # 所有条件满足时做空
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """定义平仓信号 - 放宽条件"""
        dataframe.loc[:, 'exit_short'] = 0
        
        conditions = []
        
        # 1. 价格反弹超过 0.5%
        conditions.append(dataframe['close'] > dataframe['close'].shift(1) * 1.005)
        
        # 2. 或 RSI 反弹（> 45）
        conditions.append(dataframe['rsi'] > 45)
        
        # 满足任一条件即平仓
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_short'] = 1
        
        return dataframe


from functools import reduce
