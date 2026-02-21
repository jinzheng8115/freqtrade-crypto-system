# Freqtrade Crypto Trading System

[![Freqtrade](https://img.shields.io/badge/Freqtrade-2026.1-blue)](https://github.com/freqtrade/freqtrade)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Chinese](https://img.shields.io/badge/文档-中文-red)](README_CN.md)
[![English](https://img.shields.io/badge/Docs-English-blue)](README_EN.md)

**A comprehensive cryptocurrency trading system built on Freqtrade framework with optimized Supertrend strategies for spot and futures markets.**

**基于 Freqtrade 框架的加密货币交易系统，包含优化的 Supertrend 现货和合约策略。**

---

## 📖 Documentation / 文档

**Choose your language / 选择语言**:

- 🇺🇸 **[English Documentation](README_EN.md)** - Full documentation in English
- 🇨🇳 **[中文文档](README_CN.md)** - 完整中文文档

---

## ⚡ Quick Start / 快速开始

```bash
# 1. Clone repository / 克隆仓库
git clone https://github.com/jinzheng8115/freqtrade-crypto-system.git
cd freqtrade-crypto-system

# 2. Run setup script / 运行安装脚本
./setup.sh

# 3. Add API keys / 添加 API 密钥
nano user_data/config_spot.json
nano user_data/config_futures.json

# 4. Start trading / 开始交易
docker-compose up -d
```

**Deploy in 5 minutes! / 5分钟快速部署！** 🚀

See **[QUICKSTART.md](QUICKSTART.md)** for detailed instructions.

详细步骤请看 **[QUICKSTART.md](QUICKSTART.md)**。

---

## 🎯 What This Project Is / 项目简介

**This is NOT a standalone trading system.** It is a **strategy layer** built on top of **Freqtrade framework**.

**这不是独立的交易系统。** 它是构建在 **Freqtrade 框架**之上的**策略层**。

### Three-Layer Architecture / 三层架构

```
Layer 3: Configuration (User API keys, risk parameters)
         配置层（用户 API 密钥、风险参数）
                    ↓
Layer 2: Trading Strategies (This project - our contribution)
         策略层（本项目 - 我们的贡献）
                    ↓
Layer 1: Freqtrade Framework (Open-source infrastructure)
         框架层（开源基础设施）
```

**What we provide / 我们提供什么**:
- ✅ Optimized trading strategies (Supertrend + ADX + EMA)
- ✅ Backtested parameters (90-173 days historical data)
- ✅ Monitoring scripts (hourly status reports)
- ✅ Complete documentation (paper-standard)

**What Freqtrade provides / Freqtrade 提供什么**:
- ✅ Exchange connectivity (OKX API)
- ✅ Order execution (buy/sell/stop loss)
- ✅ Data management (historical + real-time)
- ✅ Backtesting engine
- ✅ Risk management

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for details.

详情请看 **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**。

---

## 📊 Strategy Performance / 策略表现

### Spot Strategy / 现货策略

**SupertrendStrategy_Smart** (ADX optimized)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Return** | -5.92% | **-1.89%** | **+4.03%** ✅ |
| **Max Drawdown** | 11.16% | **3.42%** | **-69%** ✅ |
| **Win Rate** | 66.7% | **65.9%** | Stable |

**Period**: 90 days (2025-11-23 to 2026-02-21)
**Market**: -28% (bear market)
**Outperformed market by**: **+26%** ✅

### Futures Strategy / 合约策略

**SupertrendFuturesStrategyV4** (15m optimized)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Return** | -22.53% | **-6.64%** | **+15.89%** ✅ |
| **Win Rate** | 47.4% | **52.9%** | **+5.5%** ✅ |

**Period**: 173 days (2025-09-01 to 2026-02-21)
**Market**: -51.6% (bear market)
**Outperformed market by**: **+45%** ✅

---

## 🚀 Features / 功能特点

- ✅ **Multi-Market Support**: Spot + Futures trading
- ✅ **Trend Filtering**: ADX + 200 EMA confirmation
- ✅ **Risk Management**: Stop loss, take profit, trailing stop
- ✅ **Backtesting**: Tested on 90-173 days historical data
- ✅ **Monitoring**: Hourly status reports via Telegram
- ✅ **Docker Ready**: One-command deployment
- ✅ **Production Ready**: Complete deployment pipeline

---

## 📦 Project Structure / 项目结构

```
freqtrade-crypto-system/
├── strategies/              # Trading strategies (Layer 2)
│   ├── SupertrendStrategy_Smart.py
│   └── SupertrendFuturesStrategyV4.py
├── config/                  # Configuration templates (Layer 3)
│   ├── config_spot.json.example
│   └── config_futures.json.example
├── scripts/                 # Utility scripts
│   └── check-status-with-push.sh
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # Architecture explanation
│   ├── README_EN.md         # English documentation
│   └── README_CN.md         # 中文文档
├── docker-compose.yml       # Freqtrade deployment (Layer 1)
├── README.md                # This file (multilingual index)
├── README_EN.md             # English full documentation
├── README_CN.md             # 中文完整文档
├── QUICKSTART.md            # 5-minute deployment guide
├── setup.sh                 # Automated setup script
└── LICENSE                  # MIT License
```

---

## 🛡️ Security / 安全

**Your API keys are safe / 你的 API 密钥是安全的**:
- ✅ Real config files are excluded via .gitignore
- ✅ Only template files (with placeholders) are uploaded
- ✅ No sensitive data in repository

See **[Security Notes](docs/ARCHITECTURE.md#security)**.

---

## 📚 Documentation / 文档

- **[English Full Documentation](README_EN.md)** - Complete paper-standard docs
- **[中文完整文档](README_CN.md)** - 完整论文标准文档
- **[Quick Start Guide](QUICKSTART.md)** - 5-minute deployment
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System architecture
- **[Freqtrade Docs](https://www.freqtrade.io/)** - Official Freqtrade documentation

---

## 🤝 Contributing / 贡献

Contributions are welcome! Please feel free to submit a Pull Request.

欢迎贡献！请随时提交 Pull Request。

---

## 📝 License / 许可证

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

本项目采用 MIT 许可证 - 详情请看 [LICENSE](LICENSE) 文件。

---

## 🙏 Acknowledgments / 致谢

- **Freqtrade Team** - For the excellent trading framework
- **OKX Exchange** - For reliable API access
- **Open Source Community** - For technical analysis libraries

---

## 📧 Contact / 联系

- **GitHub Issues**: [Submit an issue](https://github.com/jinzheng8115/freqtrade-crypto-system/issues)
- **Repository**: [https://github.com/jinzheng8115/freqtrade-crypto-system](https://github.com/jinzheng8115/freqtrade-crypto-system)

---

## ⚠️ Disclaimer / 免责声明

**Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor.** Past performance is not indicative of future results. Use this software at your own risk.

**加密货币交易存在 substantial 风险，不适合所有投资者。** 过去的表现不代表未来的结果。使用本软件的风险自负。

**Always test thoroughly in dry-run mode before real trading!**

**在真实交易前务必在 dry-run 模式下充分测试！**

---

**Star ⭐ this repo if you find it helpful!**

**如果觉得有帮助，请给个 Star ⭐！**

---

**Last Updated / 最后更新**: 2026-02-21
