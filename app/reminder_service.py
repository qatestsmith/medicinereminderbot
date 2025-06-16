#!/usr/bin/env python3
import asyncio
import logging
import time
from datetime import datetime
import pytz
import httpx
from database import Database
from utils.helpers import load_bot_token, format_reminder_message, setup_logging

class ReminderService:
    def __init__(self):
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        self.bot_token = load_bot_token()
        if not self.bot_token:
            self.logger.error("Bot token not found")
            return
        
        self.db = Database()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.logger.info("Reminder service initialized")
    
    async def send_message(self, chat_id: int, text: str):
        """Send message via Telegram API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML"
                    }
                )
                if response.status_code == 200:
                    return True
                else:
                    self.logger.error(f"Failed to send message to {chat_id}: HTTP {response.status_code}")
                    return False
        except httpx.TimeoutException:
            self.logger.error(f"Timeout sending message to {chat_id}")
            return False
        except httpx.ConnectError:
            self.logger.error(f"Connection error sending message to {chat_id}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending message to {chat_id}: {e}")
            return False
    
    async def check_and_send_reminders(self):
        """Check for due reminders and send them"""
        try:
            reminders = self.db.get_all_active_reminders()
            current_time = datetime.now()
            
            self.logger.debug(f"Checking {len(reminders)} reminders at {current_time}")
            
            for reminder in reminders:
                try:
                    # Parse user timezone
                    user_tz = pytz.timezone(reminder['timezone'])
                    user_current_time = current_time.astimezone(user_tz)
                    current_time_str = user_current_time.strftime("%H:%M")
                    
                    self.logger.debug(
                        f"Reminder {reminder['reminder_id']}: "
                        f"scheduled={reminder['time']}, current={current_time_str}"
                    )
                    
                    # Check if it's time for this reminder
                    if current_time_str == reminder['time']:
                        # Check if we already sent this reminder in the last 2 minutes
                        # to avoid duplicate sends
                        recent_logs = self.db.get_recent_reminder_logs(
                            reminder['reminder_id'], 
                            minutes=2
                        )
                        
                        if recent_logs:
                            self.logger.debug(
                                f"Reminder {reminder['reminder_id']} already sent recently, skipping"
                            )
                            continue
                        
                        message = format_reminder_message(
                            reminder['medicine_name'],
                            reminder['dosage'],
                            reminder['time']
                        )
                        
                        self.logger.info(
                            f"Sending reminder to user {reminder['telegram_id']} "
                            f"for {reminder['medicine_name']} at {reminder['time']}"
                        )
                        
                        success = await self.send_message(
                            reminder['telegram_id'],
                            message
                        )
                        
                        if success:
                            self.db.log_reminder_sent(reminder['reminder_id'])
                            self.logger.info(
                                f"✅ Reminder sent successfully to user {reminder['telegram_id']} "
                                f"for {reminder['medicine_name']}"
                            )
                        else:
                            self.logger.error(
                                f"❌ Failed to send reminder to user {reminder['telegram_id']} "
                                f"for {reminder['medicine_name']}"
                            )
                            
                except Exception as e:
                    self.logger.error(f"Error processing reminder {reminder['reminder_id']}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in reminder checker: {e}")
    
    async def run_reminder_loop(self):
        """Main reminder loop"""
        self.logger.info("Starting reminder service...")
        
        while True:
            try:
                await self.check_and_send_reminders()
                # Sleep for 60 seconds (check every minute)
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                self.logger.info("Reminder service stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in reminder loop: {e}")
                await asyncio.sleep(60)  # Continue after error

async def main():
    """Main function"""
    service = ReminderService()
    await service.run_reminder_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Reminder service stopped")
    except Exception as e:
        logging.error(f"Fatal error: {e}")