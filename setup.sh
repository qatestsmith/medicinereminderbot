#!/bin/bash

echo "🤖 Medicine Reminder Bot Setup"
echo "=============================="

# Check if config files exist
if [ ! -f "app/config/bot_token.txt" ]; then
    echo "❌ Missing bot_token.txt"
    echo "Please create app/config/bot_token.txt with your Telegram bot token"
    echo "Get a token from @BotFather on Telegram"
    exit 1
fi

if [ ! -f "app/config/allowed_users.txt" ]; then
    echo "❌ Missing allowed_users.txt"
    echo "Please create app/config/allowed_users.txt with authorized Telegram user IDs"
    echo "Add one user ID per line"
    exit 1
fi

echo "✅ Configuration files found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose first."
    exit 1
fi

echo "✅ Docker found"

# Build and start
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting bot..."
docker-compose up -d

echo ""
echo "✅ Bot started successfully!"
echo ""
echo "📋 Useful commands:"
echo "  docker-compose logs -f          # View logs"
echo "  docker-compose stop             # Stop bot"
echo "  docker-compose restart          # Restart bot"
echo "  docker exec med-reminder-bot python backup.py create  # Create backup"
echo ""
echo "🔍 Check status:"
echo "  docker-compose ps"