# SupertrendStrategyV3 - DCA + 动态止损
# 改进点：
# 1. DCA 加仓 - 亏损时按比例加仓
# 2. 动态止损 - 根据盈利情况收紧止损
# 3. 保持4个交易对
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from functools import reduce
from datetime import datetime

class SupertrendStrategyV3(IStrategy):
    INTERFACE_VERSION = 3
    
    # Supertrend 参数
    atr_period = IntParameter(10, 30, default=14, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy", optimize=True)
    
    # ADX 趋势过滤
    adx_threshold = IntParameter(15, 30, default=20, space="buy", optimize=True)
    
    # DCA 加仓参数
    dca_start = DecimalParameter(-0.02, -0.05, default=-0.03, space="buy", optimize=True)  # 亏损3%开始加仓
    dca_step = DecimalParameter(-0.02, -0.04, default=-0.03, space="buy", optimize=True)   # 每跌3%加一次
    max_dca_trades = 3  # 最多加仓3次
    
    # 动态止损参数
    initial_stoploss = DecimalParameter(-0.05, -0.08, default=-0.06, space="sell", optimize=True)  # 初始止损6%
    profit_level_1 = DecimalParameter(0.02, 0.04, default=0.03, space="sell", optimize=True)  # 盈利3%
    stoploss_level_1 = DecimalParameter(-0.02, -0.04, default=-0.03, space="sell", optimize=True)  # 止损收紧到3%
    profit_level_2 = DecimalParameter(0.04, 0.07, default=0.05, space="sell", optimize=True)  # 盈利5%
    stoploss_level_2 = DecimalParameter(-0.01, -0.03, default=-0.02, space="sell", optimize=True)  # 止损收紧到2%
    profit_level_3 = DecimalParameter(0.07, 0.10, default=0.08, space="sell", optimize=True)  # 盈利8%
    stoploss_level_3 = DecimalParameter(0.0, -0.02, default=0.0, space="sell", optimize=True)  # 保本止损
    
    minimal_roi = {"0": 0.12}  # 12% 止盈
    stoploss = -0.10  # 硬止损10%（最后防线）
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    
    startup_candle_count = 200
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    # DCA 加仓设置
    position_adjustment_enable = True
    max_entry_position_adjustment = 3  # 最多加仓3次
    
    # 存储每个交易对的加仓信息
    custom_info_trail = {}
    
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
        # Supertrend
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, 
            period=self.atr_period.value, 
            multiplier=self.atr_multiplier.value
        )
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=21)
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 1. Supertrend 看涨
            dataframe['st_dir'] == 1,
            
            # 2. EMA 多头排列
            dataframe['ema_fast'] > dataframe['ema_slow'],
            
            # 3. ADX 显示有趋势
            dataframe['adx'] > self.adx_threshold.value,
            
            # 4. RSI 不超买
            dataframe['rsi'] < 70,
            
            # 5. 成交量确认
            dataframe['volume'] > dataframe['volume_ma'],
            
            # 6. 价格在 Supertrend 之上
            dataframe['close'] > dataframe['supertrend'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            dataframe['st_dir'] == -1,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
    
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: float, max_stake: float,
                           leverage: float, entry_tag: str, side: str, **kwargs) -> float:
        """
        DCA 加仓逻辑
        - 首次入场：100% 基础仓位
        - 亏损 3%：加仓 50%
        - 亏损 6%：加仓 50%
        - 亏损 9%：加仓 50%
        """
        # 获取当前交易信息
        trades = self.trades
        
        # 查找该交易对的现有持仓
        current_trade = None
        for trade in trades:
            if trade.pair == pair and trade.is_open:
                current_trade = trade
                break
        
        if current_trade is None:
            # 首次入场，使用标准仓位
            return proposed_stake
        
        # 计算当前盈亏比例
        current_profit = (current_rate - current_trade.open_rate) / current_trade.open_rate
        
        # 检查是否应该加仓
        # 计算已经加仓次数
        dca_count = current_trade.nr_of_successful_buys - 1 if hasattr(current_trade, 'nr_of_successful_buys') else 0
        
        if dca_count >= self.max_dca_trades:
            # 已达最大加仓次数
            return 0
        
        # 判断是否需要加仓
        dca_threshold = self.dca_start.value - (dca_count * self.dca_step.value)
        
        if current_profit <= dca_threshold:
            # 触发加仓，使用 50% 基础仓位
            return proposed_stake * 0.5
        
        # 不加仓
        return 0
    
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float:
        """
        动态止损逻辑
        - 初始止损: -6%
        - 盈利 3%: 止损收紧到 -3%
        - 盈利 5%: 止损收紧到 -2%
        - 盈利 8%: 保本止损 (0%)
        """
        # 默认使用初始止损
        stoploss = self.initial_stoploss.value
        
        # 根据盈利情况动态调整
        if current_profit >= self.profit_level_3.value:
            # 盈利 8%+ → 保本止损
            stoploss = self.stoploss_level_3.value
        elif current_profit >= self.profit_level_2.value:
            # 盈利 5%+ → 止损 -2%
            stoploss = self.stoploss_level_2.value
        elif current_profit >= self.profit_level_1.value:
            # 盈利 3%+ → 止损 -3%
            stoploss = self.stoploss_level_1.value
        
        return stoploss
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: str,
                           side: str, **kwargs) -> bool:
        """入场确认"""
        return True
