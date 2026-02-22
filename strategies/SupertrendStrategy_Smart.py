# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union

from freqtrade.strategy import IStrategy, CategoricalParameter, DecimalParameter, IntParameter
from technical.util import resample_to_interval, resampled_merge
from technical.indicators import SSLChannels, vwmacd
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class SupertrendStrategy_Smart(IStrategy):
    """
    Supertrend + EMA 趋势跟踪策略 - 智能版
    
    核心优化：
    1. 添加200 EMA市场趋势过滤（下跌市不交易）
    2. 更严格的卖出条件（AND 逻辑）
    3. 更激进的止盈策略
    4. 优化的追踪止损
    """
    
    INTERFACE_VERSION = 3
    
    # 策略参数 - Sharpe 优化后
    atr_period = IntParameter(5, 20, default=5, space="buy")  # 优化：10 → 5
    atr_multiplier = DecimalParameter(1.0, 5.0, default=4.366, space="buy")  # 优化：3.0 → 4.366
    ema_fast = IntParameter(5, 50, default=10, space="buy")  # 优化：9 → 10
    ema_slow = IntParameter(20, 200, default=113, space="buy")  # 优化：21 → 113
    rsi_period = IntParameter(10, 30, default=12, space="buy")  # 优化：14 → 12
    rsi_overbought = IntParameter(60, 85, default=82, space="sell")  # 优化：75 → 82
    
    # ADX 参数 - 调整为更合理的值
    adx_threshold = IntParameter(20, 35, default=28, space="buy")  # 调整：35 → 28
    
    # 最小收益率 - 更激进的止盈
    minimal_roi = {
        "240": 0.02,   # 4小时 2%
        "120": 0.03,   # 2小时 3%
        "60": 0.05,    # 1小时 5%
        "30": 0.08,    # 30分钟 8%
        "0": 0.12      # 即时 12%
    }
    
    # 止损 - 5% 是最优设置
    stoploss = -0.05
    
    # 时间框架
    timeframe = '15m'
    
    # 追踪止损 - 更激进
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    
    # 启动蜡烛数
    startup_candle_count = 200
    
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
    
    def supertrend(self, dataframe, period=10, multiplier=3):
        """
        计算 Supertrend 指标
        """
        hl2 = (dataframe['high'] + dataframe['low']) / 2
        
        # ATR
        atr = ta.ATR(dataframe, timeperiod=period)
        
        # 基本带
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)
        
        # 初始化
        supertrend = np.zeros(len(dataframe))
        direction = np.zeros(len(dataframe))
        
        for i in range(1, len(dataframe)):
            if dataframe['close'][i] > upperband[i-1]:
                direction[i] = 1
            elif dataframe['close'][i] < lowerband[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
            
            if direction[i] == 1:
                supertrend[i] = lowerband[i]
            else:
                supertrend[i] = upperband[i]
        
        return pd.Series(supertrend, index=dataframe.index), pd.Series(direction, index=dataframe.index)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """添加技术指标 - 优化版：添加 ADX 趋势强度"""

        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        
        # 200 EMA - 长期趋势判断
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Supertrend
        dataframe['supertrend'], dataframe['supertrend_direction'] = self.supertrend(
            dataframe, 
            period=self.atr_period.value, 
            multiplier=self.atr_multiplier.value
        )
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        
        # Volume Weighted MACD
        vwmacd_data = vwmacd(dataframe)
        if isinstance(vwmacd_data, pd.DataFrame):
            dataframe['vwmacd'] = vwmacd_data.iloc[:, 0] if len(vwmacd_data.columns) > 0 else 0
        else:
            dataframe['vwmacd'] = vwmacd_data
        dataframe['vwmacd_signal'] = ta.EMA(dataframe['vwmacd'], timeperiod=9)
        
        # ATR for volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # SSL Channel
        dataframe['ssl_up'], dataframe['ssl_down'] = SSLChannels(dataframe, 10)
        
        # ========== 新增：ADX 趋势强度 ==========
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_pos'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['adx_neg'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """定义买入信号 - 智能版：只在上涨市交易，ADX 过滤"""
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = []
        
        # 0. 市场趋势过滤：价格必须在200 EMA之上（上涨市）
        conditions.append(dataframe['close'] > dataframe['ema_200'])
        
        # 1. Supertrend 看涨
        conditions.append(dataframe['supertrend_direction'] == 1)
        
        # 2. 快线 EMA 在慢线之上
        conditions.append(dataframe['ema_fast'] > dataframe['ema_slow'])
        
        # 3. SSL Channel 看涨
        conditions.append(dataframe['close'] > dataframe['ssl_up'])
        
        # 4. 成交量确认 (当前成交量 > 平均成交量)
        conditions.append(dataframe['volume'] > dataframe['volume'].rolling(20).mean())
        
        # 5. 不追太高 (RSI < 75)
        conditions.append(dataframe['rsi'] < self.rsi_overbought.value)
        
        # ========== 新增：ADX 趋势强度过滤 ==========
        # 6. ADX > 25（强趋势）
        conditions.append(dataframe['adx'] > self.adx_threshold.value)
        
        # 7. +DI > -DI（上涨趋势）
        conditions.append(dataframe['adx_pos'] > dataframe['adx_neg'])
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """定义卖出信号 - 优化版：更严格的条件"""
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = []
        
        # 必须同时满足多个条件才主动卖出（AND 逻辑）
        # 1. Supertrend 转空
        conditions.append(dataframe['supertrend_direction'] == -1)
        
        # 2. RSI 超买（已过热）
        conditions.append(dataframe['rsi'] > self.rsi_overbought.value)
        
        # 3. SSL Channel 转空（确认趋势转变）
        conditions.append(dataframe['close'] < dataframe['ssl_down'])
        
        # 所有条件同时满足才主动卖出
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe


from functools import reduce
