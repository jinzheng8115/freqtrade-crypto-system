# SupertrendFuturesStrategyV4_10x - 10倍杠杆测试版
# 仅用于测试杠杆影响

import sys
sys.path.insert(0, '/freqtrade/user_data/strategies')
from SupertrendFuturesStrategyV4 import SupertrendFuturesStrategyV4

class SupertrendFuturesStrategyV4_10x(SupertrendFuturesStrategyV4):
    leverage_default = 10  # 10倍杠杆
