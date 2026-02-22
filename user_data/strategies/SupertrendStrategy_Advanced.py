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


class SupertrendStrategy_Advanced(IStrategy):
    """
    Supertrend + EMA 趋势跟踪策略 - 高级版
    
    全面优化（9个新特征）：
    A. 趋势质量：ADX, 多时间框架, 趋势斜率
    B. 资金流向：OBV, CMF, VWAP
    C. 市场结构：支撑阻力, 价格位置, 波动率自适应
    """
    
    INTERFACE_VERSION = 3
    
    # 策略参数
    atr_period = IntParameter(5, 20, default=10, space="buy")
    atr_multiplier = DecimalParameter(1.0, 5.0, default=3.0, space="buy")
    ema_fast = IntParameter(5, 50, default=9, space="buy")
    ema_slow = IntParameter(20, 200, default=21, space="buy")
    rsi_period = IntParameter(10, 30, default=14, space="buy")
    rsi_overbought = IntParameter(60, 85, default=75, space="sell")
    
    # 新增参数 - 趋势质量
    adx_threshold = IntParameter(20, 35, default=25, space="buy")
    
    # 新增参数 - 资金流向
    obv_threshold = DecimalParameter(0, 1, default=0.5, space="buy")
    cmf_threshold = DecimalParameter(-0.2, 0.2, default=0, space="buy")
    
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
    
    # 启动蜡烛数 - 增加到250以支持多时间框架
    startup_candle_count = 250
    
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
        """定义信息对 - 多时间框架"""
        return [
            ("BTC/USDT", "1h"),
            ("BTC/USDT", "4h"),
            ("ETH/USDT", "1h"),
            ("ETH/USDT", "4h"),
            ("SOL/USDT", "1h"),
            ("SOL/USDT", "4h"),
            ("DOGE/USDT", "1h"),
            ("DOGE/USDT", "4h"),
        ]
    
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
        """添加技术指标 - 高级版（20个特征）"""

        # ==================== 原有特征 ====================
        
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        
        # 200 EMA - 长期趋势判断
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # A3. 趋势斜率 - EMA 斜率（提前计算，供后续使用）
        dataframe['ema_slope'] = ta.LINEARREG_SLOPE(dataframe['ema_fast'], timeperiod=5)
        
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
        
        # ==================== A. 趋势质量（3个新特征）====================
        
        # A1. ADX - 趋势强度
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_pos'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['adx_neg'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # A2. 多时间框架趋势（简化版）
        dataframe['trend_1h'] = np.where(dataframe['ema_slope'] > 0, 1, 0)
        dataframe['trend_4h'] = np.where(dataframe['ema_200'] > dataframe['ema_200'].shift(10), 1, 0)
        
        # ==================== B. 资金流向（3个新特征）====================
        
        # B1. OBV - 能量潮
        dataframe['obv'] = ta.OBV(dataframe)
        dataframe['obv_ema'] = ta.EMA(dataframe['obv'], timeperiod=20)
        dataframe['obv_trend'] = np.where(dataframe['obv'] > dataframe['obv_ema'], 1, 0)
        
        # B2. CMF - 资金流量（ADOSC近似）
        dataframe['cmf'] = ta.ADOSC(dataframe, fastperiod=3, slowperiod=10)
        
        # B3. VWAP - 成交量加权均价
        typical_price = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        dataframe['vwap'] = (dataframe['volume'] * typical_price).cumsum() / dataframe['volume'].cumsum()
        
        # ==================== C. 市场结构（3个新特征）====================
        
        # C1. 支撑/阻力位 - 20周期高点和低点
        dataframe['support'] = dataframe['low'].rolling(20).min()
        dataframe['resistance'] = dataframe['high'].rolling(20).max()
        
        # C2. 价格位置 - 在支撑阻力区间的位置（0-1）
        dataframe['price_position'] = (dataframe['close'] - dataframe['support']) / \
                                      (dataframe['resistance'] - dataframe['support'] + 0.0001)
        
        # C3. 波动率自适应 - 高/低波动环境
        dataframe['volatility'] = dataframe['atr_pct'].rolling(50).mean()
        dataframe['high_volatility'] = np.where(
            dataframe['atr_pct'] > dataframe['volatility'], 1, 0
        )
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """定义买入信号 - 高级版：15个条件"""
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = []
        
        # ==================== 原有条件（6个）====================
        
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
        
        # ==================== A. 趋势质量条件（3个）====================
        
        # A1. ADX 趋势强度（ADX > 25）
        conditions.append(dataframe['adx'] > self.adx_threshold.value)
        
        # A2. 多时间框架趋势（1h 和 4h 都向上）
        # 注意：需要数据支持，先用简化的趋势斜率
        conditions.append(dataframe['ema_slope'] > 0)
        
        # A3. 趋势斜率为正
        # 已合并到 A2
        
        # ==================== B. 资金流向条件（3个）====================
        
        # B1. OBV 趋势向上（资金流入）
        conditions.append(dataframe['obv'] > dataframe['obv_ema'])
        
        # B2. CMF > 0（买方强势）
        conditions.append(dataframe['cmf'] > self.cmf_threshold.value)
        
        # B3. 价格在 VWAP 之上
        conditions.append(dataframe['close'] > dataframe['vwap'])
        
        # ==================== C. 市场结构条件（3个）====================
        
        # C1. 价格不在阻力位附近（避免假突破）
        conditions.append(dataframe['price_position'] < 0.9)
        
        # C2. 价格在支撑位之上（安全边际）
        conditions.append(dataframe['close'] > dataframe['support'] * 1.02)
        
        # C3. 波动率适中（不过度波动）
        conditions.append(dataframe['atr_pct'] < dataframe['volatility'] * 1.5)
        
        # ==================== 所有条件必须满足 ====================
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """定义卖出信号 - 高级版：8个条件"""
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = []
        
        # ==================== 原有条件（3个）====================
        
        # 必须同时满足多个条件才主动卖出（AND 逻辑）
        # 1. Supertrend 转空
        conditions.append(dataframe['supertrend_direction'] == -1)
        
        # 2. RSI 超买（已过热）
        conditions.append(dataframe['rsi'] > self.rsi_overbought.value)
        
        # 3. SSL Channel 转空（确认趋势转变）
        conditions.append(dataframe['close'] < dataframe['ssl_down'])
        
        # ==================== 新增条件（5个）====================
        
        # 4. ADX 趋势减弱（ADX < 20）
        conditions.append(dataframe['adx'] < 20)
        
        # 5. 趋势斜率为负
        conditions.append(dataframe['ema_slope'] < 0)
        
        # 6. 资金流出（OBV < OBV_EMA）
        conditions.append(dataframe['obv'] < dataframe['obv_ema'])
        
        # 7. 价格跌破 VWAP
        conditions.append(dataframe['close'] < dataframe['vwap'])
        
        # 8. 价格接近支撑位（风险增加）
        conditions.append(dataframe['price_position'] < 0.3)
        
        # 所有条件同时满足才主动卖出
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe


from functools import reduce
