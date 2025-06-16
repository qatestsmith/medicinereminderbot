# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Medicine Reminder Bot - A Telegram bot for elderly users to receive medication reminders in Ukrainian. Designed for Raspberry Pi 5 deployment with Docker containerization.

## Architecture

- **Language**: Python 3.11+
- **Framework**: python-telegram-bot library with AsyncIO
- **Database**: SQLite with custom Database class
- **Scheduler**: APScheduler for automated reminders
- **Deployment**: Docker with docker-compose
- **Target Platform**: Raspberry Pi 5

## Key Components

- `app/bot.py` - Main application entry point with conversation handlers
- `app/database.py` - Database operations and schema management
- `app/scheduler.py` - Reminder scheduling system using APScheduler
- `app/handlers/main_handlers.py` - Telegram bot handlers and Ukrainian interface
- `app/handlers/auth.py` - User authorization checking
- `app/utils/helpers.py` - Utility functions for validation and formatting

## Database Schema

- `users` - Telegram user info with timezone preferences
- `medicines` - User medications
- `reminders` - Scheduled reminders with time and dosage
- `reminder_logs` - Tracking sent reminders

## Configuration Files

- `app/config/bot_token.txt` - Telegram bot token (gitignored)
- `app/config/allowed_users.txt` - Approved user IDs (gitignored)
- `app/config/timezones.json` - Available timezone options
- `app/config/settings.json` - Bot configuration

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot locally (requires config files)
cd app && python bot.py

# Create database backup
cd app && python backup.py create

# Build and run with Docker
docker-compose up --build

# Run backup inside container
docker exec med-reminder-bot python backup.py create
```

## Setup Requirements

1. Create `app/config/bot_token.txt` with Telegram bot token
2. Create `app/config/allowed_users.txt` with authorized Telegram user IDs
3. Ensure Docker and docker-compose are installed for deployment

## Ukrainian Interface

All user interactions are in Ukrainian with large button-based navigation. Time format is 24-hour (HH:MM). The bot includes input validation for time and dosage formats with elderly-friendly error messages.

## Conversation Flow

The bot uses ConversationHandler for multi-step medicine addition:
1. Timezone selection (new users)
2. Medicine name input
3. Time selection (with preset buttons)
4. Dosage input
5. Confirmation
6. Option to add more times

## Testing

The bot requires live Telegram integration for testing. Test with authorized user IDs in a development environment before production deployment.