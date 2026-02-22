# Freqtrade 加密货币交易系统

[![Freqtrade](https://img.shields.io/badge/Freqtrade-2026.1-blue)](https://github.com/freqtrade/freqtrade)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

**基于 Freqtrade 框架的加密货币合约交易系统，使用 V8+XRP 策略实现稳定收益。**

> **📅 最后更新**: 2026-02-22  
> **📊 当前版本**: V8.0  
> **🔄 状态**: ✅ 运行中

---

## 📊 当前策略表现

### V8+XRP 策略（2026-02-22 部署）

| 指标 | 预期表现 | 回测周期 |
|------|---------|---------|
| **预期收益** | **+10.17%** | 90天 |
| **胜率** | **70.0%** | 90天 |
| **最大回撤** | **3.55%** | 90天 |
| **交易频率** | 2-3次/周 | - |
| **夏普比率** | 2.87 | 风险调整收益 |

### 交易对配置

```
BTC/USDT:USDT  ← 比特币（核心）
ETH/USDT:USDT  ← 以太坊（核心）
DOGE/USDT:USDT ← 狗狗币（高波动）
XRP/USDT:USDT  ← 瑞波币（优化选择）
```

---

## 🚀 快速开始

### 1. 启动系统

```bash
cd /root/freqtrade
docker compose up -d freqtrade-futures
```

### 2. 查看状态

```bash
# 实时日志
docker logs -f freqtrade-futures

# 快速检查
./scripts/quick-check-v8-xrp.sh

# 详细监控
./scripts/monitor-v8-xrp.sh
```

### 3. 检查配置

```bash
# 查看当前配置
cat user_data/config_futures.json

# 查看策略参数
docker exec freqtrade-futures cat /freqtrade/user_data/strategies/SupertrendFuturesStrategyV8.py
```

---

## 📈 策略优化历程

### 版本对比（90天回测）

| 版本 | 收益 | 胜率 | 回撤 | 交易次数 | 评价 |
|------|------|------|------|---------|------|
| **V8+XRP** ⭐ | **+10.17%** | **70.0%** | **3.55%** | 30 | ✅ 当前最优 |
| V8(SOL) | +8.91% | 69.4% | 4.94% | 36 | ✅ 优秀 |
| V4 | +7.47% | 63.6% | 5.35% | 55 | ✅ 良好 |

### V8 核心改进

#### 1. Alpha#101 多因子过滤

```python
# 日内趋势强度指标
dataframe['alpha_101'] = (close - open) / (high - low + 0.001)
# 只在 alpha_101 > 0.1 时交易
```

**效果**：过滤假突破，提升信号质量

#### 2. RSI 温和范围

```python
# RSI 在 40-75 之间才交易
(dataframe['rsi'] > 40) & (dataframe['rsi'] < 75)
```

**效果**：避免极端区域，提升胜率

#### 3. 成交量确认

```python
# 成交量 > 1.2倍均值
dataframe['volume'] > dataframe['volume_ma'] * 1.2
```

**效果**：确保流动性，降低滑点

#### 4. 趋势强度评分

```python
# ADX > 30: +1分
# ADX > 35: +2分
# 至少需要1分
trend_score >= 1
```

**效果**：只交易强趋势

#### 5. 波动率控制

```python
# ATR/Close < 0.05
dataframe['volatility_ratio'] < 0.05
```

**效果**：避免极端波动，降低风险

---

## 🔄 XRP vs SOL 优化

### 交易对测试结果

**测试日期**: 2026-02-22  
**测试范围**: 90天回测

| 组合 | 收益 | 胜率 | 回撤 | 交易次数 | 排名 |
|------|------|------|------|---------|------|
| **BTC/ETH/DOGE/XRP** | **+10.17%** | **70.0%** | **3.55%** | 30 | 🥇 **最优** |
| BTC/ETH/SOL/DOGE | +8.91% | 69.4% | 4.94% | 36 | 🥈 良好 |
| BTC/ETH/SOL/MATIC | +2.46% | 67.9% | 3.80% | 28 | 🥉 一般 |
| BTC/ETH/SOL/LINK | +2.85% | 67.7% | 5.01% | 31 | ⚠️ 一般 |

### 核心发现

**BTC + ETH + DOGE 是核心三角** ✅

- **BTC/ETH**: 高流动性，稳定基础
- **DOGE**: 高波动性，提供盈利机会
- **第4币种**: XRP 表现最优

### XRP 优于 SOL 的原因

| 特性 | SOL | XRP ⭐ | 说明 |
|------|-----|-------|------|
| **流动性** | 高 | **高** | 都是主流币 |
| **波动性** | 很高 | **适中** | XRP 波动更稳定 |
| **趋势明确度** | 中 | **高** | XRP 趋势更清晰 |
| **假突破率** | 高 | **低** | XRP 更可靠 |
| **与核心组合协同** | 中 | **高** | XRP 互补性更好 |

---

## 🔧 系统配置

### 策略参数

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

### 核心指标参数

```python
{
  "atr_period": 11,
  "atr_multiplier": 2.884,
  "ema_fast": 48,
  "ema_slow": 151,
  "adx_threshold_long": 33,
  "adx_threshold_short": 23,
  "alpha_threshold": 0.1  # V8 特有
}
```

### 风险管理

```json
{
  "trailing_stop": true,
  "trailing_stop_positive": 0.02,
  "trailing_stop_positive_offset": 0.03,
  "trailing_only_offset_is_reached": true
}
```

---

## 📊 监控脚本

### 1. 快速状态检查

```bash
./scripts/quick-check-v8-xrp.sh
```

**输出内容**:
- ✅ 容器运行状态
- 📊 当前持仓数
- 💰 总盈亏

**使用场景**: 每日快速检查

### 2. 详细性能监控

```bash
./scripts/monitor-v8-xrp.sh
```

**输出内容**:
- 📦 容器详细状态
- ⚙️ 策略配置
- 💰 持仓详情
- 📊 最近交易
- 💵 账户状态
- 📈 交易统计

**使用场景**: 每周详细审查

---

## 📅 预期表现

### 月度预期

| 时间 | 预期收益 | 预期交易 | 累计收益 |
|------|---------|---------|---------|
| **1个月** | **+3.39%** | ~10次 | +3.39% |
| **2个月** | +6.78% | ~20次 | +6.78% |
| **3个月** | **+10.17%** | ~30次 | +10.17% |
| **6个月** | +20.34% | ~60次 | +22.40% (复利) |
| **12个月** | +40.68% | ~120次 | +50.57% (复利) |

### 保守估计

考虑到实盘滑点和市场变化，保守估计实际收益约为回测的 **60-80%**：

| 时间 | 保守收益 | 说明 |
|------|---------|------|
| 1个月 | +2-2.7% | 保守估计 |
| 3个月 | +7-8% | 合理预期 |
| 12个月 | +25-32% | 长期目标 |

---

## 🚨 告警规则

### 立即通知（紧急）

- ❌ **周亏损 > -5%**
- ❌ **机器人停止运行**
- ❌ **最大回撤 > 8%**

### 警告提醒（注意）

- ⚠️ **月收益 < +2%** (低于预期)
- ⚠️ **胜率 < 60%** (策略可能失效)
- ⚠️ **最大回撤 > 6%** (风险过高)
- ⚠️ **交易频率 < 1次/周** (信号过少)

---

## 🔬 研究文档

### 核心研究

| 文档 | 说明 |
|------|------|
| [V8+XRP 优化总结](docs/v8-xrp-optimization-summary.md) | 完整优化过程和数据 |
| [Walk-Forward 验证](research/walk-forward-report.md) | 180天分段验证 |
| [交易对优化](research/v8-pair-optimization.md) | SOL→XRP 分析 |
| [扩展测试报告](research/v8-expansion-test-report.md) | 交易对/持仓测试 |

### 策略文件

| 策略 | 说明 |
|------|------|
| `SupertrendFuturesStrategyV8.py` | 当前策略 ⭐ |
| `SupertrendFuturesStrategyV4.py` | 基础版本 |
| `SupertrendFuturesStrategyV8_1.py` | 频率优化版 |
| `SupertrendFuturesStrategyV8_2.py` | 平衡版 |

---

## 📁 项目结构

```
freqtrade-crypto-system/
├── strategies/                  # 策略文件
│   ├── SupertrendFuturesStrategyV8.py  ⭐ 当前
│   └── ...
├── scripts/                     # 监控脚本
│   ├── quick-check-v8-xrp.sh    # 快速检查
│   ├── monitor-v8-xrp.sh        # 详细监控
│   └── README.md
├── user_data/                   # 配置文件
│   ├── config_futures.json      # 合约配置
│   ├── config_spot.json         # 现货配置
│   └── strategies/              # 策略参数
├── docs/                        # 文档
│   ├── v8-xrp-optimization-summary.md
│   └── README.md
├── research/                    # 研究文档
│   ├── walk-forward-report.md
│   └── ...
├── README.md                    # 本文件（中文）
└── README_EN.md                 # 英文版
```

---

## 🎯 路线图

### 短期（1-2周）

- [x] V8+XRP 策略部署
- [x] 监控脚本创建
- [ ] 观察实盘表现
- [ ] 收集交易样本

### 中期（1-3个月）

- [ ] 信号质量评分（可选）
- [ ] 市场环境识别（可选）
- [ ] 策略微调

### 长期（3-6个月）

- [ ] 机器学习集成
- [ ] 多策略系统
- [ ] 风险管理优化

---

## 🔧 常用命令

### 日常管理

```bash
# 启动机器人
docker compose up -d freqtrade-futures

# 停止机器人
docker compose down freqtrade-futures

# 重启机器人
docker compose restart freqtrade-futures

# 查看日志
docker logs -f freqtrade-futures

# 查看最近日志
docker logs --tail 100 freqtrade-futures
```

### 监控检查

```bash
# 快速检查
./scripts/quick-check-v8-xrp.sh

# 详细监控
./scripts/monitor-v8-xrp.sh

# 查看持仓
docker exec freqtrade-futures freqtrade show-trades \
  --db-url sqlite:////freqtrade/user_data/tradesv3_futures.sqlite
```

### 回测验证

```bash
# 运行回测
docker exec freqtrade-futures freqtrade backtesting \
  --strategy SupertrendFuturesStrategyV8 \
  --timeframe 30m \
  --timerange 20251124-20260222 \
  --config user_data/config_futures.json
```

---

## 📊 性能历史

### 回测结果（90天）

| 版本 | 收益 | 胜率 | 回撤 | 夏普 |
|------|------|------|------|------|
| **V8+XRP** | **+10.17%** | **70.0%** | **3.55%** | **2.87** |
| V8(SOL) | +8.91% | 69.4% | 4.94% | 1.80 |
| V4 | +7.47% | 63.6% | 5.35% | 1.40 |

### 实盘跟踪

**开始时间**: 2026-02-22 16:25  
**跟踪文件**: [tracking/v8-xrp-performance.md](tracking/v8-xrp-performance.md)

*持续更新中...*

---

## 📞 故障排除

### 常见问题

**Q: 机器人不运行？**

```bash
# 检查容器状态
docker ps | grep freqtrade

# 重启容器
docker compose restart freqtrade-futures
```

**Q: 长时间没有交易？**

- 正常：V8 是低频策略（平均3天1次）
- 检查：确认配置正确
- 等待：耐心等待信号

**Q: 回撤过大？**

- 警告：回撤 > 6%
- 检查：最近交易记录
- 考虑：暂停策略

---

## 📝 更新日志

### v8.0 (2026-02-22)

**重大更新**:
- ✅ 升级到 V8 策略（多因子温和版）
- ✅ 优化交易对：SOL → XRP
- ✅ 收益提升：+8.91% → +10.17%
- ✅ 风险降低：4.94% → 3.55% 回撤

**技术改进**:
- ✅ 添加 Alpha#101 过滤
- ✅ 优化 RSI 范围
- ✅ 完善趋势评分
- ✅ 创建监控脚本

**文档更新**:
- ✅ 统一中英文文档
- ✅ 添加详细研究文档
- ✅ 完善使用指南

---

## 📄 许可证

私有仓库，仅供个人使用。

---

## 🔗 相关链接

- **GitHub**: https://github.com/jinzheng8115/freqtrade-crypto-system
- **Freqtrade**: https://github.com/freqtrade/freqtrade
- **OKX**: https://www.okx.com/

---

<div align="center">

**[📖 English Version | 英文版](README_EN.md)**

---

**最后更新**: 2026-02-22 17:30  
**版本**: v8.0  
**状态**: ✅ 运行中

</div>
