# Medicine Reminder Bot

A Telegram bot for elderly users to receive medication reminders in Ukrainian. Designed for Raspberry Pi 5 deployment.

## Features

- 🇺🇦 Ukrainian interface with large buttons
- 💊 Medicine management (add, view, edit)
- ⏰ Multiple daily reminders per medicine
- 🕐 24-hour time format
- 🌍 Timezone support
- 🔐 Admin-controlled user access
- 📱 Elderly-friendly interface
- 💾 Automatic database backups

## Quick Setup

1. **Get a Telegram Bot Token**
   - Message @BotFather on Telegram
   - Create a new bot and get the token

2. **Configure the Bot**
   ```bash
   # Copy your bot token
   echo "YOUR_BOT_TOKEN_HERE" > app/config/bot_token.txt
   
   # Add authorized user IDs (one per line)
   echo "123456789" > app/config/allowed_users.txt
   ```

3. **Run the Bot**
   ```bash
   # Make setup script executable
   chmod +x setup.sh
   
   # Run setup
   ./setup.sh
   ```

## Manual Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**
   - Copy `app/config/bot_token.txt.example` to `app/config/bot_token.txt`
   - Copy `app/config/allowed_users.txt.example` to `app/config/allowed_users.txt`
   - Edit both files with your values

3. **Run Locally**
   ```bash
   cd app && python bot.py
   ```

4. **Run with Docker**
   ```bash
   docker-compose up --build
   ```

## Usage

1. Start the bot: `/start`
2. Select your timezone (new users only)
3. Use the main menu:
   - ➕ **Add Medicine** - Add new medications with reminders
   - 📋 **My Medicines** - View all saved medications
   - ✏️ **Edit Medicines** - Modify or delete medications
   - ❓ **Help** - Show help information

## Backup

```bash
# Create backup
docker exec med-reminder-bot python backup.py create

# List backups
docker exec med-reminder-bot python backup.py list

# Restore backup
docker exec med-reminder-bot python backup.py restore --backup-file backups/backup_2024-01-01_12-00.db
```

## Configuration

- **User Access**: Edit `app/config/allowed_users.txt` (auto-reloads)
- **Timezones**: Edit `app/config/timezones.json`
- **Settings**: Edit `app/config/settings.json`

## Architecture

- **Backend**: Python 3.11+ with python-telegram-bot
- **Database**: SQLite with automated backups
- **Scheduler**: APScheduler for reminders
- **Deployment**: Docker on Raspberry Pi 5
- **Interface**: Ukrainian with button navigation
