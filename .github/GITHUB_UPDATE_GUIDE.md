# GitHub 更新流程

> 每次更新 Freqtrade 相关文件后，应同步更新 README.md

---

## 快速更新清单

### 1️⃣ 检查需要提交的文件

```bash
cd /root/freqtrade
git status
```

### 2️⃣ 更新 README.md（如有必要）

**必须更新的部分**：
- [ ] **最后更新日期**（底部）
- [ ] **版本号**（如有重大更改）
- [ ] **策略/交易对变更**
- [ ] **回测/实盘结果**
- [ ] **新增功能**

**可选更新的部分**：
- [ ] 部署指南
- [ ] 未来工作
- [ ] 结论

### 3️⃣ 提交更改

```bash
# 添加所有更改
git add -A

# 提交（使用规范的 commit message）
git commit -m "type: brief description

- detail 1
- detail 2"

# 推送到 GitHub
git push origin main
```

---

## Commit Message 规范

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | feat: Add SUI and BONK trading pairs |
| `fix` | 修复bug | fix: Correct EMA parameter loading |
| `docs` | 文档更新 | docs: Update README for V9.0 |
| `refactor` | 重构代码 | refactor: Improve strategy structure |
| `test` | 测试相关 | test: Add backtest for PEPE |
| `chore` | 杂项 | chore: Update docker-compose |

---

## 版本号规则

- **Major (X.0)**: 策略架构重大改变
  - V8.0 → V9.0: 单策略 → 多交易对独立策略
  
- **Minor (8.X)**: 功能更新
  - V8.1: 添加新交易对
  - V8.2: 添加新指标

- **Patch (8.1.X)**: 小修改
  - 参数优化
  - Bug修复

---

## 重要文件说明

| 文件 | 敏感性 | 提交规则 |
|------|--------|----------|
| `config_futures.json` | ❌ 高（含API key） | 不提交（.gitignore） |
| `config_futures.example.json` | ✅ 低 | 提交 |
| `strategies/*.py` | ✅ 低 | 提交 |
| `strategies/*.json` | ✅ 低 | 提交（优化参数） |
| `README.md` | ✅ 低 | 提交 |
| `STRATEGY_CONFIG.md` | ✅ 低 | 提交 |
| `docker-compose.yml` | ✅ 低 | 提交 |
| `backtest_results/` | ✅ 低 | 可选（体积大） |
| `data/` | ✅ 低 | 不提交（体积大） |

---

## 当前版本信息

**最新版本**: V9.0 MultiPair  
**更新日期**: 2026-02-23  
**主要变更**:
- 多交易对独立策略
- 4个交易对（DOGE, UNI, SUI, BONK）
- 波动率动态仓位
- 交易对特定过滤

---

## 示例：完整更新流程

```bash
# 1. 检查更改
cd /root/freqtrade
git status

# 2. 编辑 README.md
vim README.md
# 更新：最后更新日期、版本号、交易对、结果等

# 3. 添加所有更改
git add -A

# 4. 提交
git commit -m "feat: Add volatility-based dynamic position sizing

- Implement custom_stake_amount based on 24h volatility
- Low volatility (<2%): 333 USDT (+33%)
- High volatility (>6%): 125 USDT (-50%)
- Update README with new risk management section"

# 5. 推送
git push origin main

# 6. 验证
echo "✅ GitHub updated successfully"
```

---

*最后更新: 2026-02-23*
