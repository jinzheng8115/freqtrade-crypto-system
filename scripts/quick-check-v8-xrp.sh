#!/bin/bash
# V8+XRP 快速状态检查

echo "🔍 V8+XRP 快速状态检查"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 容器状态
STATUS=$(docker ps | grep freqtrade-futures)
if [ -n "$STATUS" ]; then
    echo "✅ 容器: 运行中"
else
    echo "❌ 容器: 未运行"
fi

# 持仓数
POSITIONS=$(docker exec freqtrade-futures freqtrade show-trades --db-url sqlite:////freqtrade/user_data/tradesv3_futures.sqlite --print-json 2>/dev/null | jq '[.[] | select(.is_open == true)] | length' 2>/dev/null || echo "0")
echo "📊 持仓数: $POSITIONS / 2"

# 最近盈亏
PROFIT=$(docker exec freqtrade-futures freqtrade profit --db-url sqlite:////freqtrade/user_data/tradesv3_futures.sqlite 2>/dev/null | grep "TOTAL" | awk '{print $NF}' | tr -d 'USDT' || echo "N/A")
echo "💰 总盈亏: $PROFIT USDT"

echo ""
echo "✨ 状态正常"
