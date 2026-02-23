# BreakoutStrategyV2 - 简化突破策略
# 只做突破检测 + 成交量确认

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from functools import reduce
import logging

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta

logger = logging.getLogger(__name__)


class BreakoutStrategyV2(IStrategy):
    """
    突破策略 V2 - 简化版
    
    核心逻辑：
    - 价格下跌超过阈值 + 成交量放大 = 做空
    - 价格上涨超过阈值 + 成交量放大 = 做多
    
    简化条件，提高信号频率
    """
    
    INTERFACE_VERSION = 3

    # 可调参数
    breakout_threshold = DecimalParameter(1.0, 4.0, default=2.0, space="buy")
    volume_multiplier = DecimalParameter(1.2, 2.0, default=1.5, space="buy")

    # 30分钟周期
    timeframe = '30m'
    
    # 风险控制
    minimal_roi = {
        "0": 0.03,
        "60": 0.015,
        "120": 0.01
    }
    stoploss = -0.025
    
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.02
    
    startup_candle_count = 50

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    can_short: bool = True
    leverage_default = 2

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算技术指标"""
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # EMA
        dataframe['ema_20'] = ta.EMA(dataframe['close'], timeperiod=20)
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # 价格变化 (1小时 = 2根30分钟K线)
        dataframe['price_change_1h'] = dataframe['close'].pct_change(periods=2) * 100
        
        # 波动率
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volatility'] = dataframe['atr'] / dataframe['close'] * 100
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - 禁用（熊市模式）"""
        dataframe.loc[:, 'enter_long'] = 0
        return dataframe

    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空 - 快速下跌"""
        dataframe.loc[:, 'enter_short'] = 0

        # 简化条件：价格下跌 + 成交量放大
        condition = (
            (dataframe['price_change_1h'] < -self.breakout_threshold.value) &
            (dataframe['volume_ratio'] > self.volume_multiplier.value) &
            (dataframe['volatility'] < 10)
        )
        
        dataframe.loc[condition, 'enter_short'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多平仓"""
        dataframe.loc[:, 'exit_long'] = 0
        
        # 价格回落或RSI超买
        condition = (
            (dataframe['rsi'] > 70) |
            (dataframe['close'] < dataframe['ema_20'])
        )
        
        dataframe.loc[condition, 'exit_long'] = 1
        return dataframe

    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空平仓"""
        dataframe.loc[:, 'exit_short'] = 0
        
        # 价格反弹或RSI超卖
        condition = (
            (dataframe['rsi'] < 30) |
            (dataframe['close'] > dataframe['ema_20'])
        )
        
        dataframe.loc[condition, 'exit_short'] = 1
        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                side: str, **kwargs) -> float:
        return self.leverage_default
