#!/usr/bin/env python3
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from utils.helpers import load_bot_token

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Привіт! Бот працює!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text('Допомога: /start - почати роботу з ботом')

def main() -> None:
    """Start the bot."""
    # Load bot token
    token = load_bot_token()
    if not token:
        logger.error("Bot token not found. Please check config/bot_token.txt")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()