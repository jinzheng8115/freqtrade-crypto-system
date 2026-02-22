# Architecture Overview / 架构概览

**This project is NOT a standalone trading system. It is a strategy layer built on top of the Freqtrade framework.**

**本项目不是一个独立的交易系统。它是基于 Freqtrade 框架构建的策略层。**

---

## Three-Layer Architecture / 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: User Configuration (配置层)                        │
│  ─────────────────────────────────────────────────────────  │
│  • API credentials (OKX API Key + Secret)                  │
│  • Risk parameters (stake amount, max trades, leverage)    │
│  • Trading pairs (BTC/USDT, ETH/USDT, etc.)                │
│  • Runtime mode (dry_run vs real trading)                  │
│                                                             │
│  Files: config_spot.json, config_futures.json              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Trading Strategies (策略层) - 本项目主要贡献        │
│  ─────────────────────────────────────────────────────────  │
│  • Entry signals (when to buy/sell)                        │
│  • Exit signals (when to close positions)                  │
│  • Technical indicators (Supertrend, EMA, ADX, RSI)        │
│  • Trend confirmation (multi-indicator filtering)          │
│  • Risk management logic (stop loss, take profit)          │
│                                                             │
│  Files: SupertrendStrategy_Smart.py                        │
│         SupertrendFuturesStrategyV4.py                     │
│         (Inherits from Freqtrade's IStrategy)              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Freqtrade Framework (框架层) - 开源框架             │
│  ─────────────────────────────────────────────────────────  │
│  Infrastructure provided by Freqtrade:                     │
│  ✅ Exchange connectivity (OKX, Binance, etc.)             │
│  ✅ Order execution (buy, sell, cancel)                    │
│  ✅ Data management (historical + real-time data)          │
│  ✅ Backtesting engine (test strategies on past data)      │
│  ✅ Risk management (position sizing, leverage)            │
│  ✅ Database persistence (SQLite trade history)            │
│  ✅ Web UI + REST API (monitoring & control)               │
│                                                             │
│  Installation: Docker image (freqtradeorg/freqtrade:stable)│
│  Website: https://www.freqtrade.io/                        │
│  GitHub: https://github.com/freqtrade/freqtrade            │
└─────────────────────────────────────────────────────────────┘
```

---

## Dependency Flow / 依赖关系

```
Freqtrade Framework (Layer 1)
         ↓ required
Trading Strategies (Layer 2)
         ↓ required
User Configuration (Layer 3)
         ↓
    Automated Trading Bot
```

**All three layers are required** / **三层都是必需的**

---

## What Each Layer Provides / 每层提供什么

### Layer 1: Freqtrade Framework (基础设施)

**Provided by**: Freqtrade open-source project
**Installation**: Docker image (automatic)

| Component | Description |
|-----------|-------------|
| **Exchange API** | Connects to OKX, Binance, etc. |
| **Order Execution** | Submits buy/sell orders |
| **Data Download** | Fetches historical + real-time data |
| **Backtesting** | Tests strategies on past data |
| **Database** | Stores trade history (SQLite) |
| **Web UI** | Dashboard for monitoring |
| **REST API** | Programmatic control |

### Layer 2: Trading Strategies (交易逻辑)

**Provided by**: This project
**Installation**: Copy to `user_data/strategies/`

| Strategy | Type | Features |
|----------|------|----------|
| **SupertrendStrategy_Smart** | Spot | ADX filter, 200 EMA trend, optimized for choppy markets |
| **SupertrendFuturesStrategyV4** | Futures | 15m optimized, long+short, works in trending markets |

**Strategy Logic**:
```python
# Inherits from Freqtrade's IStrategy
class SupertrendStrategy_Smart(IStrategy):
    def populate_indicators(self, dataframe, metadata):
        # Calculate technical indicators
        dataframe['supertrend'] = self.supertrend(dataframe)
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
    
    def populate_entry_trend(self, dataframe, metadata):
        # Define buy conditions
        conditions = [
            dataframe['supertrend'] == 1,  # Uptrend
            dataframe['adx'] > 35,          # Strong trend
            dataframe['close'] > dataframe['ema_200'],  # Above 200 EMA
        ]
    
    def populate_exit_trend(self, dataframe, metadata):
        # Define sell conditions
        # ...
```

### Layer 3: User Configuration (个性化配置)

**Provided by**: User
**Installation**: Edit JSON files

```json
{
  "max_open_trades": 2,
  "stake_amount": 400,
  "dry_run": true,
  "exchange": {
    "name": "okx",
    "key": "YOUR_API_KEY",
    "secret": "YOUR_API_SECRET"
  }
}
```

---

## How They Work Together / 如何协同工作

### 1. Startup Sequence / 启动顺序

```bash
# Step 1: Docker starts Freqtrade container
docker-compose up -d
# → Pulls freqtradeorg/freqtrade:stable image
# → Starts Freqtrade application

# Step 2: Freqtrade loads configuration
# → Reads user_data/config_spot.json
# → Reads user_data/config_futures.json
# → Connects to OKX using API keys

# Step 3: Freqtrade loads strategies
# → Imports SupertrendStrategy_Smart
# → Imports SupertrendFuturesStrategyV4
# → Strategies inherit from IStrategy

# Step 4: Trading begins
# → Strategies analyze market data
# → Generate buy/sell signals
# → Freqtrade executes orders
```

### 2. Trading Loop / 交易循环

```
Market Data (OKX API)
       ↓
Freqtrade downloads data
       ↓
Strategy analyzes indicators
       ↓
Strategy generates signal (buy/sell)
       ↓
Freqtrade executes order
       ↓
Position management (stop loss, take profit)
       ↓
Database records trade
       ↓
Monitoring (logs, Telegram alerts)
```

---

## Why This Architecture? / 为什么采用这种架构？

### Benefits / 优势

**1. Separation of Concerns / 关注点分离**
- Freqtrade handles infrastructure
- Strategies focus on trading logic
- Configuration personalizes behavior

**2. Modularity / 模块化**
- Easy to swap strategies
- Easy to update Freqtrade
- Easy to adjust parameters

**3. Reliability / 可靠性**
- Freqtrade is battle-tested (1000+ GitHub stars)
- Active community support
- Regular updates

**4. Backtesting / 回测能力**
- Test strategies on historical data
- Validate before real trading
- Optimize parameters

---

## Comparison: Standalone vs Freqtrade-Based / 对比

### Standalone Trading Bot / 独立交易机器人

```
❌ Must build exchange connectivity
❌ Must implement order execution
❌ Must build backtesting engine
❌ Must handle database
❌ Must implement risk management
❌ High development effort
```

### Freqtrade-Based (This Project) / 基于 Freqtrade（本项目）

```
✅ Exchange connectivity: Built-in
✅ Order execution: Built-in
✅ Backtesting engine: Built-in
✅ Database: Built-in
✅ Risk management: Built-in
✅ Focus on strategy logic only
✅ Low development effort
✅ Production-ready infrastructure
```

---

## Deployment Checklist / 部署检查清单

- [ ] **Layer 1 (Freqtrade)**: Docker installed, `docker-compose up -d` successful
- [ ] **Layer 2 (Strategies)**: Files copied to `user_data/strategies/`
- [ ] **Layer 3 (Config)**: API keys added to config files
- [ ] **Verification**: Bots running, logs show no errors
- [ ] **Monitoring**: Telegram alerts working

---

## Troubleshooting / 故障排查

### Issue: "Freqtrade not found"

**Solution**: Ensure Docker is running and image is pulled
```bash
docker-compose pull
docker-compose up -d
```

### Issue: "Strategy import failed"

**Solution**: Ensure strategies are in correct directory
```bash
ls user_data/strategies/
# Should show:
# - SupertrendStrategy_Smart.py
# - SupertrendFuturesStrategyV4.py
```

### Issue: "Exchange connection failed"

**Solution**: Check API keys in config files
```bash
cat user_data/config_spot.json | grep "key"
# Should show your API key (not placeholder)
```

---

## Further Reading / 延伸阅读

- **Freqtrade Documentation**: https://www.freqtrade.io/
- **Freqtrade Strategy Guide**: https://www.freqtrade.io/en/stable/strategy-customization/
- **Freqtrade GitHub**: https://github.com/freqtrade/freqtrade

---

**Key Takeaway**: This project provides trading strategies (Layer 2) that run on top of the Freqtrade framework (Layer 1), with user-specific configuration (Layer 3). All three layers work together to create an automated trading system.

**关键要点**：本项目提供运行在 Freqtrade 框架（Layer 1）之上的交易策略（Layer 2），配合用户特定配置（Layer 3），三层协同工作创建自动化交易系统。
