# SupertrendFuturesStrategyV5 - 多时间框架 + 动态风控
# 优化：
# 1. 多时间框架趋势（1h/4h 确认大势）
# 2. 波动率动态止损（ATR 倍数）
# 3. 信号强度评分（动态仓位）
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from functools import reduce

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta


class SupertrendFuturesStrategyV5(IStrategy):
    INTERFACE_VERSION = 3
    
    # 基础参数
    atr_period = IntParameter(10, 30, default=14, space="buy")
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy")
    ema_fast = IntParameter(5, 20, default=9, space="buy")
    ema_slow = IntParameter(20, 50, default=21, space="buy")
    
    # 动态止损参数
    stoploss_atr_mult = DecimalParameter(1.5, 3.0, default=2.0, space="buy")
    
    minimal_roi = {"0": 0.06}
    stoploss = -0.10  # 10% 硬止损（兜底）
    
    timeframe = '15m'
    
    # 追踪止盈
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
    
    # 信号强度阈值
    signal_strength_threshold = 3  # 至少 3 分才入场
    
    def informative_pairs(self):
        """获取多时间框架数据"""
        return [
            ("BTC/USDT:USDT", "1h"),
            ("BTC/USDT:USDT", "4h"),
            ("ETH/USDT:USDT", "1h"),
            ("ETH/USDT:USDT", "4h"),
            ("SOL/USDT:USDT", "1h"),
            ("SOL/USDT:USDT", "4h"),
            ("DOGE/USDT:USDT", "1h"),
            ("DOGE/USDT:USDT", "4h"),
        ]
    
    def supertrend(self, dataframe, period=14, multiplier=3):
        """计算 Supertrend"""
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
    
    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        """动态杠杆 - 根据信号强度调整"""
        # 默认 2x，信号强时可提升
        return min(self.leverage_default, max_leverage)
    
    def custom_stoploss(self, pair: str, trade, current_time: datetime, current_rate: float,
                        current_profit: float, **kwargs) -> Optional[float]:
        """动态止损 - 基于 ATR"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return None
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle.get('atr', 0)
        
        if atr <= 0:
            return None
        
        # 动态止损 = ATR * 倍数
        atr_stoploss = (atr / current_rate) * self.stoploss_atr_mult.value
        
        # 限制范围：最小 5%，最大 15%
        atr_stoploss = max(-0.15, min(-0.05, -atr_stoploss))
        
        return atr_stoploss
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        
        # === 基础指标 ===
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Supertrend
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value
        )
        
        # 动量指标
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # 波动率
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = dataframe['atr'] / dataframe['close'] * 100
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # === 多时间框架趋势 ===
        # 尝试获取 1h 数据
        inf_1h = self.dp.get_pair_dataframe(pair, "1h")
        if inf_1h is not None and len(inf_1h) > 0:
            dataframe['trend_1h'] = ta.EMA(inf_1h, timeperiod=50).iloc[-1] if len(inf_1h) > 50 else None
            dataframe['trend_1h_bull'] = inf_1h['close'].iloc[-1] > dataframe['trend_1h'] if dataframe['trend_1h'] else False
        else:
            dataframe['trend_1h_bull'] = None
        
        # 尝试获取 4h 数据
        inf_4h = self.dp.get_pair_dataframe(pair, "4h")
        if inf_4h is not None and len(inf_4h) > 0:
            dataframe['trend_4h'] = ta.EMA(inf_4h, timeperiod=50).iloc[-1] if len(inf_4h) > 50 else None
            dataframe['trend_4h_bull'] = inf_4h['close'].iloc[-1] > dataframe['trend_4h'] if dataframe['trend_4h'] else False
        else:
            dataframe['trend_4h_bull'] = None
        
        # 趋势一致性
        dataframe['trend_aligned_long'] = (
            (dataframe['trend_1h_bull'] == True) & 
            (dataframe['trend_4h_bull'] == True)
        ) | (dataframe['trend_1h_bull'].isna())  # 无数据时不限制
        
        dataframe['trend_aligned_short'] = (
            (dataframe['trend_1h_bull'] == False) & 
            (dataframe['trend_4h_bull'] == False)
        ) | (dataframe['trend_1h_bull'].isna())
        
        # === 信号强度评分 ===
        # 做多评分
        long_score = 0
        long_score += (dataframe['st_dir'] == 1).astype(int) * 1  # Supertrend 做多
        long_score += (dataframe['ema_fast'] > dataframe['ema_slow']).astype(int) * 1  # EMA 多头
        long_score += (dataframe['adx'] > 20).astype(int) * 1  # 趋势强度
        long_score += (dataframe['rsi'] < 70).astype(int) * 1  # RSI 未超买
        long_score += (dataframe['volume_ratio'] > 1).astype(int) * 1  # 成交量放大
        long_score += dataframe['trend_aligned_long'].astype(int) * 1  # 多时间框架一致
        
        dataframe['long_score'] = long_score
        
        # 做空评分
        short_score = 0
        short_score += (dataframe['st_dir'] == -1).astype(int) * 1
        short_score += (dataframe['ema_fast'] < dataframe['ema_slow']).astype(int) * 1
        short_score += (dataframe['adx'] > 15).astype(int) * 1  # 放宽
        short_score += (dataframe['rsi'] > 25).astype(int) * 1
        short_score += (dataframe['volume_ratio'] > 0.8).astype(int) * 1  # 放宽
        short_score += dataframe['trend_aligned_short'].astype(int) * 1
        
        dataframe['short_score'] = short_score
        
        # 趋势判断
        dataframe['is_uptrend'] = dataframe['close'] > dataframe['ema_200']
        dataframe['is_downtrend'] = dataframe['close'] < dataframe['ema_200']
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多 - 多因子评分"""
        dataframe.loc[:, 'enter_long'] = 0
        
        # 信号强度 >= 阈值
        conditions = [
            dataframe['long_score'] >= self.signal_strength_threshold,
            dataframe['close'] > dataframe['supertrend'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        conditions = [dataframe['st_dir'] == -1]
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        return dataframe
    
    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空 - 多因子评分"""
        dataframe.loc[:, 'enter_short'] = 0
        
        # 信号强度 >= 阈值（做空阈值降低）
        conditions = [
            dataframe['short_score'] >= (self.signal_strength_threshold - 1),  # 降低1分
            dataframe['close'] < dataframe['supertrend'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_short'] = 0
        conditions = [dataframe['st_dir'] == 1]
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_short'] = 1
        return dataframe
