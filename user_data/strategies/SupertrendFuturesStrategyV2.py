# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# isort: skip_file
"""
Supertrend Futures V2 策略 - 优化版
改进点：
1. 适当放宽入场条件，增加交易机会
2. 添加 ADX 趋势强度
3. 优化做多做空信号
4. 动态杠杆管理
"""
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union
from functools import reduce

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta


class SupertrendFuturesStrategyV2(IStrategy):
    """
    Supertrend V2 - 合约优化版
    支持做多和做空
    """
    
    INTERFACE_VERSION = 3
    
    # 可优化参数
    atr_period = IntParameter(10, 30, default=26, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.821, space="buy", optimize=True)
    ema_fast = IntParameter(5, 20, default=19, space="buy", optimize=True)
    ema_slow = IntParameter(20, 50, default=49, space="buy", optimize=True)
    adx_threshold = IntParameter(18, 30, default=24, space="buy", optimize=True)
    
    # 止盈
    minimal_roi = {
        "0": 0.08,     # 8% 即时止盈
    }
    
    # 止损
    stoploss = -0.07  # 7% (放宽止损)
    
    # 时间框架
    timeframe = '15m'
    
    # 追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.035
    trailing_only_offset_is_reached = True
    
    startup_candle_count = 200
    
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
    
    can_short: bool = True
    leverage_default = 2
    
    use_exit_signal = True
    exit_profit_only = False
    
    def informative_pairs(self):
        return []
    
    def supertrend(self, dataframe, period=14, multiplier=3):
        """计算 Supertrend 指标"""
        df = dataframe.copy()
        hl2 = (df['high'] + df['low']) / 2
        atr = ta.ATR(df, timeperiod=period)
        
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)
        
        supertrend = [0] * len(df)
        direction = [1] * len(df)
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > upperband.iloc[i-1]:
                direction[i] = 1
            elif df['close'].iloc[i] < lowerband.iloc[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
            
            if direction[i] == 1:
                supertrend[i] = lowerband.iloc[i]
            else:
                supertrend[i] = upperband.iloc[i]
        
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """动态杠杆 - 默认2x"""
        return min(self.leverage_default, max_leverage)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA 趋势
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        
        # Supertrend
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, 
            period=self.atr_period.value, 
            multiplier=self.atr_multiplier.value
        )
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多信号"""
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 1. Supertrend 看涨
            dataframe['st_dir'] == 1,
            
            # 2. EMA 多头
            dataframe['ema_fast'] > dataframe['ema_slow'],
            
            # 3. ADX > 20 (趋势存在)
            dataframe['adx'] > self.adx_threshold.value,
            
            # 4. RSI < 70
            dataframe['rsi'] < 70,
            
            # 5. 成交量 > 平均 (放宽)
            dataframe['volume'] > dataframe['volume_ma'],
            
            # 6. 价格在 Supertrend 之上
            dataframe['close'] > dataframe['supertrend'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多平仓"""
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            dataframe['st_dir'] == -1,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
    
    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空信号"""
        dataframe.loc[:, 'enter_short'] = 0
        
        conditions = [
            # 1. Supertrend 看空
            dataframe['st_dir'] == -1,
            
            # 2. EMA 空头
            dataframe['ema_fast'] < dataframe['ema_slow'],
            
            # 3. ADX > 20
            dataframe['adx'] > self.adx_threshold.value,
            
            # 4. RSI > 30
            dataframe['rsi'] > 30,
            
            # 5. 成交量 > 平均
            dataframe['volume'] > dataframe['volume_ma'],
            
            # 6. 价格在 Supertrend 之下
            dataframe['close'] < dataframe['supertrend'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空平仓"""
        dataframe.loc[:, 'exit_short'] = 0
        
        conditions = [
            dataframe['st_dir'] == 1,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_short'] = 1
        
        return dataframe
