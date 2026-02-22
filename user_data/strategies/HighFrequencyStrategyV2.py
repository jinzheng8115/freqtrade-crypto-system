# HighFrequencyStrategyV2 - 改进版高频策略
# 改进点:
# 1. 增加趋势过滤（30m趋势）
# 2. 优化入场条件
# 3. 调整止盈止损
# 4. 增加波动率过滤

import numpy as np
import pandas as pd
from pandas import DataFrame
from functools import reduce
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

class HighFrequencyStrategyV2(IStrategy):
    """
    高频策略改进版 V2
    
    改进:
    1. 只在30m趋势方向交易
    2. 增加波动率过滤
    3. 优化入场条件
    4. 调整风险参数
    """
    
    INTERFACE_VERSION = 3
    
    # 参数
    breakout_period = IntParameter(3, 10, default=5, space="buy")
    volume_mult = DecimalParameter(1.5, 2.5, default=2.0, space="buy")
    
    # 风险管理
    minimal_roi = {"0": 0.005}  # 0.5%止盈
    stoploss = -0.003  # 0.3%止损
    
    timeframe = '5m'
    startup_candle_count = 200
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    can_short: bool = True
    leverage_default = 2
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 5分钟指标
        dataframe['ema5_fast'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema5_slow'] = ta.EMA(dataframe, timeperiod=15)
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['high_5'] = dataframe['high'].rolling(5).max().shift(1)
        dataframe['low_5'] = dataframe['low'].rolling(5).min().shift(1)
        
        # 30分钟趋势（从更高时间框架）
        # 简化处理：使用更长周期的EMA判断趋势
        dataframe['ema30_trend'] = ta.EMA(dataframe, timeperiod=30)
        dataframe['is_uptrend_5m'] = dataframe['close'] > dataframe['ema30_trend']
        dataframe['is_downtrend_5m'] = dataframe['close'] < dataframe['ema30_trend']
        
        # 波动率
        dataframe['volatility'] = dataframe['close'].pct_change().rolling(20).std()
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 1. 30m趋势向上
            dataframe['is_uptrend_5m'],
            
            # 2. 突破前5根高点
            dataframe['close'] > dataframe['high_5'],
            
            # 3. 成交量放大
            dataframe['volume'] > dataframe['volume_ma'] * 2,
            
            # 4. 5m EMA金叉
            dataframe['ema5_fast'] > dataframe['ema5_slow'],
            
            # 5. 波动率适中（不太高也不太低）
            (dataframe['volatility'] > 0.002) & (dataframe['volatility'] < 0.015),
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # EMA死叉或跌破支撑
            (dataframe['ema5_fast'] < dataframe['ema5_slow']) |
            (dataframe['close'] < dataframe['low_5'])
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_long'] = 1
        
        return dataframe
    
    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_short'] = 0
        
        conditions = [
            dataframe['is_downtrend_5m'],
            dataframe['close'] < dataframe['low_5'],
            dataframe['volume'] > dataframe['volume_ma'] * 2,
            dataframe['ema5_fast'] < dataframe['ema5_slow'],
            (dataframe['volatility'] > 0.002) & (dataframe['volatility'] < 0.015),
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_short'] = 0
        
        conditions = [
            (dataframe['ema5_fast'] > dataframe['ema5_slow']) |
            (dataframe['close'] > dataframe['high_5'])
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_short'] = 1
        
        return dataframe
