#!/bin/bash

echo "🤖 Starting Medicine Reminder Bot with Reminder Service"
echo "======================================================"

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BOT_PID $REMINDER_PID 2>/dev/null
    wait $BOT_PID $REMINDER_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Start the bot in background
echo "🚀 Starting main bot..."
python medicine_bot.py &
BOT_PID=$!

# Wait a moment for bot to start
sleep 2

# Start the reminder service in background
echo "⏰ Starting reminder service..."
python reminder_service.py &
REMINDER_PID=$!

echo ""
echo "✅ Both services are running!"
echo "📱 Bot PID: $BOT_PID"
echo "⏰ Reminder PID: $REMINDER_PID"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Wait for either process to exit
wait $BOT_PID $REMINDER_PID