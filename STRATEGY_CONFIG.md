# Freqtrade 多交易对策略配置

> 最后更新: 2026-02-23

## 当前配置

### 策略
- **策略名称**: `MultiPairFuturesStrategy`
- **策略类型**: 多交易对独立参数策略
- **时间周期**: 30分钟
- **交易模式**: 合约交易 (Futures)
- **交易所**: OKX

### 交易对 (4个)
| 交易对 | 特点 | 入场过滤 |
|--------|------|----------|
| DOGE | 波动大 | 标准趋势跟踪 |
| UNI | 中等波动 | RSI 70/30 过滤 |
| SUI | 新加入 | 优化参数 |
| BONK | Meme币 | 成交量确认过滤 |

### 资金管理
```json
{
  "dry_run": true,           // 模拟模式
  "dry_run_wallet": 5000,    // 模拟资金: 5000 USDT
  "stake_amount": 250,       // 每笔交易: 250 USDT
  "max_open_trades": 4,      // 最大同时持仓: 4
  "leverage": 2,             // 杠杆倍数: 2x
  "stoploss": -0.03,         // 止损: 3%
  "trailing_stop": true      // 追踪止损
}
```

### 风控参数
- **基础仓位**: 250 USDT/笔
- **波动率动态调整**:
  - 波动率 < 2% → 333 USDT (+33%)
  - 波动率 2-4% → 250 USDT (标准)
  - 波动率 4-6% → 167 USDT (-33%)
  - 波动率 > 6% → 125 USDT (-50%)

### 技术指标
| 指标 | 用途 |
|------|------|
| Supertrend | 趋势方向 |
| ADX | 趋势强度 |
| Alpha | 动量确认 |
| EMA 快/慢 | 趋势方向确认 |
| RSI | 超买超卖过滤 (UNI) |
| Volume MA | 成交量确认 (BONK) |

## 优化参数

参数通过 Hyperopt 优化（Sharpe Ratio 目标）

### DOGE (已验证)
```python
adx_threshold_long: 31
adx_threshold_short: 15
alpha_threshold: 0.035
atr_multiplier: 4.344
ema_fast: 48
ema_slow: 167
```

### UNI
```python
adx_threshold_long: 26.12
adx_threshold_short: 17.45
alpha_threshold: 0.029
atr_multiplier: 3.648
ema_fast: 34
ema_slow: 178
```

### SUI
```python
adx_threshold_long: 37.36
adx_threshold_short: 13.51
alpha_threshold: 0.038
atr_multiplier: 4.873
ema_fast: 54
ema_slow: 161
```

### BONK
```python
adx_threshold_long: 27.99
adx_threshold_short: 11.29
alpha_threshold: 0.027
atr_multiplier: 3.724
ema_fast: 40
ema_slow: 146
```

## 回测表现 (2025-01-01 至 2026-02-23)

| 指标 | 数值 |
|------|------|
| 总交易次数 | 55 |
| 胜率 | 58.2% |
| 平均收益 | 0.84% |
| 总收益 | +10.52% |
| 最大回撤 | 3.76% |

## 文件说明

```
/user_data/
├── config_futures.json      # 合约配置 (未提交到git，含敏感信息)
├── config_futures.example.json  # 配置示例
├── strategies/
│   └── MultiPairFuturesStrategy.py  # 策略文件
└── hyperopt_results/
    └── strategy_MultiPairFuturesStrategy.json  # 优化参数
```

## 启动命令

```bash
docker compose up -d freqtrade-futures
```

## 监控

- Telegram 通知已启用
- 每次交易会自动发送波动率和仓位信息
- 每周检查一次表现

## 注意事项

1. **模拟模式**: 当前为 dry_run=true，所有交易都是模拟
2. **观察期**: 新配置需要 1-2 周观察期验证表现
3. **风险**: 加密货币交易存在风险，过往表现不代表未来
