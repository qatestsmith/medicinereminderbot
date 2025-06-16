#!/usr/bin/env python3
import asyncio
import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from database import Database
from handlers.main_handlers import BotHandlers
from utils.helpers import load_bot_token, load_config, setup_logging

# Conversation states
(SELECTING_TIMEZONE, ADDING_MEDICINE_NAME, ADDING_MEDICINE_TIME, 
 ADDING_MEDICINE_DOSAGE, CONFIRMING_MEDICINE, ADDING_MORE_TIMES,
 EDITING_MEDICINE_SELECT, EDITING_MEDICINE_ACTION) = range(8)

class MedicineReminderBot:
    def __init__(self):
        # Setup logging
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = load_config()
        bot_token = load_bot_token()
        
        if not bot_token:
            self.logger.error("Bot token not found. Please check config/bot_token.txt")
            sys.exit(1)
        
        # Initialize components
        self.db = Database()
        self.application = Application.builder().token(bot_token).build()
        self.handlers = BotHandlers(self.db)
        
        # Setup handlers
        self.setup_handlers()
        
        self.logger.info("Medicine Reminder Bot initialized")
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        
        # Conversation handler for adding medicines
        add_medicine_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.handlers.start_command),
                MessageHandler(filters.Regex('^➕ Додати ліки$'), self.handlers.handle_add_medicine)
            ],
            states={
                SELECTING_TIMEZONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_timezone_selection)
                ],
                ADDING_MEDICINE_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_medicine_name)
                ],
                ADDING_MEDICINE_TIME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_medicine_time)
                ],
                ADDING_MEDICINE_DOSAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_medicine_dosage)
                ],
                CONFIRMING_MEDICINE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_medicine_confirmation)
                ],
                ADDING_MORE_TIMES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_adding_more_times)
                ]
            },
            fallbacks=[
                MessageHandler(filters.Regex('^❌ Скасувати$'), self.handlers.handle_cancel),
                CommandHandler('cancel', self.handlers.handle_cancel)
            ]
        )
        
        # Add handlers to application
        self.application.add_handler(add_medicine_handler)
        
        # Other message handlers
        self.application.add_handler(MessageHandler(
            filters.Regex('^📋 Мої ліки$'), 
            self.handlers.handle_show_medicines
        ))
        
        self.application.add_handler(MessageHandler(
            filters.Regex('^❓ Допомога$'), 
            self.handlers.handle_help
        ))
        
        # Catch-all handler for unknown messages
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handlers.handle_unknown
        ))
        
        self.logger.info("Bot handlers configured")
    
    def run(self):
        """Run the bot"""
        self.logger.info("Starting bot...")
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

def main():
    """Main function"""
    bot = MedicineReminderBot()
    bot.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)