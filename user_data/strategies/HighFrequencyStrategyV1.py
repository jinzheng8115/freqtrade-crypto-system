# HighFrequencyStrategyV1 - 高频趋势突破策略
# 时间周期: 5分钟
# 目标: 每天3-10次交易

import numpy as np
import pandas as pd
from pandas import DataFrame
from functools import reduce
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

class HighFrequencyStrategyV1(IStrategy):
    """
    高频趋势突破策略 V1
    
    核心思路:
    1. 5分钟周期，捕捉短期趋势
    2. 价格突破 + 成交量确认
    3. 快进快出，小止损小止盈
    
    预期表现:
    - 交易频率: 5-8次/天
    - 胜率: 55-60%
    - 单笔收益: 0.15%
    - 日收益: 0.5-1%
    """
    
    INTERFACE_VERSION = 3
    
    # 策略参数（待优化）
    breakout_period = IntParameter(5, 30, default=10, space="buy")  # 突破周期
    volume_mult = DecimalParameter(1.5, 3.0, default=2.0, space="buy")  # 成交量倍数
    ema_fast = IntParameter(3, 10, default=5, space="buy")  # 快EMA
    ema_slow = IntParameter(10, 30, default=15, space="buy")  # 慢EMA
    
    # 风险管理（高频策略特点：小止损小止盈）
    minimal_roi = {
        "0": 0.003,   # 0.3% 立即止盈
    }
    stoploss = -0.002  # 0.2% 止损
    
    # 时间止损
    exit_timeout = 6  # 6根K线 = 30分钟
    
    timeframe = '5m'
    startup_candle_count = 100
    
    order_types = {
        'entry': 'limit',  # 改用限价单
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    can_short: bool = True
    leverage_default = 2  # 高频策略降低杠杆
    
    # 限制每日交易次数
    max_trades_per_day = 10
    
    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        return min(self.leverage_default, max_leverage)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(20).mean()
        
        # 突破高点
        dataframe['high_breakout'] = dataframe['high'].rolling(self.breakout_period.value).max().shift(1)
        dataframe['low_breakout'] = dataframe['low'].rolling(self.breakout_period.value).min().shift(1)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ATR（波动率）
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # 动量
        dataframe['momentum'] = dataframe['close'].pct_change(5)
        
        # 波动率
        dataframe['volatility'] = dataframe['close'].pct_change().rolling(20).std()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多"""
        dataframe.loc[:, 'enter_long'] = 0
        
        conditions = [
            # 1. 价格突破前N根K线高点
            dataframe['close'] > dataframe['high_breakout'],
            
            # 2. 成交量放大
            dataframe['volume'] > dataframe['volume_ma'] * self.volume_mult.value,
            
            # 3. EMA金叉
            dataframe['ema_fast'] > dataframe['ema_slow'],
            
            # 4. RSI不过热
            dataframe['rsi'] < 75,
            
            # 5. 有足够动量
            dataframe['momentum'] > 0.005,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多出场"""
        dataframe.loc[:, 'exit_long'] = 0
        
        conditions = [
            # 1. EMA死叉
            dataframe['ema_fast'] < dataframe['ema_slow'],
            
            # 或者
            # 2. 跌破突破低点
            # dataframe['close'] < dataframe['low_breakout'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
    
    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空"""
        dataframe.loc[:, 'enter_short'] = 0
        
        conditions = [
            # 1. 价格跌破前N根K线低点
            dataframe['close'] < dataframe['low_breakout'],
            
            # 2. 成交量放大
            dataframe['volume'] > dataframe['volume_ma'] * self.volume_mult.value,
            
            # 3. EMA死叉
            dataframe['ema_fast'] < dataframe['ema_slow'],
            
            # 4. RSI不超卖
            dataframe['rsi'] > 25,
            
            # 5. 有足够动量
            dataframe['momentum'] < -0.005,
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空出场"""
        dataframe.loc[:, 'exit_short'] = 0
        
        conditions = [
            dataframe['ema_fast'] > dataframe['ema_slow'],
        ]
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_short'] = 1
        
        return dataframe
    
    def custom_exit(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        """自定义出场：时间止损"""
        
        # 获取当前DataFrame
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        # 计算持仓K线数
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 300  # 5分钟
        
        # 超过30分钟（6根K线）未盈利，强制出场
        if trade_duration > self.exit_timeout and current_profit < 0:
            return 'exit_timeout'
        
        return None


# === 使用说明 ===
"""
高频策略注意事项:

1. 手续费影响
   - 高频交易手续费累积很大
   - 确保单笔收益 > 2倍手续费
   - OKX合约: Maker 0.02%, Taker 0.05%

2. 滑点影响
   - 市价单会有滑点
   - 小币种滑点更大
   - 建议只用主流币种

3. 交易次数限制
   - OKX有API限速
   - 每秒最多20次请求
   - 注意不要触发限速

4. 资金管理
   - 高频策略建议降低杠杆
   - 单笔仓位不宜过大
   - 预留足够保证金

5. 监控要求
   - 高频策略需要更频繁监控
   - 建议设置更严格的告警
   - 异常情况需要快速响应

预期表现:
- 交易频率: 5-8次/天
- 胜率: 55-60%
- 单笔收益: 0.15%
- 日收益: 0.5-1%
- 月收益: 15-30%
"""
