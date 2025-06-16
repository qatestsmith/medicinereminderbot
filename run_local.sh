#!/bin/bash

echo "🤖 Setting up local development environment"
echo "=========================================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Add your bot token to app/config/bot_token.txt"
echo "2. Add your Telegram user ID to app/config/allowed_users.txt"
echo "3. Run: source venv/bin/activate && cd app && python bot.py"
echo ""
echo "📋 Quick commands:"
echo "  source venv/bin/activate     # Activate environment"
echo "  cd app && python bot.py      # Run bot"
echo "  python app/backup.py create  # Create backup"