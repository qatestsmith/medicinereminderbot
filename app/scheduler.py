import asyncio
import logging
from datetime import datetime, time
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from database import Database
from utils.helpers import format_reminder_message

class ReminderScheduler:
    def __init__(self, bot: Bot, database: Database):
        self.bot = bot
        self.db = database
        self.scheduler = AsyncIOScheduler()
        self.setup_scheduler()
    
    def setup_scheduler(self):
        """Setup the reminder scheduler"""
        # Schedule reminder checks every minute
        self.scheduler.add_job(
            self.check_and_send_reminders,
            CronTrigger(second=0),  # Run at the start of every minute
            id='reminder_checker',
            max_instances=1
        )
        logging.info("Reminder scheduler configured")
    
    async def check_and_send_reminders(self):
        """Check for due reminders and send them"""
        try:
            current_time = datetime.now()
            reminders = self.db.get_all_active_reminders()
            
            for reminder in reminders:
                # Parse user timezone
                try:
                    user_tz = pytz.timezone(reminder['timezone'])
                    user_current_time = current_time.astimezone(user_tz)
                    current_time_str = user_current_time.strftime("%H:%M")
                    
                    # Check if it's time for this reminder
                    if current_time_str == reminder['time']:
                        await self.send_reminder(reminder)
                        
                except Exception as e:
                    logging.error(f"Error processing reminder {reminder['reminder_id']}: {e}")
                    
        except Exception as e:
            logging.error(f"Error in reminder checker: {e}")
    
    async def send_reminder(self, reminder: dict):
        """Send a single reminder to user"""
        try:
            message = format_reminder_message(
                reminder['medicine_name'],
                reminder['dosage'], 
                reminder['time']
            )
            
            await self.bot.send_message(
                chat_id=reminder['telegram_id'],
                text=message
            )
            
            # Log the reminder
            self.db.log_reminder_sent(reminder['reminder_id'])
            logging.info(f"Reminder sent to user {reminder['telegram_id']} for {reminder['medicine_name']}")
            
        except Exception as e:
            logging.error(f"Failed to send reminder to user {reminder['telegram_id']}: {e}")
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logging.info("Reminder scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logging.info("Reminder scheduler stopped")