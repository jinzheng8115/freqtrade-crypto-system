# SupertrendStrategyV3C - 保守版 DCA + 动态止损
# 改进：DCA 只在反弹信号确认时加仓，而不是单纯亏损就加
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from functools import reduce
from datetime import datetime

class SupertrendStrategyV3C(IStrategy):
    INTERFACE_VERSION = 3
    
    # Supertrend 参数
    atr_period = IntParameter(10, 30, default=14, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy", optimize=True)
    adx_threshold = IntParameter(15, 30, default=20, space="buy", optimize=True)
    
    # DCA 加仓参数（保守版）
    dca_trigger_profit = DecimalParameter(-0.03, -0.06, default=-0.04, space="buy")  # 亏损4%才考虑加仓
    max_dca_trades = 2  # 最多加仓2次（更保守）
    dca_stake_ratio = 0.3  # 加仓金额为初始仓位的30%
    
    # 动态止损参数（保持不变）
    initial_stoploss = -0.06  # 初始止损6%
    profit_level_1 = 0.03   # 盈利3%
    stoploss_level_1 = -0.03  # 止损收紧到3%
    profit_level_2 = 0.05   # 盈利5%
    stoploss_level_2 = -0.02  # 止损收紧到2%
    profit_level_3 = 0.08   # 盈利8%
    stoploss_level_3 = 0.0  # 保本止损
    
    minimal_roi = {"0": 0.10}
    stoploss = -0.08
    
    timeframe = '15m'
    
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
    
    position_adjustment_enable = True
    max_entry_position_adjustment = 2
    
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
            if direction[i] == 1:
                supertrend[i] = lowerband.iloc[i]
            else:
                supertrend[i] = upperband.iloc[i]
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=self.atr_multiplier.value
        )
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        # 反弹信号：RSI 开始上升
        dataframe['rsi_rising'] = dataframe['rsi'] > dataframe['rsi'].shift(1)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        conditions = [
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold.value,
            dataframe['rsi'] < 70,
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
    
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: float, max_stake: float,
                           leverage: float, entry_tag: str, side: str, **kwargs) -> float:
        """
        保守版 DCA：只在以下条件同时满足时加仓
        1. 亏损超过阈值（如4%）
        2. RSI 开始上升（反弹信号）
        3. 价格在 Supertrend 之上
        """
        trades = self.trades
        current_trade = None
        for trade in trades:
            if trade.pair == pair and trade.is_open:
                current_trade = trade
                break
        
        if current_trade is None:
            return proposed_stake  # 首次入场
        
        # 计算当前盈亏
        current_profit = (current_rate - current_trade.open_rate) / current_trade.open_rate
        
        # 计算已加仓次数
        dca_count = current_trade.nr_of_successful_buys - 1 if hasattr(current_trade, 'nr_of_successful_buys') else 0
        
        if dca_count >= self.max_dca_trades:
            return 0  # 已达最大加仓次数
        
        # 获取当前市场数据
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 2:
            return 0
        
        last_candle = dataframe.iloc[-1]
        
        # 保守加仓条件：必须同时满足
        should_dca = (
            current_profit <= self.dca_trigger_profit.value and  # 亏损足够
            last_candle['rsi_rising'] and  # RSI 上升
            last_candle['st_dir'] == 1 and  # Supertrend 仍看涨
            last_candle['close'] > last_candle['supertrend']  # 价格在支撑之上
        )
        
        if should_dca:
            return proposed_stake * self.dca_stake_ratio  # 加仓30%
        
        return 0
    
    def custom_stoploss(self, pair: str, trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float:
        """动态止损"""
        if current_profit >= self.profit_level_3:
            return self.stoploss_level_3
        elif current_profit >= self.profit_level_2:
            return self.stoploss_level_2
        elif current_profit >= self.profit_level_1:
            return self.stoploss_level_1
        return self.initial_stoploss
