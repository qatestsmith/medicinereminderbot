#!/usr/bin/env python3
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from utils.helpers import load_bot_token

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Привіт! Бот працює! 🤖')

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Допомога: /start - почати роботу з ботом')

def main() -> None:
    """Start the bot."""
    # Load bot token
    token = load_bot_token()
    if not token:
        logger.error("Bot token not found. Please check config/bot_token.txt")
        return
    
    # Create the Updater
    updater = Updater(token)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # Start the Bot
    logger.info("Starting bot...")
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()