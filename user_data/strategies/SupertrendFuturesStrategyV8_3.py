# SupertrendFuturesStrategyV8_3 - 交易对自适应版
# 为每个交易对定制参数

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Dict
from functools import reduce
import logging

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta

logger = logging.getLogger(__name__)


class SupertrendFuturesStrategyV8_3(IStrategy):
    """
    V8.3: 交易对自适应版
    
    为每个交易对定制最优参数：
    - BTC: 稳健型，大止损，长持仓
    - ETH: 平衡型，标准参数
    - XRP: 敏感型，小止损，短持仓
    - DOGE: 激进型，高波动适应
    """
    
    INTERFACE_VERSION = 3

    # 基础参数（默认值，会被交易对特定参数覆盖）
    atr_period = IntParameter(5, 30, default=21, space="buy")
    atr_multiplier = DecimalParameter(2.0, 5.0, default=4.622, space="buy")
    ema_fast = IntParameter(5, 50, default=21, space="buy")
    ema_slow = IntParameter(20, 200, default=47, space="buy")
    adx_threshold_long = IntParameter(20, 40, default=34, space="buy")
    adx_threshold_short = IntParameter(15, 35, default=23, space="buy")
    alpha_threshold = DecimalParameter(0.02, 0.15, default=0.118, space="buy")

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
    
    # 交易对特定配置
    PAIR_CONFIG: Dict[str, Dict] = {
        'BTC/USDT:USDT': {
            'stoploss': -0.04,           # BTC波动相对小，大止损避免假突破
            'atr_multiplier': 4.0,       # 更宽的通道
            'minimal_roi': {"0": 0.08},  # 更高止盈（趋势持续性强）
            'leverage': 2,
            'description': '稳健型 - 大趋势，大止损'
        },
        'ETH/USDT:USDT': {
            'stoploss': -0.03,           # 标准止损
            'atr_multiplier': 4.622,     # Hyperopt优化值
            'minimal_roi': {"0": 0.06},  # 标准止盈
            'leverage': 2,
            'description': '平衡型 - 标准参数'
        },
        'XRP/USDT:USDT': {
            'stoploss': -0.025,          # XRP波动大，更紧止损
            'atr_multiplier': 3.5,       # 更敏感的通道
            'minimal_roi': {"0": 0.05, "30": 0.03},  # 更快止盈
            'leverage': 1,               # 降低杠杆
            'description': '敏感型 - 紧止损，快止盈'
        },
        'DOGE/USDT:USDT': {
            'stoploss': -0.02,           # DOGE高波动，严格止损
            'atr_multiplier': 3.0,       # 非常敏感的通道
            'minimal_roi': {"0": 0.04, "15": 0.02},  # 快速止盈
            'leverage': 1,               # 保守杠杆
            'description': '激进型 - 严格风控'
        }
    }

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

    def get_pair_config(self, pair: str) -> Dict:
        """获取交易对特定配置"""
        return self.PAIR_CONFIG.get(pair, {
            'stoploss': -0.03,
            'atr_multiplier': 4.622,
            'minimal_roi': {"0": 0.06},
            'leverage': 2,
            'description': '默认配置'
        })

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        """根据交易对调整杠杆"""
        config = self.get_pair_config(pair)
        return min(config.get('leverage', 2), max_leverage)

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """根据交易对调整止损"""
        config = self.get_pair_config(pair)
        return config.get('stoploss', -0.03)

    def get_minimal_roi(self, pair: str) -> Dict:
        """根据交易对调整ROI"""
        config = self.get_pair_config(pair)
        return config.get('minimal_roi', {"0": 0.06})

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算技术指标"""
        
        # 获取交易对特定配置
        pair = metadata.get('pair', '')
        config = self.get_pair_config(pair)
        atr_mult = config.get('atr_multiplier', self.atr_multiplier.value)
        
        # === 核心指标 ===
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['supertrend'], dataframe['st_dir'] = self.supertrend(
            dataframe, period=self.atr_period.value, multiplier=atr_mult
        )
        
        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx_pos'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['adx_neg'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 成交量
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        
        # Alpha#101
        dataframe['alpha_101'] = (
            (dataframe['close'] - dataframe['close'].shift(5)) / dataframe['close'].shift(5) * 100 -
            (dataframe['volume'] - dataframe['volume'].shift(5)) / dataframe['volume'].shift(5) * 10
        )
        
        # 趋势判断
        dataframe['is_uptrend'] = dataframe['close'] > dataframe['supertrend']
        dataframe['is_downtrend'] = dataframe['close'] < dataframe['supertrend']
        
        # 波动率
        dataframe['volatility_ratio'] = ta.ATR(dataframe, timeperiod=14) / dataframe['close']
        
        # 记录配置（用于日志）
        dataframe['pair_config'] = config.get('description', '')
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做多"""
        dataframe.loc[:, 'enter_long'] = 0

        conditions = [
            dataframe['st_dir'] == 1,
            dataframe['ema_fast'] > dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_long.value,
            dataframe['adx_pos'] > dataframe['adx_neg'],
            dataframe['close'] > dataframe['supertrend'],
            dataframe['is_uptrend'],
            (dataframe['rsi'] > 35) & (dataframe['rsi'] < 80),
            dataframe['alpha_101'] > self.alpha_threshold.value,
            dataframe['volume'] > dataframe['volume_ma'] * 1.1,
            dataframe['volatility_ratio'] < 0.06,
        ]

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1

        return dataframe

    def populate_entry_trend_short(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """做空"""
        dataframe.loc[:, 'enter_short'] = 0

        conditions = [
            dataframe['st_dir'] == -1,
            dataframe['ema_fast'] < dataframe['ema_slow'],
            dataframe['adx'] > self.adx_threshold_short.value,
            dataframe['adx_neg'] > dataframe['adx_pos'],
            dataframe['close'] < dataframe['supertrend'],
            dataframe['is_downtrend'],
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
        config = self.get_pair_config(pair)
        logger.info(f"交易对 {pair}: {config.get('description', '')}")
        return True
