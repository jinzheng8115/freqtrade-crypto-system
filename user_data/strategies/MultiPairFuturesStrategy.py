#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多交易对独立策略框架
每个交易对可以有独立的指标、参数和交易逻辑
"""

from freqtrade.strategy import IStrategy, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
from datetime import datetime


class MultiPairFuturesStrategy(IStrategy):
    """
    多交易对独立策略
    支持 DOGE、UNI 等多个交易对，每个都有独立的参数和逻辑
    """
    
    # 基础配置
    timeframe = '30m'
    can_short: bool = True
    stoploss = -0.03
    
    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    
    # ============ DOGE 专用参数 ============
    # 基于 Hyperopt 优化结果
    doge_adx_threshold_long = 31
    doge_adx_threshold_short = 15
    doge_alpha_threshold = 0.035
    doge_atr_multiplier = 4.344
    doge_atr_period = 24
    doge_ema_fast = 48
    doge_ema_slow = 167
    
    # ============ SUI 专用参数 ============
    # 待优化
    sui_adx_threshold_long = DecimalParameter(15, 40, default=28, space='buy', optimize=True)
    sui_adx_threshold_short = DecimalParameter(10, 30, default=20, space='sell', optimize=True)
    sui_alpha_threshold = DecimalParameter(0.01, 0.05, default=0.025, space='buy', optimize=True)
    sui_atr_multiplier = DecimalParameter(3.0, 5.0, default=3.5, space='buy', optimize=True)
    sui_atr_period = 24
    sui_ema_fast = DecimalParameter(20, 60, default=45, space='buy', optimize=True)
    sui_ema_slow = DecimalParameter(100, 200, default=150, space='buy', optimize=True)
    
    # ============ BONK 专用参数 ============
    # 待优化 (Meme币特性)
    bonk_adx_threshold_long = DecimalParameter(15, 40, default=25, space='buy', optimize=True)
    bonk_adx_threshold_short = DecimalParameter(10, 30, default=18, space='sell', optimize=True)
    bonk_alpha_threshold = DecimalParameter(0.01, 0.05, default=0.03, space='buy', optimize=True)
    bonk_atr_multiplier = DecimalParameter(3.0, 5.0, default=4.5, space='buy', optimize=True)
    bonk_atr_period = 24
    bonk_ema_fast = DecimalParameter(20, 60, default=50, space='buy', optimize=True)
    bonk_ema_slow = DecimalParameter(100, 200, default=160, space='buy', optimize=True)
    uni_adx_threshold_long = DecimalParameter(15, 40, default=25, space='buy', optimize=True)
    uni_adx_threshold_short = DecimalParameter(10, 30, default=20, space='sell', optimize=True)
    uni_alpha_threshold = DecimalParameter(0.01, 0.05, default=0.03, space='buy', optimize=True)
    uni_atr_multiplier = DecimalParameter(3.0, 5.0, default=4.0, space='buy', optimize=True)
    uni_atr_period = 24
    uni_ema_fast = DecimalParameter(20, 60, default=48, space='buy', optimize=True)
    uni_ema_slow = DecimalParameter(100, 200, default=167, space='buy', optimize=True)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        根据交易对加载不同的指标
        """
        pair = metadata['pair']
        
        # 基础指标（所有交易对都需要）
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=24)
        
        # 根据交易对加载专用指标
        if 'DOGE' in pair:
            dataframe = self._populate_doge_indicators(dataframe)
        elif 'UNI' in pair:
            dataframe = self._populate_uni_indicators(dataframe)
        elif 'SUI' in pair:
            dataframe = self._populate_sui_indicators(dataframe)
        elif 'BONK' in pair:
            dataframe = self._populate_bonk_indicators(dataframe)
        else:
            # 默认指标
            dataframe = self._populate_default_indicators(dataframe)
        
        return dataframe
    
    def _populate_doge_indicators(self, dataframe: DataFrame) -> DataFrame:
        """DOGE 专用指标"""
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.doge_ema_fast)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.doge_ema_slow)
        
        # Supertrend
        hl2 = (dataframe['high'] + dataframe['low']) / 2
        atr = ta.ATR(dataframe, timeperiod=self.doge_atr_period)
        
        upper_band = hl2 + (self.doge_atr_multiplier * atr)
        lower_band = hl2 - (self.doge_atr_multiplier * atr)
        
        dataframe['supertrend'] = 0.0
        dataframe.loc[dataframe['close'] > upper_band.shift(1), 'supertrend'] = 1
        dataframe.loc[dataframe['close'] < lower_band.shift(1), 'supertrend'] = -1
        
        # Alpha 指标
        dataframe['alpha'] = (
            (dataframe['close'] - dataframe['close'].shift(12)) / 
            dataframe['close'].shift(12) * 100
        )
        
        return dataframe
    
    def _get_param_value(self, param):
        """获取参数值，兼容 DecimalParameter 和普通数值"""
        if hasattr(param, 'value'):
            return param.value
        return param
    
    def _populate_uni_indicators(self, dataframe: DataFrame) -> DataFrame:
        """UNI 专用指标"""
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=int(self._get_param_value(self.uni_ema_fast)))
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=int(self._get_param_value(self.uni_ema_slow)))
        
        # Supertrend
        hl2 = (dataframe['high'] + dataframe['low']) / 2
        atr = ta.ATR(dataframe, timeperiod=self.uni_atr_period)
        
        upper_band = hl2 + (self._get_param_value(self.uni_atr_multiplier) * atr)
        lower_band = hl2 - (self._get_param_value(self.uni_atr_multiplier) * atr)
        
        dataframe['supertrend'] = 0.0
        dataframe.loc[dataframe['close'] > upper_band.shift(1), 'supertrend'] = 1
        dataframe.loc[dataframe['close'] < lower_band.shift(1), 'supertrend'] = -1
        
        # Alpha 指标
        dataframe['alpha'] = (
            (dataframe['close'] - dataframe['close'].shift(12)) / 
            dataframe['close'].shift(12) * 100
        )
        
        # UNI 特有：RSI 过滤
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        return dataframe
    
    def _populate_sui_indicators(self, dataframe: DataFrame) -> DataFrame:
        """SUI 专用指标"""
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=int(self._get_param_value(self.sui_ema_fast)))
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=int(self._get_param_value(self.sui_ema_slow)))
        
        # Supertrend
        hl2 = (dataframe['high'] + dataframe['low']) / 2
        atr = ta.ATR(dataframe, timeperiod=self.sui_atr_period)
        
        upper_band = hl2 + (self._get_param_value(self.sui_atr_multiplier) * atr)
        lower_band = hl2 - (self._get_param_value(self.sui_atr_multiplier) * atr)
        
        dataframe['supertrend'] = 0.0
        dataframe.loc[dataframe['close'] > upper_band.shift(1), 'supertrend'] = 1
        dataframe.loc[dataframe['close'] < lower_band.shift(1), 'supertrend'] = -1
        
        # Alpha 指标
        dataframe['alpha'] = (
            (dataframe['close'] - dataframe['close'].shift(12)) / 
            dataframe['close'].shift(12) * 100
        )
        
        return dataframe
    
    def _populate_bonk_indicators(self, dataframe: DataFrame) -> DataFrame:
        """BONK 专用指标 (Meme币特性)"""
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=int(self._get_param_value(self.bonk_ema_fast)))
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=int(self._get_param_value(self.bonk_ema_slow)))
        
        # Supertrend
        hl2 = (dataframe['high'] + dataframe['low']) / 2
        atr = ta.ATR(dataframe, timeperiod=self.bonk_atr_period)
        
        upper_band = hl2 + (self._get_param_value(self.bonk_atr_multiplier) * atr)
        lower_band = hl2 - (self._get_param_value(self.bonk_atr_multiplier) * atr)
        
        dataframe['supertrend'] = 0.0
        dataframe.loc[dataframe['close'] > upper_band.shift(1), 'supertrend'] = 1
        dataframe.loc[dataframe['close'] < lower_band.shift(1), 'supertrend'] = -1
        
        # Alpha 指标 - Meme币用更短周期
        dataframe['alpha'] = (
            (dataframe['close'] - dataframe['close'].shift(6)) / 
            dataframe['close'].shift(6) * 100
        )
        
        # BONK 特有：Volume 过滤
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def _populate_default_indicators(self, dataframe: DataFrame) -> DataFrame:
        """默认指标（未识别的交易对）"""
        # 使用 DOGE 参数作为默认
        return self._populate_doge_indicators(dataframe)
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """入场信号"""
        pair = metadata['pair']
        
        if 'DOGE' in pair:
            dataframe = self._doge_entry(dataframe)
        elif 'UNI' in pair:
            dataframe = self._uni_entry(dataframe)
        elif 'SUI' in pair:
            dataframe = self._sui_entry(dataframe)
        elif 'BONK' in pair:
            dataframe = self._bonk_entry(dataframe)
        else:
            dataframe = self._default_entry(dataframe)
        
        return dataframe
    
    def _doge_entry(self, dataframe: DataFrame) -> DataFrame:
        """DOGE 入场逻辑"""
        # 做多
        dataframe.loc[
            (
                (dataframe['supertrend'] == 1) &
                (dataframe['adx'] > self.doge_adx_threshold_long) &
                (dataframe['alpha'] > self.doge_alpha_threshold) &
                (dataframe['ema_fast'] > dataframe['ema_slow'])
            ),
            'enter_long'
        ] = 1
        
        # 做空
        dataframe.loc[
            (
                (dataframe['supertrend'] == -1) &
                (dataframe['adx'] > self.doge_adx_threshold_short) &
                (dataframe['alpha'] < -self.doge_alpha_threshold) &
                (dataframe['ema_fast'] < dataframe['ema_slow'])
            ),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def _uni_entry(self, dataframe: DataFrame) -> DataFrame:
        """UNI 入场逻辑"""
        # 做多
        dataframe.loc[
            (
                (dataframe['supertrend'] == 1) &
                (dataframe['adx'] > self._get_param_value(self.uni_adx_threshold_long)) &
                (dataframe['alpha'] > self._get_param_value(self.uni_alpha_threshold)) &
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['rsi'] < 70)  # UNI 特有：RSI 过滤
            ),
            'enter_long'
        ] = 1
        
        # 做空
        dataframe.loc[
            (
                (dataframe['supertrend'] == -1) &
                (dataframe['adx'] > self._get_param_value(self.uni_adx_threshold_short)) &
                (dataframe['alpha'] < -self._get_param_value(self.uni_alpha_threshold)) &
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (dataframe['rsi'] > 30)  # UNI 特有：RSI 过滤
            ),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def _sui_entry(self, dataframe: DataFrame) -> DataFrame:
        """SUI 入场逻辑"""
        # 做多
        dataframe.loc[
            (
                (dataframe['supertrend'] == 1) &
                (dataframe['adx'] > self._get_param_value(self.sui_adx_threshold_long)) &
                (dataframe['alpha'] > self._get_param_value(self.sui_alpha_threshold)) &
                (dataframe['ema_fast'] > dataframe['ema_slow'])
            ),
            'enter_long'
        ] = 1
        
        # 做空
        dataframe.loc[
            (
                (dataframe['supertrend'] == -1) &
                (dataframe['adx'] > self._get_param_value(self.sui_adx_threshold_short)) &
                (dataframe['alpha'] < -self._get_param_value(self.sui_alpha_threshold)) &
                (dataframe['ema_fast'] < dataframe['ema_slow'])
            ),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def _bonk_entry(self, dataframe: DataFrame) -> DataFrame:
        """BONK 入场逻辑 (Meme币 - 需要成交量确认)"""
        # 做多
        dataframe.loc[
            (
                (dataframe['supertrend'] == 1) &
                (dataframe['adx'] > self._get_param_value(self.bonk_adx_threshold_long)) &
                (dataframe['alpha'] > self._get_param_value(self.bonk_alpha_threshold)) &
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['volume'] > dataframe['volume_ma'])  # BONK 特有：成交量过滤
            ),
            'enter_long'
        ] = 1
        
        # 做空
        dataframe.loc[
            (
                (dataframe['supertrend'] == -1) &
                (dataframe['adx'] > self._get_param_value(self.bonk_adx_threshold_short)) &
                (dataframe['alpha'] < -self._get_param_value(self.bonk_alpha_threshold)) &
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (dataframe['volume'] > dataframe['volume_ma'])  # BONK 特有：成交量过滤
            ),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def _default_entry(self, dataframe: DataFrame) -> DataFrame:
        """默认入场逻辑"""
        return self._doge_entry(dataframe)
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """出场信号"""
        # 简单的出场逻辑（主要靠 trailing stop）
        dataframe.loc[
            (dataframe['supertrend'] == -1),
            'exit_long'
        ] = 1
        
        dataframe.loc[
            (dataframe['supertrend'] == 1),
            'exit_short'
        ] = 1
        
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str,
                 side: str, **kwargs) -> float:
        """固定杠杆"""
        return 2.0
    
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            leverage: float, entry_tag: str, side: str,
                            **kwargs) -> float:
        """
        基于波动率动态调整仓位大小
        
        逻辑：
        - 计算相对波动率（ATR/价格）
        - 波动率低 → 增加仓位
        - 波动率高 → 减少仓位
        """
        # 基础仓位
        base_stake = 150.0
        
        # 从 dataframe 获取波动率数据
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 24:
            # 数据不足，使用基础仓位
            return base_stake
        
        # 计算相对波动率（使用最近24根K线的价格变动标准差）
        recent_closes = dataframe['close'].tail(24)
        returns = recent_closes.pct_change().dropna()
        volatility = returns.std() * 100  # 转为百分比
        
        # 根据波动率调整仓位
        if volatility < 2.0:
            # 低波动 - 增加仓位 33%
            stake = base_stake * 1.33  # ~200 USDT
        elif volatility < 4.0:
            # 正常波动 - 基础仓位
            stake = base_stake  # 150 USDT
        elif volatility < 6.0:
            # 较高波动 - 减少仓位 33%
            stake = base_stake * 0.67  # ~100 USDT
        else:
            # 高波动 - 最小仓位 50%
            stake = base_stake * 0.5  # ~75 USDT
        
        # 确保不超过 max_stake
        stake = min(stake, max_stake)
        
        # 记录日志
        self.dp.send_msg(
            f"*{pair}* Volatility: {volatility:.2f}% → Stake: {stake:.0f} USDT"
        )
        
        return stake
