# SupertrendFuturesStrategyV8_3 - 高频版
# 放宽 Alpha#101 阈值，提升交易频率

import numpy as np
import pandas as pd
from pandas import DataFrame
from functools import reduce
import talib.abstract as ta
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter

class SupertrendFuturesStrategyV8_3(IStrategy):
    """
    V8.3: 高频版
    
    唯一改动：Alpha#101 阈值 0.1 → 0.05
    
    预期效果：
    - 交易频率：30 → 45+ (提升50%)
    - 胜率：70% → 65-68% (略降)
    - 收益：保持 8-10%
    """
    
    INTERFACE_VERSION = 3
    atr_period = IntParameter(5, 30, default=11, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=2.884, space="buy")
    ema_fast = IntParameter(5, 50, default=48, space="buy")
    ema_slow = IntParameter(20, 200, default=151, space="buy")
    adx_threshold_long = IntParameter(20, 35, default=33, space="buy")
    adx_threshold_short = IntParameter(15, 30, default=23, space="buy")
    alpha_threshold = DecimalParameter(0.02, 0.10, default=0.05, space="buy")  # 降低到0.05

    minimal_roi = {"0": 0.06}
    stoploss = -0.03
    timeframe = '30m'
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    startup_candle_count = 200
    order_types = {'entry': 'limit', 'exit': 'limit', 'stoploss': 'market', 'stoploss_on_exchange': False}
    can_short: bool = True
    leverage_default = 2

    def supertrend(self, dataframe, period=14, multiplier=3):
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
        return min(self.leverage_default, max_leverage)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_pos'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['adx_neg'] = ta.MINUS_DI(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['is_uptrend'] = dataframe['close'] > dataframe['ema_200']
        dataframe['is_downtrend'] = dataframe['close'] < dataframe['ema_200']
        dataframe['alpha_101'] = (dataframe['close'] - dataframe['open']) / (dataframe['high'] - dataframe['low'] + 0.001)
        dataframe['alpha_54'] = (dataframe['close'] - dataframe['close'].shift(5)) / dataframe['close'].shift(5)
        dataframe['volatility_ratio'] = dataframe['atr'] / dataframe['close']
        dataframe['trend_score'] = 0
        dataframe.loc[dataframe['adx'] > 30, 'trend_score'] += 1
        dataframe.loc[dataframe['adx'] > 35, 'trend_score'] += 1
        dataframe.loc[abs(dataframe['alpha_54']) > 0.05, 'trend_score'] += 1
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        conditions = [
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_long.value,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
            (dataframe['rsi'] > 40) & (dataframe['rsi'] < 75),
            dataframe['alpha_101'] > self.alpha_threshold.value,  # 0.05 更宽松
            dataframe['volume'] > dataframe['volume_ma'] * 1.2,
            dataframe['trend_score'] >= 1,
            dataframe['volatility_ratio'] < 0.05,
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
        dataframe.loc[:, 'enter_short'] = 0
        conditions = [
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_short.value,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
            (dataframe['rsi'] > 25) & (dataframe['rsi'] < 60),
            dataframe['alpha_101'] < -self.alpha_threshold.value,
            dataframe['volume'] > dataframe['volume_ma'] * 1.2,
            dataframe['trend_score'] >= 1,
            dataframe['volatility_ratio'] < 0.05,
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
