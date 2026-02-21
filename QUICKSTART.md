# Quick Start Guide / 快速开始指南

**Deploy your crypto trading bot in 5 minutes!**

**5分钟内部署你的加密货币交易机器人！**

---

## Prerequisites / 前置条件

- Docker & Docker Compose
- OKX Account with API keys
- 4+ CPU cores, 8+ GB RAM

---

## Step 1: Clone Repository / 克隆仓库

```bash
git clone https://github.com/jinzheng8115/freqtrade-crypto-system.git
cd freqtrade-crypto-system
```

---

## Step 2: Create Directory Structure / 创建目录结构

```bash
# Create required directories
mkdir -p user_data/strategies
mkdir -p user_data/logs
mkdir -p user_data/data
```

---

## Step 3: Copy Strategy Files / 复制策略文件

```bash
# Copy strategies to user_data directory
cp strategies/SupertrendStrategy_Smart.py user_data/strategies/
cp strategies/SupertrendFuturesStrategyV4.py user_data/strategies/
```

---

## Step 4: Configure API Keys / 配置 API 密钥

```bash
# Copy example config files
cp config/config_spot.json.example user_data/config_spot.json
cp config/config_futures.json.example user_data/config_futures.json

# Edit config files with your API keys
nano user_data/config_spot.json
nano user_data/config_futures.json
```

**Replace these placeholders / 替换这些占位符**:
- `YOUR_API_KEY_HERE` → Your OKX API Key
- `YOUR_API_SECRET_HERE` → Your OKX API Secret

**Example / 示例**:
```json
{
  "exchange": {
    "name": "okx",
    "key": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
    "secret": "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0"
  }
}
```

---

## Step 5: Start Trading Bots / 启动交易机器人

```bash
# Start both spot and futures bots
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## Step 6: Download Historical Data / 下载历史数据

```bash
# Download spot data (90 days)
docker exec freqtrade-spot freqtrade download-data \
  --exchange okx \
  --pairs BTC/USDT ETH/USDT SOL/USDT DOGE/USDT \
  --timeframes 5m 15m 1h \
  --timerange 20251123- \
  --trading-mode spot

# Download futures data (173 days)
docker exec freqtrade-futures freqtrade download-data \
  --exchange okx \
  --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT \
  --timeframes 5m 15m 1h \
  --timerange 20250901- \
  --trading-mode futures \
  --erase
```

---

## Step 7: Verify Installation / 验证安装

```bash
# Check bot status
curl http://localhost:8080/api/v1/ping  # Futures
curl http://localhost:8081/api/v1/ping  # Spot

# Check logs
docker-compose logs freqtrade-spot
docker-compose logs freqtrade-futures
```

---

## Step 8: Monitor Performance / 监控表现

```bash
# View real-time logs
docker-compose logs -f --tail=100

# Check open trades
docker exec freqtrade-spot freqtrade show_trades --db-url sqlite:////freqtrade/user_data/tradesv3_spot.sqlite
docker exec freqtrade-futures freqtrade show_trades --db-url sqlite:////freqtrade/user_data/tradesv3_futures.sqlite
```

---

## Optional: Backtesting / 可选：回测

```bash
# Backtest spot strategy
docker exec freqtrade-spot freqtrade backtesting \
  --config user_data/config_spot.json \
  --strategy SupertrendStrategy_Smart \
  --timeframe 15m \
  --timerange 20251123-

# Backtest futures strategy
docker exec freqtrade-futures freqtrade backtesting \
  --config user_data/config_futures.json \
  --strategy SupertrendFuturesStrategyV4 \
  --timeframe 15m \
  --timerange 20250901-
```

---

## Production Deployment / 生产部署

**⚠️ WARNING / 警告**: Only deploy to production after thorough dry-run testing!

**⚠️ 警告**：只有在彻底的 dry-run 测试后才能部署到生产环境！

### Production Checklist / 生产检查清单

- [ ] Backtest results satisfactory (> 0% return)
- [ ] Dry-run tested for 1-2 weeks
- [ ] Risk parameters reviewed
- [ ] Stop loss configured correctly
- [ ] Monitoring system active

### Enable Production Mode / 启用生产模式

```bash
# Edit config files
nano user_data/config_spot.json
nano user_data/config_futures.json

# Change dry_run to false
"dry_run": false

# Restart services
docker-compose restart
```

---

## Troubleshooting / 故障排查

### Bot won't start / 机器人无法启动

```bash
# Check logs
docker-compose logs freqtrade-spot
docker-compose logs freqtrade-futures

# Verify config files
cat user_data/config_spot.json
cat user_data/config_futures.json

# Check API key permissions
# Ensure API keys have "Read" and "Trade" permissions
```

### No trades happening / 没有交易

```bash
# This is NORMAL during downtrend
# Strategy has 200 EMA filter to avoid trading in bear markets
# Wait for uptrend signals

# Check market conditions
# If price < EMA_200, strategy will not trade
```

### Port already in use / 端口已被占用

```bash
# Check what's using the ports
netstat -tulpn | grep 8080
netstat -tulpn | grep 8081

# Change ports in docker-compose.yml
ports:
  - "8082:8081"  # Change to available port
```

---

## Directory Structure / 目录结构

After setup, your directory will look like this:

```
freqtrade-crypto-system/
├── config/
│   ├── config_spot.json.example
│   └── config_futures.json.example
├── user_data/                    # Created by you
│   ├── config_spot.json          # Your config
│   ├── config_futures.json       # Your config
│   ├── strategies/               # Copied from strategies/
│   │   ├── SupertrendStrategy_Smart.py
│   │   └── SupertrendFuturesStrategyV4.py
│   ├── data/                     # Downloaded market data
│   ├── logs/                     # Bot logs
│   ├── tradesv3_spot.sqlite      # Spot database
│   └── tradesv3_futures.sqlite   # Futures database
├── strategies/                   # Original strategy files
├── scripts/
├── docker-compose.yml
└── README.md
```

---

## Support / 支持

- **Documentation**: [Full README](README.md)
- **Issues**: [GitHub Issues](https://github.com/jinzheng8115/freqtrade-crypto-system/issues)
- **Freqtrade Docs**: https://www.freqtrade.io/

---

**Happy Trading! 🚀**

**祝交易愉快！🚀**
