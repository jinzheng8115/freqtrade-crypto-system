# Freqtrade Crypto Trading System

[![Freqtrade](https://img.shields.io/badge/Freqtrade-2026.1-blue)](https://github.com/freqtrade/freqtrade)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![中文](https://img.shields.io/badge/Language-中文-red)](README.md)

**Cryptocurrency futures trading system based on Freqtrade framework, achieving stable returns with V8+XRP strategy.**

> **📅 Last Updated**: 2026-02-22  
> **📊 Current Version**: V8.0  
> **🔄 Status**: ✅ Running

---

## 📊 Current Strategy Performance

### V8+XRP Strategy (Deployed 2026-02-22)

| Metric | Expected | Backtest Period |
|--------|----------|-----------------|
| **Expected Return** | **+10.17%** | 90 days |
| **Win Rate** | **70.0%** | 90 days |
| **Max Drawdown** | **3.55%** | 90 days |
| **Trade Frequency** | 2-3/week | - |
| **Sharpe Ratio** | 2.87 | Risk-adjusted return |

### Trading Pairs

```
BTC/USDT:USDT  ← Bitcoin (Core)
ETH/USDT:USDT  ← Ethereum (Core)
DOGE/USDT:USDT ← Dogecoin (High Volatility)
XRP/USDT:USDT  ← Ripple (Optimized Choice)
```

---

## 🚀 Quick Start

### 1. Start System

```bash
cd /root/freqtrade
docker compose up -d freqtrade-futures
```

### 2. Check Status

```bash
# Live logs
docker logs -f freqtrade-futures

# Quick check
./scripts/quick-check-v8-xrp.sh

# Detailed monitoring
./scripts/monitor-v8-xrp.sh
```

### 3. Verify Configuration

```bash
# View current config
cat user_data/config_futures.json

# View strategy parameters
docker exec freqtrade-futures cat /freqtrade/user_data/strategies/SupertrendFuturesStrategyV8.py
```

---

## 📈 Strategy Evolution

### Version Comparison (90-day backtest)

| Version | Return | Win Rate | Drawdown | Trades | Rating |
|---------|--------|----------|----------|--------|--------|
| **V8+XRP** ⭐ | **+10.17%** | **70.0%** | **3.55%** | 30 | ✅ Current Best |
| V8(SOL) | +8.91% | 69.4% | 4.94% | 36 | ✅ Excellent |
| V4 | +7.47% | 63.6% | 5.35% | 55 | ✅ Good |

### V8 Core Improvements

#### 1. Alpha#101 Multi-Factor Filter

```python
# Daily trend strength indicator
dataframe['alpha_101'] = (close - open) / (high - low + 0.001)
# Trade only when alpha_101 > 0.1
```

**Effect**: Filters false breakouts, improves signal quality

#### 2. RSI Moderate Range

```python
# Trade only when RSI is between 40-75
(dataframe['rsi'] > 40) & (dataframe['rsi'] < 75)
```

**Effect**: Avoids extreme zones, improves win rate

#### 3. Volume Confirmation

```python
# Volume > 1.2x average
dataframe['volume'] > dataframe['volume_ma'] * 1.2
```

**Effect**: Ensures liquidity, reduces slippage

#### 4. Trend Strength Score

```python
# ADX > 30: +1 point
# ADX > 35: +2 points
# Minimum required: 1 point
trend_score >= 1
```

**Effect**: Trades only strong trends

#### 5. Volatility Control

```python
# ATR/Close < 0.05
dataframe['volatility_ratio'] < 0.05
```

**Effect**: Avoids extreme volatility, reduces risk

---

## 🔄 XRP vs SOL Optimization

### Trading Pair Test Results

**Test Date**: 2026-02-22  
**Test Period**: 90-day backtest

| Combination | Return | Win Rate | Drawdown | Trades | Rank |
|-------------|--------|----------|----------|--------|------|
| **BTC/ETH/DOGE/XRP** | **+10.17%** | **70.0%** | **3.55%** | 30 | 🥇 **Best** |
| BTC/ETH/SOL/DOGE | +8.91% | 69.4% | 4.94% | 36 | 🥈 Good |
| BTC/ETH/SOL/MATIC | +2.46% | 67.9% | 3.80% | 28 | 🥉 Average |
| BTC/ETH/SOL/LINK | +2.85% | 67.7% | 5.01% | 31 | ⚠️ Average |

### Key Findings

**BTC + ETH + DOGE is the Core Triangle** ✅

- **BTC/ETH**: High liquidity, stable foundation
- **DOGE**: High volatility, profit opportunities
- **4th Coin**: XRP performs best

### Why XRP Outperforms SOL

| Characteristic | SOL | XRP ⭐ | Explanation |
|---------------|-----|-------|-------------|
| **Liquidity** | High | **High** | Both are mainstream |
| **Volatility** | Very High | **Moderate** | XRP more stable |
| **Trend Clarity** | Medium | **High** | XRP trends clearer |
| **False Breakout Rate** | High | **Low** | XRP more reliable |
| **Synergy with Core** | Medium | **High** | XRP better complement |

---

## 🔧 System Configuration

### Strategy Parameters

```json
{
  "strategy": "SupertrendFuturesStrategyV8",
  "timeframe": "30m",
  "max_open_trades": 2,
  "stake_currency": "USDT",
  "stake_amount": 400,
  "dry_run_wallet": 1000,
  "stoploss": -0.03
}
```

### Core Indicator Parameters

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

### Risk Management

```json
{
  "trailing_stop": true,
  "trailing_stop_positive": 0.02,
  "trailing_stop_positive_offset": 0.03,
  "trailing_only_offset_is_reached": true
}
```

---

## 📊 Monitoring Scripts

### 1. Quick Status Check

```bash
./scripts/quick-check-v8-xrp.sh
```

**Output**:
- ✅ Container status
- 📊 Current positions
- 💰 Total P/L

**Use Case**: Daily quick check

### 2. Detailed Performance Monitoring

```bash
./scripts/monitor-v8-xrp.sh
```

**Output**:
- 📦 Container details
- ⚙️ Strategy config
- 💰 Position details
- 📊 Recent trades
- 💵 Account status
- 📈 Trade statistics

**Use Case**: Weekly detailed review

---

## 📅 Expected Performance

### Monthly Expectations

| Time | Expected Return | Expected Trades | Cumulative Return |
|------|----------------|----------------|-------------------|
| **1 month** | **+3.39%** | ~10 trades | +3.39% |
| **2 months** | +6.78% | ~20 trades | +6.78% |
| **3 months** | **+10.17%** | ~30 trades | +10.17% |
| **6 months** | +20.34% | ~60 trades | +22.40% (compound) |
| **12 months** | +40.68% | ~120 trades | +50.57% (compound) |

### Conservative Estimate

Considering live trading slippage and market changes, actual returns are conservatively estimated at **60-80%** of backtest:

| Time | Conservative Return | Note |
|------|-------------------|------|
| 1 month | +2-2.7% | Conservative |
| 3 months | +7-8% | Reasonable |
| 12 months | +25-32% | Long-term target |

---

## 🚨 Alert Rules

### Immediate Notification (Critical)

- ❌ **Weekly loss > -5%**
- ❌ **Bot stopped running**
- ❌ **Max drawdown > 8%**

### Warning Alerts (Attention)

- ⚠️ **Monthly return < +2%** (below expectation)
- ⚠️ **Win rate < 60%** (strategy may be failing)
- ⚠️ **Max drawdown > 6%** (risk too high)
- ⚠️ **Trade frequency < 1/week** (too few signals)

---

## 🔬 Research Documentation

### Core Research

| Document | Description |
|----------|-------------|
| [V8+XRP Optimization Summary](docs/v8-xrp-optimization-summary.md) | Complete optimization process and data |
| [Walk-Forward Validation](research/walk-forward-report.md) | 180-day segment validation |
| [Trading Pair Optimization](research/v8-pair-optimization.md) | SOL→XRP analysis |
| [Expansion Test Report](research/v8-expansion-test-report.md) | Pair/position testing |

### Strategy Files

| Strategy | Description |
|----------|-------------|
| `SupertrendFuturesStrategyV8.py` | Current strategy ⭐ |
| `SupertrendFuturesStrategyV4.py` | Base version |
| `SupertrendFuturesStrategyV8_1.py` | Frequency optimized |
| `SupertrendFuturesStrategyV8_2.py` | Balanced version |

---

## 📁 Project Structure

```
freqtrade-crypto-system/
├── strategies/                  # Strategy files
│   ├── SupertrendFuturesStrategyV8.py  ⭐ Current
│   └── ...
├── scripts/                     # Monitoring scripts
│   ├── quick-check-v8-xrp.sh    # Quick check
│   ├── monitor-v8-xrp.sh        # Detailed monitoring
│   └── README.md
├── user_data/                   # Configuration
│   ├── config_futures.json      # Futures config
│   ├── config_spot.json         # Spot config
│   └── strategies/              # Strategy parameters
├── docs/                        # Documentation
│   ├── v8-xrp-optimization-summary.md
│   └── README.md
├── research/                    # Research docs
│   ├── walk-forward-report.md
│   └── ...
├── README.md                    # Chinese version
└── README_EN.md                 # This file (English)
```

---

## 🎯 Roadmap

### Short Term (1-2 weeks)

- [x] V8+XRP strategy deployment
- [x] Monitoring script creation
- [ ] Observe live performance
- [ ] Collect trade samples

### Medium Term (1-3 months)

- [ ] Signal quality scoring (optional)
- [ ] Market regime identification (optional)
- [ ] Strategy fine-tuning

### Long Term (3-6 months)

- [ ] Machine learning integration
- [ ] Multi-strategy system
- [ ] Risk management optimization

---

## 🔧 Common Commands

### Daily Management

```bash
# Start bot
docker compose up -d freqtrade-futures

# Stop bot
docker compose down freqtrade-futures

# Restart bot
docker compose restart freqtrade-futures

# View logs
docker logs -f freqtrade-futures

# Recent logs
docker logs --tail 100 freqtrade-futures
```

### Monitoring Checks

```bash
# Quick check
./scripts/quick-check-v8-xrp.sh

# Detailed monitoring
./scripts/monitor-v8-xrp.sh

# View positions
docker exec freqtrade-futures freqtrade show-trades \
  --db-url sqlite:////freqtrade/user_data/tradesv3_futures.sqlite
```

### Backtesting

```bash
# Run backtest
docker exec freqtrade-futures freqtrade backtesting \
  --strategy SupertrendFuturesStrategyV8 \
  --timeframe 30m \
  --timerange 20251124-20260222 \
  --config user_data/config_futures.json
```

---

## 📊 Performance History

### Backtest Results (90 days)

| Version | Return | Win Rate | Drawdown | Sharpe |
|---------|--------|----------|----------|--------|
| **V8+XRP** | **+10.17%** | **70.0%** | **3.55%** | **2.87** |
| V8(SOL) | +8.91% | 69.4% | 4.94% | 1.80 |
| V4 | +7.47% | 63.6% | 5.35% | 1.40 |

### Live Tracking

**Start Date**: 2026-02-22 16:25  
**Tracking File**: [tracking/v8-xrp-performance.md](tracking/v8-xrp-performance.md)

*Continuously updated...*

---

## 📞 Troubleshooting

### Common Issues

**Q: Bot not running?**

```bash
# Check container status
docker ps | grep freqtrade

# Restart container
docker compose restart freqtrade-futures
```

**Q: No trades for a long time?**

- Normal: V8 is low-frequency strategy (avg 3 days/trade)
- Check: Verify configuration is correct
- Wait: Be patient for signals

**Q: High drawdown?**

- Warning: Drawdown > 6%
- Check: Recent trade records
- Consider: Pause strategy

---

## 📝 Changelog

### v8.0 (2026-02-22)

**Major Updates**:
- ✅ Upgraded to V8 strategy (multi-factor gentle version)
- ✅ Optimized trading pairs: SOL → XRP
- ✅ Improved returns: +8.91% → +10.17%
- ✅ Reduced risk: 4.94% → 3.55% drawdown

**Technical Improvements**:
- ✅ Added Alpha#101 filter
- ✅ Optimized RSI range
- ✅ Enhanced trend scoring
- ✅ Created monitoring scripts

**Documentation**:
- ✅ Unified Chinese/English docs
- ✅ Added detailed research docs
- ✅ Improved user guide

---

## 📄 License

Private repository for personal use only.

---

## 🔗 Related Links

- **GitHub**: https://github.com/jinzheng8115/freqtrade-crypto-system
- **Freqtrade**: https://github.com/freqtrade/freqtrade
- **OKX**: https://www.okx.com/

---

<div align="center">

**[📖 中文版 | Chinese Version](README.md)**

---

**Last Updated**: 2026-02-22 17:30  
**Version**: v8.0  
**Status**: ✅ Running

</div>
