# Freqtrade Crypto Futures Trading System

> **Current Strategy**: SupertrendFuturesStrategyV8 + XRP  
> **Last Updated**: 2026-02-22  
> **Status**: ✅ Running in Dry Run Mode

---

## 📊 Current Configuration

### V8+XRP Strategy (Latest - 2026-02-22)

**Trading Pairs**: BTC/ETH/DOGE/XRP  
**Timeframe**: 30m  
**Max Positions**: 2  
**Expected Performance** (90 days):
- ✅ **Return**: +10.17%
- ✅ **Win Rate**: 70.0%
- ✅ **Max Drawdown**: 3.55%

### Key Improvements

Compared to V4:
- ✅ Return: +7.47% → **+10.17%** (+2.70%)
- ✅ Win Rate: 63.6% → **70.0%** (+6.4%)
- ✅ Drawdown: 5.35% → **3.55%** (-1.80%)

---

## 🚀 Quick Start

### 1. Start the Bot

```bash
cd /root/freqtrade
docker compose up -d freqtrade-futures
```

### 2. Check Status

```bash
# Quick check
./scripts/quick-check-v8-xrp.sh

# Detailed monitoring
./scripts/monitor-v8-xrp.sh
```

### 3. View Logs

```bash
docker logs -f freqtrade-futures
```

---

## 📈 Strategy Evolution

### Version History

| Version | Date | Return | Win Rate | Drawdown | Notes |
|---------|------|--------|----------|----------|-------|
| **V8+XRP** ⭐ | 2026-02-22 | **+10.17%** | **70.0%** | **3.55%** | Current optimal |
| V8(SOL) | 2026-02-22 | +8.91% | 69.4% | 4.94% | Multi-factor gentle |
| V4 | 2026-02-22 | +7.47% | 63.6% | 5.35% | Baseline optimized |

### Key Optimizations

#### V8 Improvements
1. **Alpha#101 Filter** (0.1 threshold)
   - Daily trend strength indicator
   - Filters false breakouts

2. **RSI Range** (40-75)
   - Avoids extreme zones
   - Improves signal quality

3. **Volume Confirmation** (1.2x average)
   - Ensures liquidity
   - Not too strict (1.5x)

4. **Trend Strength Score**
   - ADX > 30: +1 point
   - ADX > 35: +2 points
   - Minimum required: 1 point

5. **Volatility Control**
   - ATR/Close < 0.05
   - Avoids extreme volatility

#### XRP vs SOL

| Metric | SOL | **XRP** | Improvement |
|--------|-----|---------|-------------|
| Return | +8.91% | **+10.17%** | **+1.26%** |
| Win Rate | 69.4% | **70.0%** | **+0.6%** |
| Drawdown | 4.94% | **3.55%** | **-1.39%** |

**Why XRP is Better**:
- Better liquidity/volatility balance
- Clearer trends
- Fewer false breakouts
- Better synergy with BTC/ETH/DOGE

---

## 📁 Project Structure

```
freqtrade-crypto-system/
├── strategies/
│   ├── SupertrendFuturesStrategyV8.py      # Current strategy ⭐
│   ├── SupertrendFuturesStrategyV4.py      # Previous version
│   └── ...other versions
├── scripts/
│   ├── quick-check-v8-xrp.sh               # Quick status check
│   ├── monitor-v8-xrp.sh                   # Detailed monitoring
│   └── check-status-with-push.sh           # Telegram push
├── user_data/
│   ├── config_futures.json                 # Futures config
│   ├── config_spot.json                    # Spot config
│   └── strategies/                         # Strategy parameters
├── docs/
│   ├── v8-xrp-optimization-summary.md      # Optimization summary
│   └── README.md                           # This file
└── docker-compose.yml
```

---

## 🔧 Configuration

### Current Settings

```json
{
  "strategy": "SupertrendFuturesStrategyV8",
  "timeframe": "30m",
  "trading_pairs": [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "DOGE/USDT:USDT",
    "XRP/USDT:USDT"
  ],
  "max_positions": 2,
  "stake_amount": 400,
  "total_capital": 1000,
  "stoploss": -0.03,
  "trailing_stop": true,
  "trailing_stop_positive": 0.02,
  "trailing_stop_positive_offset": 0.03
}
```

### Strategy Parameters

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

## 📊 Monitoring & Tracking

### Monitoring Scripts

#### Quick Status Check
```bash
./scripts/quick-check-v8-xrp.sh
```
Shows: Container status, positions, P/L

#### Detailed Monitoring
```bash
./scripts/monitor-v8-xrp.sh
```
Shows: Full performance stats, recent trades, account status

### Expected Performance

| Timeframe | Expected Return | Expected Trades |
|-----------|----------------|-----------------|
| 1 week | +0.85% | 2-3 trades |
| 1 month | +3.39% | ~10 trades |
| 3 months | +10.17% | ~30 trades |
| 6 months | +20.34% | ~60 trades |

### Performance Tracking

Tracking file: `/root/.openclaw/agents/freqtrade/tracking/v8-xrp-performance.md`

Updated weekly with:
- Trade count and win rate
- Cumulative returns
- Maximum drawdown
- XRP vs SOL comparison

---

## 🔬 Research & Backtesting

### Key Studies

