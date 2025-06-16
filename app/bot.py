#!/usr/bin/env python3
import asyncio
import logging
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from database import Database
from handlers.main_handlers import BotHandlers
from scheduler import ReminderScheduler
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
        self.scheduler = None
        
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
    
    async def start_scheduler(self):
        """Start the reminder scheduler"""
        if not self.scheduler:
            bot = self.application.bot
            self.scheduler = ReminderScheduler(bot, self.db)
            self.scheduler.start()
    
    async def stop_scheduler(self):
        """Stop the reminder scheduler"""
        if self.scheduler:
            self.scheduler.stop()
            self.scheduler = None
    
    async def start_bot(self):
        """Start the bot"""
        try:
            # Start the scheduler
            await self.start_scheduler()
            
            # Start polling
            self.logger.info("Bot started successfully")
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
                
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop_bot(self):
        """Stop the bot gracefully"""
        try:
            self.logger.info("Stopping bot...")
            
            # Stop scheduler
            await self.stop_scheduler()
            
            # Stop the application
            await self.application.stop()
            await self.application.shutdown()
            
            self.logger.info("Bot stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(self.stop_bot())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main function"""
    bot = MedicineReminderBot()
    
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        await bot.stop_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)