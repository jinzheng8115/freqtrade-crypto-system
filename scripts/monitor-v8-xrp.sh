#!/bin/bash
# V8+XRP 性能监控脚本
# 每周运行一次，统计性能数据

echo "=========================================="
echo "V8+XRP 实盘性能监控"
echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 1. 检查容器状态
echo "📦 容器状态:"
docker ps | grep freqtrade-futures | awk '{print "  ✅ 运行中 (" $1 ")"}' || echo "  ❌ 未运行"
echo ""

# 2. 检查策略配置
echo "⚙️  策略配置:"
STRATEGY=$(docker exec freqtrade-futures cat /freqtrade/user_data/config_futures.json 2>/dev/null | grep -A 4 "pair_whitelist" | grep -o '"[^"]*"' | tr '\n' ' ')
echo "  交易对: $STRATEGY"
echo ""

# 3. 检查当前持仓
echo "💰 当前持仓:"
docker exec freqtrade-futures freqtrade show-trades --db-url sqlite:////freqtrade/user_data/tradesv3_futures.sqlite --print-json 2>/dev/null | jq -r '.[] | select(.is_open == true) | "  \(.pair): \(.amount) @ \(.open_rate) (\(.profit_ratio * 100)%)"' || echo "  无持仓"
echo ""

# 4. 检查最近交易
echo "📊 最近交易 (最近7天):"
docker logs freqtrade-futures --since 168h 2>&1 | grep -E "Entry signal|Exit signal" | tail -10
echo ""

# 5. 检查账户余额
echo "💵 账户状态:"
docker exec freqtrade-futures freqtrade profit --db-url sqlite:////freqtrade/user_data/tradesv3_futures.sqlite 2>/dev/null | grep -A 5 "TOTAL" | tail -6
echo ""

# 6. 检查交易次数
echo "📈 交易统计 (部署以来):"
TRADE_COUNT=$(docker logs freqtrade-futures 2>&1 | grep -c "Entry signal" || echo "0")
echo "  总交易信号: $TRADE_COUNT 次"
echo ""

echo "=========================================="
echo "监控完成"
echo "=========================================="
echo ""
echo "📝 预期目标:"
echo "  月收益: +3.39%"
echo "  胜率: 70%"
echo "  交易频率: 2-3次/周"
echo ""
echo "📊 对比分析:"
echo "  [需要手动对比实际 vs 预期]"
echo ""
