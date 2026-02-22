# 智能自适应策略
# 自动检测市场状态，在策略内部切换逻辑
# 不需要重启机器人！
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
from functools import reduce

class AdaptiveStrategy(IStrategy):
    """
    智能自适应策略
    - 自动检测市场状态（趋势/震荡/高波动）
    - 根据状态切换入场逻辑
    - 无需重启机器人
    """
    
    INTERFACE_VERSION = 3
    
    # 通用参数
    adx_trend_threshold = IntParameter(20, 30, default=25, space="buy", optimize=True)
    volatility_threshold = DecimalParameter(2.0, 4.0, default=3.0, space="buy", optimize=True)
    
    # Supertrend 参数 (趋势模式)
    atr_period = IntParameter(10, 30, default=14, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy", optimize=True)
    
    # RSI 参数 (震荡模式)
    rsi_oversold = IntParameter(25, 35, default=30, space="buy", optimize=True)
    rsi_overbought = IntParameter(65, 75, default=70, space="sell", optimize=True)
    
    minimal_roi = {"0": 0.08}
    stoploss = -0.05
    
    timeframe = '15m'
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
    
    startup_candle_count = 200
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    # 存储市场状态
    market_state = 'unknown'
    
    def detect_market_state(self, dataframe: DataFrame) -> str:
        """检测当前市场状态"""
        last = dataframe.iloc[-1]
        
        adx = last.get('adx', 20)
        atr_pct = last.get('atr_pct', 2)
        trend_slope = last.get('trend_slope', 0)
        
        # 高波动
        if atr_pct > self.volatility_threshold.value:
            return 'volatile'
        
        # 趋势市场
        if adx > self.adx_trend_threshold.value:
            if trend_slope > 0:
                return 'trend_up'
            else:
                return 'trend_down'
        
        # 震荡市场
        return 'ranging'
    
    def supertrend(self, dataframe, period=14, multiplier=3):
        """计算 Supertrend"""
        import pandas as pd
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
        import pandas as pd
        
        # === 通用指标 ===
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        # === 趋势指标 ===
        # Supertrend
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, 
            period=self.atr_period.value, 
            multiplier=self.atr_multiplier.value
        )
        
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=21)
        
        # 趋势斜率 (线性回归)
        close_series = dataframe['close'].rolling(20).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 20 else 0,
            raw=False
        )
        dataframe['trend_slope'] = close_series / dataframe['close'] * 100  # 百分比
        
        # === 震荡指标 ===
        # 布林带
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_position'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower']) * 100
        
        # 检测市场状态
        self.market_state = self.detect_market_state(dataframe)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        
        # 根据市场状态使用不同的入场逻辑
        if self.market_state == 'trend_up':
            # 上涨趋势 - 追涨
            conditions = [
                dataframe['st_dir'] == 1,
                dataframe['close'] > dataframe['supertrend'],
                dataframe['rsi'] < 70,
                dataframe['volume'] > dataframe['volume_ma'],
            ]
        elif self.market_state == 'trend_down':
            # 下跌趋势 - 谨慎
            conditions = [
                dataframe['st_dir'] == 1,
                dataframe['close'] > dataframe['supertrend'],
                dataframe['rsi'] < 60,  # 更保守
                dataframe['adx'] > 20,  # 确认趋势
                dataframe['volume'] > dataframe['volume_ma'] * 1.2,
            ]
        elif self.market_state == 'volatile':
            # 高波动 - 综合
            conditions = [
                dataframe['st_dir'] == 1,
                dataframe['ema_fast'] > dataframe['ema_slow'],
                dataframe['rsi'] < 65,
                dataframe['bb_position'] < 70,
                dataframe['volume'] > dataframe['volume_ma'],
            ]
        else:  # ranging
            # 震荡 - 均值回归
            conditions = [
                dataframe['rsi'] < self.rsi_oversold.value,
                dataframe['bb_position'] < 25,
                dataframe['volume'] > dataframe['volume_ma'],
            ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        # 根据市场状态使用不同的出场逻辑
        if self.market_state in ['trend_up', 'trend_down']:
            # 趋势市场 - Supertrend 反转
            conditions = [dataframe['st_dir'] == -1]
        elif self.market_state == 'volatile':
            # 高波动 - 快速止盈
            conditions = [
                (dataframe['rsi'] > 70) | (dataframe['bb_position'] > 75)
            ]
        else:  # ranging
            # 震荡 - RSI 超买
            conditions = [dataframe['rsi'] > self.rsi_overbought.value]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
    
    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, 
                           current_time, entry_tag, side, **kwargs):
        """入场确认 - 记录市场状态"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) > 0:
            state = self.detect_market_state(dataframe)
            # 可以在这里添加日志
        return True
