<div align="center">

# Freqtrade 加密货币交易系统
# Freqtrade Crypto Trading System

[![Freqtrade](https://img.shields.io/badge/Freqtrade-2026.1-blue)](https://github.com/freqtrade/freqtrade)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Running-brightgreen)]()

**[中文文档](#中文) | [English Docs](#english)**

</div>

---

<a name="中文"></a>
## 📖 中文文档

### 当前策略 | Current Strategy

**V8+XRP** (2026-02-22)

| 指标 Metric | 数值 Value |
|------------|-----------|
| **预期收益 Expected Return** | **+10.17%** (90天/90 days) |
| **胜率 Win Rate** | **70.0%** |
| **最大回撤 Max Drawdown** | **3.55%** |
| **交易频率 Trade Frequency** | 2-3次/周 (2-3/week) |

### 交易对 | Trading Pairs

```
BTC/USDT:USDT
ETH/USDT:USDT
DOGE/USDT:USDT
XRP/USDT:USDT
```

### 快速开始 | Quick Start

```bash
# 启动机器人 | Start bot
docker compose up -d freqtrade-futures

# 查看状态 | Check status
docker logs -f freqtrade-futures

# 快速检查 | Quick check
./scripts/quick-check-v8-xrp.sh
```

### 关键优化 | Key Optimizations

#### V8 策略改进 | V8 Strategy Improvements

1. **Alpha#101 过滤** - 日内趋势强度
2. **RSI 温和范围** (40-75) - 避免极端
3. **成交量确认** (1.2x) - 确保流动性
4. **趋势强度评分** - 信号质量控制
5. **波动率控制** (< 0.05) - 降低风险

#### XRP vs SOL

| 指标 Metric | SOL | XRP ⭐ | 改善 Improvement |
|------------|-----|-------|-----------------|
| 收益 Return | +8.91% | **+10.17%** | +1.26% |
| 胜率 Win Rate | 69.4% | **70.0%** | +0.6% |
| 回撤 Drawdown | 4.94% | **3.55%** | -1.39% |

### 性能对比 | Performance Comparison

| 版本 Version | 收益 Return | 胜率 Win Rate | 回撤 Drawdown |
|-------------|------------|--------------|--------------|
| **V8+XRP** ⭐ | **+10.17%** | **70.0%** | **3.55%** |
| V8(SOL) | +8.91% | 69.4% | 4.94% |
| V4 | +7.47% | 63.6% | 5.35% |

### 监控脚本 | Monitoring Scripts

#### 快速状态检查 | Quick Status Check
```bash
./scripts/quick-check-v8-xrp.sh
```

#### 详细性能监控 | Detailed Monitoring
```bash
./scripts/monitor-v8-xrp.sh
```

### 预期表现 | Expected Performance

| 时间 Time | 收益 Return | 交易次数 Trades |
|----------|------------|----------------|
| 1周 1 week | +0.85% | 2-3 |
| 1月 1 month | +3.39% | ~10 |
| 3月 3 months | +10.17% | ~30 |
| 6月 6 months | +20.34% | ~60 |

### 文档 | Documentation

- 📖 [完整文档 Full Documentation](README_CN.md)
- 📊 [V8+XRP 优化总结 Optimization Summary](docs/v8-xrp-optimization-summary.md)
- 🔬 [研究文档 Research Docs](docs/)

### 更新日志 | Changelog

#### v8.0 (2026-02-22)
- ✅ 添加 Alpha#101 多因子过滤
- ✅ 优化交易对 (SOL→XRP)
- ✅ 改善风险指标 (3.55% 回撤)
- ✅ 添加监控脚本

---

<a name="english"></a>
## 📖 English Documentation

### Current Strategy

**V8+XRP** (2026-02-22)

| Metric | Value |
|--------|-------|
| **Expected Return** | **+10.17%** (90 days) |
| **Win Rate** | **70.0%** |
| **Max Drawdown** | **3.55%** |
| **Trade Frequency** | 2-3/week |

### Trading Pairs

```
BTC/USDT:USDT
ETH/USDT:USDT
DOGE/USDT:USDT
XRP/USDT:USDT
```

### Quick Start

```bash
# Start bot
docker compose up -d freqtrade-futures

# Check status
docker logs -f freqtrade-futures

# Quick check
./scripts/quick-check-v8-xrp.sh
```

### Key Optimizations

#### V8 Strategy Improvements

1. **Alpha#101 Filter** - Daily trend strength
2. **RSI Range** (40-75) - Avoid extremes
3. **Volume Confirmation** (1.2x) - Ensure liquidity
4. **Trend Strength Score** - Signal quality control
5. **Volatility Control** (< 0.05) - Reduce risk

#### XRP vs SOL

| Metric | SOL | XRP ⭐ | Improvement |
|--------|-----|-------|-------------|
| Return | +8.91% | **+10.17%** | +1.26% |
| Win Rate | 69.4% | **70.0%** | +0.6% |
| Drawdown | 4.94% | **3.55%** | -1.39% |

### Performance Comparison

| Version | Return | Win Rate | Drawdown |
|---------|--------|----------|----------|
| **V8+XRP** ⭐ | **+10.17%** | **70.0%** | **3.55%** |
| V8(SOL) | +8.91% | 69.4% | 4.94% |
| V4 | +7.47% | 63.6% | 5.35% |

### Monitoring Scripts

#### Quick Status Check
```bash
./scripts/quick-check-v8-xrp.sh
```

#### Detailed Monitoring
```bash
./scripts/monitor-v8-xrp.sh
```

### Expected Performance

| Time | Return | Trades |
|------|--------|--------|
| 1 week | +0.85% | 2-3 |
| 1 month | +3.39% | ~10 |
| 3 months | +10.17% | ~30 |
| 6 months | +20.34% | ~60 |

### Documentation

- 📖 [Full Documentation](README_EN.md)
- 📊 [V8+XRP Optimization Summary](docs/v8-xrp-optimization-summary.md)
- 🔬 [Research Docs](docs/)

### Changelog

#### v8.0 (2026-02-22)
- ✅ Added Alpha#101 multi-factor filter
- ✅ Optimized trading pairs (SOL→XRP)
- ✅ Improved risk metrics (3.55% drawdown)
- ✅ Added monitoring scripts

---

## 📊 Project Structure | 项目结构

```
freqtrade-crypto-system/
├── strategies/              # Strategy files
│   ├── SupertrendFuturesStrategyV8.py  ⭐ Current
│   ├── SupertrendFuturesStrategyV4.py
│   └── ...
├── scripts/                 # Monitoring scripts
│   ├── quick-check-v8-xrp.sh
│   ├── monitor-v8-xrp.sh
│   └── README.md
├── user_data/               # Configuration
│   ├── config_futures.json
│   ├── config_spot.json
│   └── strategies/
├── docs/                    # Documentation
│   ├── v8-xrp-optimization-summary.md
│   └── README.md
├── README.md               # This file (双语/bilingual)
├── README_CN.md            # 中文详细文档
└── README_EN.md            # English detailed docs
```

---

## 🔧 Configuration | 配置

### Current Settings | 当前设置

```json
{
  "strategy": "SupertrendFuturesStrategyV8",
  "timeframe": "30m",
  "max_positions": 2,
  "stake_amount": 400,
  "stoploss": -0.03
}
```

### Strategy Parameters | 策略参数

```python
{
  "atr_period": 11,
  "atr_multiplier": 2.884,
  "ema_fast": 48,
  "ema_slow": 151,
  "adx_threshold_long": 33,
  "adx_threshold_short": 23,
  "alpha_threshold": 0.1  # V8 specific
}
```

---

## 🚨 Alert Rules | 告警规则

### Immediate Notification | 立即通知
- ❌ Weekly loss > -5%
- ❌ Bot stopped running
- ❌ Max drawdown > 8%

### Warning Alerts | 警告提醒
- ⚠️ Monthly return < +2%
- ⚠️ Win rate < 60%
- ⚠️ Max drawdown > 6%
- ⚠️ Trade frequency < 1/week

---

## 🎯 Roadmap | 路线图

### Short Term (1-2 weeks) | 短期
- Monitor V8+XRP performance
- Collect trade samples
- Validate actual vs expected

### Medium Term (1-3 months) | 中期
- Signal quality scoring (optional)
- Market regime identification (optional)
- Strategy fine-tuning

### Long Term (3-6 months) | 长期
- Machine learning integration
- Multi-strategy system
- Risk management optimization

---

## 📞 Support | 支持

### Useful Commands | 常用命令

```bash
# Start bot | 启动机器人
docker compose up -d freqtrade-futures

# Stop bot | 停止机器人
docker compose down freqtrade-futures

# View logs | 查看日志
docker logs -f freqtrade-futures

# Quick check | 快速检查
./scripts/quick-check-v8-xrp.sh

# Detailed monitoring | 详细监控
./scripts/monitor-v8-xrp.sh
```

---

## 📄 License | 许可证

Private repository for personal use.

---

<div align="center">

**Last Updated | 最后更新**: 2026-02-22 17:15  
**Version | 版本**: v8.0  
**Status | 状态**: ✅ Running | 运行中

**[⬆ Back to Top | 返回顶部](#freqtrade-加密货币交易系统)**

</div>