1. **Walk-Forward Validation**
   - 180-day backtest validation
   - 3-segment performance analysis
   - Market regime identification

2. **Trading Pair Optimization**
   - Tested 9 different 4-pair combinations
   - Found BTC+ETH+DOGE core triangle
   - XRP outperforms SOL

3. **Multi-Factor Testing**
   - V5-V7 versions tested
   - V8 emerged as optimal
   - Quality > Quantity

### Research Documents

- `docs/walk-forward-report.md` - 180-day validation
- `docs/v8-expansion-test-report.md` - Pair expansion tests
- `docs/v8-pair-optimization.md` - SOL→XRP analysis

---

## ⚙️ Maintenance

### Daily Tasks
- ✅ Check container status
- ✅ Monitor for alerts
- ✅ Review new trades

### Weekly Tasks
- ✅ Run detailed monitoring
- ✅ Update performance tracking
- ✅ Compare actual vs expected

### Monthly Tasks
- ✅ Full performance review
- ✅ Strategy validation
- ✅ Parameter adjustment (if needed)

---

## 🚨 Alert Rules

### Immediate Notification
- ❌ Weekly loss > -5%
- ❌ Bot stopped running
- ❌ Max drawdown > 8%

### Warning Alerts
- ⚠️ Monthly return < +2%
- ⚠️ Win rate < 60%
- ⚠️ Max drawdown > 6%
- ⚠️ Trade frequency < 1/week

---

## 📚 Documentation

### Strategy Documentation
- **V8+XRP Summary**: `docs/v8-xrp-optimization-summary.md`
- **Walk-Forward Report**: `research/walk-forward-report.md`
- **Pair Optimization**: `research/v8-pair-optimization.md`

### Code Documentation
- Each strategy file includes detailed comments
- Parameter explanations in code
- Backtest methodology documented

---

## 🔄 Recent Changes

### 2026-02-22 - V8+XRP Deployment

**Changes**:
- ✅ Upgraded to V8 strategy (multi-factor gentle)
- ✅ Switched trading pairs: SOL → XRP
- ✅ Added Alpha#101 and trend scoring
- ✅ Created monitoring scripts

**Commits**:
- `ddd1b81` - V8 strategy + pair optimization
- `ebbbee0` - Documentation update

**Results**:
- Expected return: +10.17% (90 days)
- Expected win rate: 70%
- Expected drawdown: 3.55%

---

## 🎯 Next Steps

### Short Term (1-2 weeks)
1. Monitor V8+XRP performance
2. Collect trade samples
3. Validate actual vs expected

### Medium Term (1-3 months)
1. Signal quality scoring (optional)
2. Market regime identification (optional)
3. Strategy fine-tuning

### Long Term (3-6 months)
1. Machine learning integration
2. Multi-strategy system
3. Risk management optimization

---

## 📞 Support

### Useful Commands

```bash
# Start bot
docker compose up -d freqtrade-futures

# Stop bot
docker compose down freqtrade-futures

# View logs
docker logs -f freqtrade-futures

# Quick check
./scripts/quick-check-v8-xrp.sh

# Detailed monitoring
./scripts/monitor-v8-xrp.sh

# Backtesting
docker exec freqtrade-futures freqtrade backtesting \
  --strategy SupertrendFuturesStrategyV8 \
  --timeframe 30m \
  --timerange 20251124-20260222 \
  --config user_data/config_futures.json
```

### Troubleshooting

**Bot not running**:
```bash
docker compose restart freqtrade-futures
```

**No trades for a while**:
- Normal for V8 (3 days/trade average)
- Check market conditions
- Verify config correct

**High drawdown**:
- Check if > 6% (warning)
- Review recent trades
- Consider pausing if > 8%

---

## 📊 Performance History

### Backtested Results (90 days)

| Version | Return | Win Rate | Drawdown | Trades |
|---------|--------|----------|----------|--------|
| **V8+XRP** ⭐ | **+10.17%** | **70.0%** | **3.55%** | 30 |
| V8(SOL) | +8.91% | 69.4% | 4.94% | 36 |
| V4 | +7.47% | 63.6% | 5.35% | 55 |

### Live Performance

*Tracking started: 2026-02-22*

*See tracking file for live results*

---

## 🤝 Contributing

### Strategy Development Process

1. **Research** → Analyze market conditions
2. **Backtest** → Validate on historical data
3. **Optimize** → Fine-tune parameters
4. **Deploy** → Paper trade first
5. **Monitor** → Track performance
6. **Iterate** → Continuous improvement

### Code Style

- Clear variable names
- Comprehensive comments
- Modular functions
- Error handling

---

## 📄 License

Private repository for personal use.

---

## 📝 Changelog

### v8.0 (2026-02-22)
- Added Alpha#101 multi-factor filter
- Optimized trading pairs (SOL→XRP)
- Improved risk metrics (3.55% drawdown)
- Added monitoring scripts
- Comprehensive documentation

### v4.0 (2026-02-21)
- Timeframe optimization (15m→30m)
- Parameter optimization via hyperopt
- Improved from -10.23% to +7.47%

---

**Last Updated**: 2026-02-22 17:05  
**Version**: v8.0  
**Status**: ✅ Running  
**Next Review**: 2026-02-29
