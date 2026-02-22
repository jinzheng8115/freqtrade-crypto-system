#!/bin/bash
# Setup script for Freqtrade Crypto Trading System
# This script automates the setup process

set -e  # Exit on error

echo "🚀 Setting up Freqtrade Crypto Trading System..."

# Step 1: Create directory structure
echo "📁 Creating directory structure..."
mkdir -p user_data/strategies
mkdir -p user_data/logs
mkdir -p user_data/data

# Step 2: Copy strategy files
echo "📋 Copying strategy files..."
cp strategies/SupertrendStrategy_Smart.py user_data/strategies/
cp strategies/SupertrendFuturesStrategyV4.py user_data/strategies/

# Step 3: Copy config templates
echo "⚙️  Copying config templates..."
cp config/config_spot.json.example user_data/config_spot.json
cp config/config_futures.json.example user_data/config_futures.json

# Step 4: Remind user to add API keys
echo ""
echo "⚠️  IMPORTANT: Add your API keys to config files!"
echo ""
echo "Edit these files:"
echo "  - user_data/config_spot.json"
echo "  - user_data/config_futures.json"
echo ""
echo "Replace these placeholders:"
echo "  - YOUR_API_KEY_HERE"
echo "  - YOUR_API_SECRET_HERE"
echo ""

# Step 5: Ask if user wants to start bots
read -p "🤖 Start bots now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "🚀 Starting bots..."
    docker-compose up -d

    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "📊 Bot status:"
    docker-compose ps

    echo ""
    echo "📖 Next steps:"
    echo "  1. Add your API keys to config files"
    echo "  2. Download historical data:"
    echo "     docker exec freqtrade-spot freqtrade download-data --exchange okx --pairs BTC/USDT ETH/USDT SOL/USDT DOGE/USDT --timeframes 15m --timerange 20251123- --trading-mode spot"
    echo "     docker exec freqtrade-futures freqtrade download-data --exchange okx --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT --timeframes 15m --timerange 20250901- --trading-mode futures --erase"
    echo "  3. Monitor logs: docker-compose logs -f"
    echo ""
else
    echo ""
    echo "✅ Directory structure created!"
    echo ""
    echo "📖 Next steps:"
    echo "  1. Add your API keys to:"
    echo "     - user_data/config_spot.json"
    echo "     - user_data/config_futures.json"
    echo "  2. Start bots: docker-compose up -d"
    echo "  3. Download data: See QUICKSTART.md"
    echo ""
fi
