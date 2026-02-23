# SupertrendFuturesStrategyV8_2 - 市场环境自适应版
# 基于V8.1，添加牛熊市识别和动态调整

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


class SupertrendFuturesStrategyV8_2(IStrategy):
    """
    V8.2: 市场环境自适应版
    
    新增功能：
    1. 市场环境识别（日线趋势）
       - 牛市：价格 > EMA200，做多优先
       - 熊市：价格 < EMA200，做空优先
       - 震荡：横盘整理，减少交易
    
    2. 动态条件调整
       - 牛市：放宽做多ADX(30)，收紧做空ADX(35)
       - 熊市：放宽做空ADX(20)，收紧做多ADX(40)
       - 震荡：ADX要求35+
    
    3. 杠杆动态调整
       - 顺势交易：2x杠杆
       - 逆势交易：1x杠杆
    
    基础参数继承V8.1优化结果
    """
    
    INTERFACE_VERSION = 3

    # V8.1 优化参数（从Hyperopt结果）
    atr_period = IntParameter(5, 30, default=21, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=4.622, space="buy")
    ema_fast = IntParameter(5, 50, default=21, space="buy")
    ema_slow = IntParameter(20, 200, default=47, space="buy")
    adx_threshold_long = IntParameter(20, 40, default=34, space="buy")
    adx_threshold_short = IntParameter(15, 35, default=23, space="buy")
    alpha_threshold = DecimalParameter(0.02, 0.15, default=0.118, space="buy")
    
    # V8.2 新增参数 - 市场环境
    trend_lookback = IntParameter(50, 200, default=100, space="buy")  # 趋势判断周期
    bear_adx_bonus = IntParameter(5, 15, default=10, space="buy")  # 熊市做空ADX放宽
    bull_adx_penalty = IntParameter(5, 15, default=10, space="buy")  # 牛市做空ADX收紧

    minimal_roi = {"0": 0.06}
    stoploss = -0.03
    timeframe = '30m'
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    startup_candle_count = 200

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    can_short: bool = True
    leverage_default = 2

    def supertrend(self, dataframe, period=14, multiplier=3):
        """Supertrend计算"""
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
            supertrend[i] = lowerband.iloc[i] if direction[i] == 1 else upperband.iloc[i]
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    def detect_market_regime(self, dataframe: DataFrame) -> DataFrame:
        """
        检测市场环境
        返回: 1=牛市, -1=熊市, 0=震荡
        """
        # 使用长期EMA判断趋势
        dataframe['ema_trend'] = ta.EMA(dataframe['close'], timeperiod=self.trend_lookback.value)
        
        # 价格相对位置
        price_position = (dataframe['close'] - dataframe['ema_trend']) / dataframe['ema_trend'] * 100
        
        # 趋势强度（ADX）
        adx = ta.ADX(dataframe, timeperiod=14)
        
        # 市场环境判断 - 放宽条件
        conditions = [
            (price_position > 2) & (adx > 20),   # 牛市：放宽
            (price_position < -2) & (adx > 20),  # 熊市：放宽
        ]
        choices = [1, -1]  # 牛市=1, 熊市=-1
        
        dataframe['market_regime'] = np.select(conditions, choices, default=0)
        
        return dataframe

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        """动态杠杆 - 顺势加仓，逆势减仓"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return min(self.leverage_default, max_leverage)
        
        last_candle = dataframe.iloc[-1]
        regime = last_candle.get('market_regime', 0)
        
        # 顺势交易：2x杠杆
        # 逆势交易：1x杠杆
        # 震荡市：1.5x杠杆
        if regime == 1 and side == 'long':  # 牛市做多
            leverage = 2.0
        elif regime == -1 and side == 'short':  # 熊市做空
            leverage = 2.0
        elif regime == 1 and side == 'short':  # 牛市做空（逆势）
            leverage = 1.0
        elif regime == -1 and side == 'long':  # 熊市做多（逆势）
            leverage = 1.0
        else:  # 震荡市
            leverage = 1.5
        
        return min(leverage, max_leverage)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算技术指标"""
        
        # === V8.1 核心指标 ===
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value
        )
        
        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_pos'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['adx_neg'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        
        # Alpha#101 (简化版)
        dataframe['alpha_101'] = (
            (dataframe['close'] - dataframe['close'].shift(5)) / dataframe['close'].shift(5) * 100 -
            (dataframe['volume'] - dataframe['volume'].shift(5)) / dataframe['volume'].shift(5) * 10
        )
        
        # 趋势判断
        dataframe['is_uptrend'] = dataframe['close'] > dataframe['supertrend']
        dataframe['is_downtrend'] = dataframe['close'] < dataframe['supertrend']
        
        # 波动率
        dataframe['volatility_ratio'] = ta.ATR(dataframe, timeperiod=14) / dataframe['close']
        
        # === V8.2 新增：市场环境判断 ===
        dataframe = self.detect_market_regime(dataframe)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - 根据市场环境调整条件"""
        dataframe.loc[:, 'enter_long'] = 0
        
        # 获取当前市场环境
        regime = dataframe['market_regime'].iloc[-1] if len(dataframe) > 0 else 0
        
        # 根据市场环境调整ADX阈值
        if regime == 1:  # 牛市：放宽做多
            adx_threshold = self.adx_threshold_long.value - 5
        elif regime == -1:  # 熊市：收紧做多
            adx_threshold = self.adx_threshold_long.value + 10
        else:  # 震荡：标准
            adx_threshold = self.adx_threshold_long.value
        
        conditions = [
            # V8.1 核心条件
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > adx_threshold,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
            
            # V8.1 多因子
            (dataframe['rsi'] > 35) & (dataframe['rsi'] < 80),
            dataframe['alpha_101'] > self.alpha_threshold.value,
            dataframe['volume'] > dataframe['volume_ma'] * 1.1,
            dataframe['volatility_ratio'] < 0.06,
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1

        return dataframe

    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空 - 根据市场环境调整条件"""
        dataframe.loc[:, 'enter_short'] = 0
        
        # 获取当前市场环境
        regime = dataframe['market_regime'].iloc[-1] if len(dataframe) > 0 else 0
        
        # 根据市场环境调整ADX阈值
        if regime == -1:  # 熊市：放宽做空
            adx_threshold = self.adx_threshold_short.value - self.bear_adx_bonus.value
        elif regime == 1:  # 牛市：收紧做空
            adx_threshold = self.adx_threshold_short.value + self.bull_adx_penalty.value
        else:  # 震荡：标准
            adx_threshold = self.adx_threshold_short.value
        
        conditions = [
            # V8.1 核心条件
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > adx_threshold,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
            
            # V8.1 多因子
            (dataframe['rsi'] > 20) & (dataframe['rsi'] < 65),
            dataframe['alpha_101'] < -self.alpha_threshold.value,
            dataframe['volume'] > dataframe['volume_ma'] * 1.1,
            dataframe['volatility_ratio'] < 0.06,
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多平仓"""
        dataframe.loc[:, 'exit_long'] = 0
        conditions = [dataframe['st_dir'] == -1]
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        return dataframe

    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空平仓"""
        dataframe.loc[:, 'exit_short'] = 0
        conditions = [dataframe['st_dir'] == 1]
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_short'] = 1
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, 
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """入场确认"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return False
        
        last_candle = dataframe.iloc[-1]
        
        # 避免极端波动
        if last_candle['volatility_ratio'] > 0.08:
            logger.info(f"波动率过高，跳过 {pair}")
            return False
        
        return True
