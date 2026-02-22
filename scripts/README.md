# Monitoring Scripts

Scripts for monitoring and managing the Freqtrade crypto trading bot.

---

## 📊 Available Scripts

### 1. quick-check-v8-xrp.sh

**Purpose**: Quick status check for V8+XRP strategy

**Usage**:
```bash
./scripts/quick-check-v8-xrp.sh
```

**Output**:
- Container status (running/stopped)
- Current positions count
- Total profit/loss

**Use Case**: Daily quick check

---

### 2. monitor-v8-xrp.sh

**Purpose**: Detailed performance monitoring

**Usage**:
```bash
./scripts/monitor-v8-xrp.sh
```

**Output**:
- Container status
- Strategy configuration
- Current positions
- Recent trades (7 days)
- Account status
- Trade statistics

**Use Case**: Weekly detailed review

---

### 3. check-status-with-push.sh

**Purpose**: Status check with Telegram notification

**Usage**:
```bash
./scripts/check-status-with-push.sh
```

**Output**:
- Status check
- Push to Telegram

**Use Case**: Automated monitoring

---

## 🎯 Expected Performance

### V8+XRP Strategy Targets

| Metric | Expected | Alert Threshold |
|--------|----------|-----------------|
| **Weekly Return** | +0.85% | < -1.25% |
| **Monthly Return** | +3.39% | < +2% |
| **Win Rate** | 70% | < 60% |
| **Max Drawdown** | < 4% | > 6% |
| **Trade Frequency** | 2-3/week | < 1/week |

---

## 📅 Monitoring Schedule

### Daily (Automated)
- Quick status check
- Alert monitoring
- Trade notifications

### Weekly (Manual)
- Run detailed monitoring
- Update tracking file
- Compare actual vs expected

### Monthly (Manual)
- Full performance review
- Strategy validation
- Documentation update

---

## 🔧 Customization

### Adjust Monitoring Frequency

Edit crontab:
```bash
crontab -e
```

Add tasks:
```bash
# Daily quick check at 9:00
0 9 * * * /root/freqtrade/scripts/quick-check-v8-xrp.sh >> /var/log/freqtrade-monitor.log 2>&1

# Weekly detailed check on Monday at 10:00
0 10 * * 1 /root/freqtrade/scripts/monitor-v8-xrp.sh >> /var/log/freqtrade-monitor.log 2>&1
```

### Add Custom Alerts

Edit the monitoring scripts to add custom alert conditions:

```bash
# Example: Alert on high loss
if [ $(echo "$PROFIT < -5" | bc) -eq 1 ]; then
    echo "⚠️ ALERT: High loss detected: $PROFIT%"
    # Add notification method (Telegram, email, etc.)
fi
```

---

## 📊 Output Format

### Quick Check Output
```
🔍 V8+XRP 快速状态检查
时间: 2026-02-22 17:00:00

✅ 容器: 运行中
📊 持仓数: 1 / 2
💰 总盈亏: +5.23 USDT

✨ 状态正常
```

### Detailed Monitoring Output
```
==========================================
V8+XRP 实盘性能监控
检查时间: 2026-02-22 17:00:00
==========================================

📦 容器状态:
  ✅ 运行中 (fc2bd18c5da1)

⚙️  策略配置:
  交易对: BTC/ETH/DOGE/XRP

💰 当前持仓:
  BTC/USDT: 0.01 @ 95000 (+2.3%)

📊 最近交易:
  [Last 10 trades]

💵 账户状态:
  [Account summary]

📈 交易统计:
  总交易信号: 5 次

==========================================
监控完成
==========================================
```

---

## 🚨 Troubleshooting

### Script Permission Denied

```bash
chmod +x scripts/*.sh
```

### jq Command Not Found

```bash
apt-get update && apt-get install -y jq
```

### Docker Permission Denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Or run with sudo
sudo ./scripts/quick-check-v8-xrp.sh
```

---

## 📝 Notes

- All scripts assume Freqtrade is running in Docker
- Scripts are configured for V8+XRP strategy
- Modify trading pairs in scripts if strategy changes
- Logs are written to stdout by default

---

## 🔄 Updates

### 2026-02-22
- Created initial monitoring scripts
- Added V8+XRP specific checks
- Added performance tracking integration

---

*Last Updated: 2026-02-22*
