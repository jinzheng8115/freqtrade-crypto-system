# SupertrendStrategyV2_5 - V2 + 动态止损（无DCA）
# 保持V2简洁，只加入动态止损锁定利润
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from functools import reduce

class SupertrendStrategyV2_5(IStrategy):
    INTERFACE_VERSION = 3
    
    # 策略参数（保持V2优化值）
    atr_period = IntParameter(10, 30, default=28, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.936, space="buy", optimize=True)
    ema_fast = IntParameter(5, 20, default=17, space="buy", optimize=True)
    ema_slow = IntParameter(20, 50, default=49, space="buy", optimize=True)
    rsi_threshold = IntParameter(60, 80, default=70, space="buy", optimize=True)
    adx_threshold = IntParameter(15, 35, default=20, space="buy", optimize=True)
    
    # 动态止损参数
    initial_stoploss = -0.06  # 初始6%
    profit_level_1 = 0.03; stoploss_level_1 = -0.03  # +3% → -3%
    profit_level_2 = 0.05; stoploss_level_2 = -0.02  # +5% → -2%
    profit_level_3 = 0.08; stoploss_level_3 = 0.0    # +8% → 保本
    
    minimal_roi = {"0": 0.10}
    stoploss = -0.08
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    
    startup_candle_count = 200
    
    order_types = {'entry': 'limit', 'exit': 'limit', 'stoploss': 'market', 'stoploss_on_exchange': False}
    
    def supertrend(self, dataframe, period=14, multiplier=3):
        df = dataframe.copy()
        hl2 = (df['high'] + df['low']) / 2
        atr = ta.ATR(df, timeperiod=period)
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)
        supertrend = [0] * len(df)
        direction = [1] * len(df)
        for i in range(1, len(df)):
            if df['close'].iloc[i] > upperband.iloc[i-1]: direction[i] = 1
            elif df['close'].iloc[i] < lowerband.iloc[i-1]: direction[i] = -1
            else: direction[i] = direction[i-1]
            supertrend[i] = lowerband.iloc[i] if direction[i] == 1 else upperband.iloc[i]
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        conditions = [
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold.value,
            dataframe['rsi'] < self.rsi_threshold.value,
            dataframe['volume'] > dataframe['volume_ma'],
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
    
    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float, current_profit: float, after_fill: bool, **kwargs) -> float:
        """动态止损：盈利越多，止损越紧"""
        if current_profit >= self.profit_level_3: return self.stoploss_level_3
        elif current_profit >= self.profit_level_2: return self.stoploss_level_2
        elif current_profit >= self.profit_level_1: return self.stoploss_level_1
        return self.initial_stoploss
