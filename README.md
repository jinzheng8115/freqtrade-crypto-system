# Freqtrade 合约交易策略

> 基于 Supertrend 指标的趋势跟踪策略，支持做多和做空

## 📊 最新优化结果 (2026-02-22)

### 策略表现

| 指标 | 数值 | 备注 |
|------|------|------|
| **总收益** | +7.47% | 90天回测 |
| **胜率** | 63.6% | 35胜/20负 |
| **交易次数** | 55 次 | 平均持仓 5h51m |
| **最大回撤** | 5.35% | 风险可控 |
| **夏普比率** | -0.37 | 待优化 |

### 时间周期对比

| 周期 | 总收益 | 胜率 | 最大回撤 | 结论 |
|------|--------|------|---------|------|
| 5m | -5.67% | 21.2% | 5.95% | ❌ 不推荐 |
| **15m** | **-10.23%** | **27.5%** | **12.36%** | ❌ 表现最差 |
| **30m** | **+7.47%** | **63.6%** | **5.35%** | ✅ **最优** |

**结论**: 30m 周期表现显著优于 15m，收益提升 8.86%，胜率提升 61%

---

## 🎯 策略配置

### 当前参数 (SupertrendFuturesStrategyV4)

```python
# 时间框架
timeframe = '30m'

# 买入参数 (2026-02-22 优化)
buy_params = {
    "adx_threshold_long": 33,      # ADX 做多阈值
    "adx_threshold_short": 23,     # ADX 做空阈值
    "atr_multiplier": 2.884,       # ATR 倍数
    "atr_period": 11,              # ATR 周期
    "ema_fast": 48,                # 快速 EMA
    "ema_slow": 151,               # 慢速 EMA
}

# 止盈止损
minimal_roi = {"0": 0.06}          # 6% 目标收益
stoploss = -0.03                   # 3% 止损

# 追踪止损
trailing_stop = True
trailing_stop_positive = 0.02      # 2% 后启动追踪
trailing_stop_positive_offset = 0.03
trailing_only_offset_is_reached = True
```

### 交易对

- BTC/USDT:USDT
- ETH/USDT:USDT
- SOL/USDT:USDT
- DOGE/USDT:USDT

### 风险管理

- **最大持仓**: 2 个
- **单笔仓位**: 400 USDT
- **杠杆**: 2x (可调)
- **交易所**: OKX

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone <your-repo-url>
cd freqtrade

# 启动 Docker
docker compose up -d
```

### 2. 配置

```bash
# 复制配置文件
cp user_data/config_futures.json.example user_data/config_futures.json

# 编辑配置
vim user_data/config_futures.json
# 填入你的 API Key、Secret、Password
```

### 3. 下载历史数据

```bash
docker exec freqtrade-futures freqtrade download-data \
  --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT \
  --timeframe 30m \
  --days 90
```

### 4. 回测

```bash
docker exec freqtrade-futures freqtrade backtesting \
  --strategy SupertrendFuturesStrategyV4 \
  --timeframe 30m \
  --timerange 20251124-20260222
```

### 5. 参数优化

```bash
docker exec freqtrade-futures freqtrade hyperopt \
  --strategy SupertrendFuturesStrategyV4 \
  --timeframe 30m \
  --epochs 50 \
  --spaces buy \
  --hyperopt-loss ProfitDrawDownHyperOptLoss
```

### 6. 实盘运行

```bash
# 修改 config_futures.json
"dry_run": false  # 改为 false 启用实盘

# 重启
docker compose restart freqtrade-futures
```

---

## 📁 目录结构

```
/root/freqtrade/
├── docker-compose.yml
├── README.md
├── user_data/
│   ├── config_futures.json      # 合约配置
│   ├── config_spot.json         # 现货配置
│   ├── strategies/
│   │   ├── SupertrendFuturesStrategyV4.py    # 当前策略
│   │   └── SupertrendFuturesStrategyV4.json  # 优化参数
│   ├── data/                    # 历史数据
│   └── logs/                    # 日志文件
└── Dockerfile
```

---

## 📈 策略逻辑

### Supertrend 指标

**核心原理**: 基于 ATR 的趋势跟踪指标

**计算公式**:
```
Upper Band = (High + Low) / 2 + (ATR × Multiplier)
Lower Band = (High + Low) / 2 - (ATR × Multiplier)
```

### 做多条件

1. 价格突破 Supertrend 上轨
2. 快速 EMA > 慢速 EMA (趋势确认)
3. ADX > 33 (趋势强度)
4. ADX+ > ADX- (多头动能)
5. 成交量 > 20 周期均值

### 做空条件

1. 价格跌破 Supertrend 下轨
2. 快速 EMA < 慢速 EMA (趋势确认)
3. ADX > 23 (趋势强度)
4. ADX- > ADX+ (空头动能)
5. 成交量 > 20 周期均值

### 退出条件

- **止盈**: 6% 目标收益
- **止损**: 3% 固定止损
- **追踪止损**: 盈利 2% 后启动，追踪 3%
- **信号退出**: Supertrend 反转

---

## 🔄 优化历史

### 2026-02-22 - 时间周期优化

**问题**: 15m 周期表现不佳 (-10.23% 回撤)

**方案**: 对比 5m / 15m / 30m 三个周期

**结果**:
- 30m 周期表现最优 (+7.47%)
- 胜率从 27.5% 提升到 63.6%
- 回撤从 12.36% 降到 5.35%

**参数调整**:
- ATR Period: 29 → 11 (更敏感)
- ATR Multiplier: 3.476 → 2.884 (更紧)
- EMA Fast: 37 → 48
- EMA Slow: 174 → 151

---

## ⚠️ 风险提示

1. **回测 ≠ 实盘**: 回测表现不代表未来收益
2. **市场风险**: 加密货币市场波动巨大
3. **策略风险**: 趋势策略在震荡市场表现不佳
4. **杠杆风险**: 2x 杠杆会放大亏损
5. **技术风险**: API 故障、网络问题等

**建议**:
- 先在 dry_run 模式测试 1-2 周
- 实盘初期使用小资金 (如 100 USDT)
- 定期监控机器人状态
- 设置合理的止损

---

## 📚 参考资料

- [Freqtrade 官方文档](https://www.freqtrade.io/en/stable/)
- [Supertrend 指标说明](https://www.tradingview.com/support/articles/en-us/44061974187-supertrend/)
- [OKX API 文档](https://www.okx.com/docs-v5/)

---

## 📝 更新日志

### 2026-02-22
- ✅ 切换到 30m 时间周期
- ✅ 完成参数优化 (50 轮)
- ✅ 应用优化参数
- ✅ 收益从 -1.39% 提升到 +7.47%

### 2026-02-21
- ✅ 创建 SupertrendFuturesStrategyV4
- ✅ 初步参数优化 (15m 周期)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License

---

**免责声明**: 本策略仅供学习和研究使用，不构成投资建议。使用本策略进行实盘交易的所有风险由使用者自行承担。
