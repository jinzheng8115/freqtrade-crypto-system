# BreakoutStrategyV1 - 突破策略（捕捉快速下跌/上涨）
# 适用于 15 分钟周期，快速响应市场变化

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


class BreakoutStrategyV1(IStrategy):
    """
    突破策略 V1 - 捕捉快速行情
    
    核心逻辑：
    1. 价格突破检测：1小时内下跌/上涨超过阈值
    2. 成交量放大：当前成交量 > 均量 * 2
    3. 动量确认：RSI 极端值 + MACD 方向
    4. 波动率过滤：避免过度震荡
    
    做空条件：
    - 1小时跌幅 > 2.5%
    - 成交量 > 均量 * 1.8
    - RSI < 40 (超卖)
    - MACD 负值且下降
    
    做多条件：
    - 1小时涨幅 > 2.5%
    - 成交量 > 均量 * 1.8
    - RSI > 60 (超买)
    - MACD 正值且上升
    
    风险控制：
    - 止损: 2%
    - 止盈: 4%
    - 最大持仓时间: 4小时
    """
    
    INTERFACE_VERSION = 3

    # 可调参数 - V1.2 放宽版
    breakout_threshold = DecimalParameter(1.0, 3.0, default=1.5, space="buy")  # 突破阈值降低
    volume_multiplier = DecimalParameter(1.2, 2.5, default=1.3, space="buy")   # 成交量倍数降低到1.3
    rsi_oversold = IntParameter(30, 50, default=50, space="buy")                # 做空RSI: < 50 (很宽松)
    rsi_overbought = IntParameter(50, 70, default=55, space="buy")              # 做多RSI放宽

    # 时间周期 - 改用30分钟，减少噪音
    timeframe = '30m'
    
    # 风险控制 - 放宽止损
    minimal_roi = {
        "0": 0.03,      # 3% 止盈
        "30": 0.02,     # 30分钟后 2%
        "60": 0.015,    # 1小时后 1.5%
        "120": 0.01     # 2小时后 1%
    }
    stoploss = -0.025   # 2.5% 止损（放宽）
    
    # 追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True
    
    startup_candle_count = 100
    use_exit_signal = True
    exit_profit_only = False

    order_types = {
        'entry': 'limit',  # 使用限价单
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    can_short: bool = True  # 允许做空
    leverage_default = 2
    
    # 暂时禁用只做空模式，双向测试
    short_only_mode = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算技术指标"""
        
        # === 基础指标 ===
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema_20'] = ta.EMA(dataframe['close'], timeperiod=20)
        dataframe['ema_50'] = ta.EMA(dataframe['close'], timeperiod=50)
        
        # === 成交量指标 ===
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # === 价格变化率 ===
        # 1小时变化 (2根30分钟K线)
        dataframe['price_change_1h'] = dataframe['close'].pct_change(periods=2) * 100
        # 30分钟变化 (1根K线)
        dataframe['price_change_30m'] = dataframe['close'].pct_change(periods=1) * 100
        
        # === MACD ===
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macd'] - macd['macdsignal']
        
        # === 波动率 ===
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volatility'] = dataframe['atr'] / dataframe['close'] * 100
        
        # === ADX (趋势强度) ===
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_pos'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['adx_neg'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # === 突破信号 ===
        # 做空突破：快速下跌
        dataframe['breakout_short'] = (
            (dataframe['price_change_1h'] < -self.breakout_threshold.value) |  # 1小时跌幅 > 阈值
            (dataframe['price_change_30m'] < -self.breakout_threshold.value * 0.7)  # 或30分钟急跌
        ).astype(int)
        
        # 做多突破：快速上涨
        dataframe['breakout_long'] = (
            (dataframe['price_change_1h'] > self.breakout_threshold.value) |  # 1小时涨幅 > 阈值
            (dataframe['price_change_30m'] > self.breakout_threshold.value * 0.7)  # 或30分钟急涨
        ).astype(int)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - 快速上涨突破"""
        dataframe.loc[:, 'enter_long'] = 0
        
        # 熊市模式 - 禁用做多
        if getattr(self, 'short_only_mode', False):
            return dataframe

        conditions = [
            # === 突破检测 ===
            dataframe['breakout_long'] == 1,
            
            # === 成交量确认 ===
            dataframe['volume_ratio'] > self.volume_multiplier.value,
            
            # === 动量确认 ===
            dataframe['rsi'] > self.rsi_overbought.value,  # 动量强劲
            dataframe['macd_hist'] > 0,  # MACD 上升
            
            # === 趋势确认 ===
            dataframe['close'] > dataframe['ema_20'],  # 价格在均线上方
            
            # === 波动率过滤 ===
            dataframe['volatility'] < 8,  # 避免极端波动
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1

        return dataframe

    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空 - 快速下跌突破"""
        dataframe.loc[:, 'enter_short'] = 0

        conditions = [
            # === 突破检测 ===
            dataframe['breakout_short'] == 1,
            
            # === 成交量确认 ===
            dataframe['volume_ratio'] > self.volume_multiplier.value,
            
            # === 动量确认 ===
            dataframe['rsi'] < self.rsi_oversold.value,  # 超卖
            dataframe['macd_hist'] < 0,  # MACD 下降
            
            # === 趋势确认 ===
            dataframe['close'] < dataframe['ema_20'],  # 价格在均线下方
            
            # === 波动率过滤 ===
            dataframe['volatility'] < 8,  # 避免极端波动
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多平仓"""
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # 反转信号
            (dataframe['rsi'] > 75) |  # 严重超买
            (dataframe['price_change_30m'] < -1.5)  # 30分钟快速下跌
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_long'] = 1
        
        return dataframe

    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空平仓"""
        dataframe.loc[:, 'exit_short'] = 0
        
        conditions = [
            # 反转信号
            (dataframe['rsi'] < 30) |  # 严重超卖
            (dataframe['price_change_30m'] > 1.5)  # 30分钟快速上涨
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x | y, conditions), 'exit_short'] = 1
        
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, 
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """入场确认 - 额外安全检查"""
        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]
        
        # 检查波动率是否过高（避免极端行情）
        if last_candle['volatility'] > 10:
            logger.info(f"波动率过高，跳过 {pair}: {last_candle['volatility']:.2f}%")
            return False
        
        # 检查成交量是否异常（可能是数据问题）
        if last_candle['volume_ratio'] > 10:
            logger.info(f"成交量异常，跳过 {pair}: ratio={last_candle['volume_ratio']:.2f}")
            return False
        
        return True

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                side: str, **kwargs) -> float:
        """动态杠杆 - 根据信号强度调整"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]
        
        # 根据成交量强度调整杠杆
        volume_strength = min(last_candle['volume_ratio'] / 3, 1.5)  # 最大1.5倍
        
        # 基础杠杆 * 强度调整
        leverage = self.leverage_default * (0.8 + volume_strength * 0.4)
        
        return min(leverage, max_leverage)
