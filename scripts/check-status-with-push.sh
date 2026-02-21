#!/bin/bash
# Freqtrade 机器人状态检查脚本（精确版 - 使用正确的数据库文件）
# 用途：定期检查交易机器人运行状态和表现，并推送到 Telegram

WORKSPACE="/root/.openclaw/agents/freqtrade"
LOG_FILE="$WORKSPACE/logs/status-check.log"
MEMORY_FILE="$WORKSPACE/memory/$(date +%Y-%m-%d).md"
TELEGRAM_TARGET="-5042944002"  # Crypto量化交易助理群组

# 创建日志目录
mkdir -p "$WORKSPACE/logs"

# 记录日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "=== Freqtrade 状态检查开始 ==="

# 1. 检查机器人运行状态
SPOT_STATUS=$(docker inspect -f '{{.State.Status}}' freqtrade-spot 2>/dev/null)
FUTURES_STATUS=$(docker inspect -f '{{.State.Status}}' freqtrade-futures 2>/dev/null)

log "现货机器人: $SPOT_STATUS"
log "合约机器人: $FUTURES_STATUS"

# 2. 检查持仓数量（从数据库查询 - 使用正确的文件名）
SPOT_POSITIONS=$(docker exec freqtrade-spot sqlite3 /freqtrade/user_data/tradesv3_spot.sqlite "SELECT COUNT(*) FROM trades WHERE is_open = 1;" 2>/dev/null || echo "0")
FUTURES_POSITIONS=$(docker exec freqtrade-futures sqlite3 /freqtrade/user_data/tradesv3_futures.sqlite "SELECT COUNT(*) FROM trades WHERE is_open = 1;" 2>/dev/null || echo "0")

log "现货持仓: $SPOT_POSITIONS"
log "合约持仓: $FUTURES_POSITIONS"

# 3. 检查最近交易（从日志提取）
SPOT_TRADES=$(docker logs freqtrade-spot --tail 100 2>&1 | grep -E "(enter_long|exit_long)" | tail -3)
FUTURES_TRADES=$(docker logs freqtrade-futures --tail 100 2>&1 | grep -E "(enter_long|enter_short|exit_long|exit_short)" | tail -3)

# 4. 生成状态报告
if [ "$SPOT_STATUS" = "running" ] && [ "$FUTURES_STATUS" = "running" ]; then
    OVERALL_STATUS="✅ 正常"
    STATUS_EMOJI="✅"
elif [ "$SPOT_STATUS" = "running" ] || [ "$FUTURES_STATUS" = "running" ]; then
    OVERALL_STATUS="⚠️ 部分异常"
    STATUS_EMOJI="⚠️"
else
    OVERALL_STATUS="❌ 严重异常"
    STATUS_EMOJI="❌"
fi

# 5. 构建推送消息（无HTML标签）
MESSAGE="$STATUS_EMOJI 【Freqtrade 状态监控】 - $(date '+%H:%M')

【整体状态】: $OVERALL_STATUS

【机器人状态】:
• 现货: $([ "$SPOT_STATUS" = "running" ] && echo "✅" || echo "❌") $([ "$SPOT_STATUS" = "running" ] && echo "运行中" || echo "已停止")
• 合约: $([ "$FUTURES_STATUS" = "running" ] && echo "✅" || echo "❌") $([ "$FUTURES_STATUS" = "running" ] && echo "运行中" || echo "已停止")

【持仓情况】:
• 现货: $SPOT_POSITIONS 个
• 合约: $FUTURES_POSITIONS 个

【最近交易】: $([ -n "$SPOT_TRADES$FUTURES_TRADES" ] && echo "有信号" || echo "无信号")

⏰ 检查时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 6. 推送到 Telegram
log "推送消息到 Telegram..."
openclaw message send --channel telegram --target "$TELEGRAM_TARGET" --message "$MESSAGE" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✅ 推送成功"
else
    log "❌ 推送失败"
fi

# 7. 更新每日记录
if [ ! -f "$MEMORY_FILE" ]; then
    echo "# $(date '+%Y-%m-%d') - Freqtrade 每日记录" > "$MEMORY_FILE"
fi

echo "
## 状态检查 - $(date '+%H:%M')
- 现货: $SPOT_STATUS (持仓: $SPOT_POSITIONS)
- 合约: $FUTURES_STATUS (持仓: $FUTURES_POSITIONS)
" >> "$MEMORY_FILE"

log "=== 检查完成 ==="
echo "✅ 状态检查完成并已推送"
