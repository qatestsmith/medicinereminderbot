#!/usr/bin/env python3
import asyncio
import logging
import sys
import threading
import time
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from database import Database
from handlers.auth import check_user_access
from utils.helpers import (
    load_bot_token, load_config, setup_logging, get_timezone_list, 
    format_medicine_list, validate_time_format, validate_dosage, format_reminder_message
)

# Conversation states
(SELECTING_TIMEZONE, ADDING_MEDICINE_NAME, ADDING_MEDICINE_TIME, 
 ADDING_MEDICINE_DOSAGE, CONFIRMING_MEDICINE, ADDING_MORE_TIMES, 
 CHANGING_TIMEZONE, DELETING_MEDICINE_SELECT, DELETING_REMINDER_SELECT,
 CONFIRMING_DELETION, CONFIRMING_DELETE_ALL) = range(11)

class MedicineBot:
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
        self.application = (
            Application.builder()
            .token(bot_token)
            .job_queue(None)  # Disable job queue to avoid weak reference issue
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .pool_timeout(30)
            .build()
        )
        
        # Setup handlers
        self.setup_handlers()
        
        # Reminder system
        self.reminder_thread = None
        self.reminder_running = False
        
        self.logger.info("Medicine Reminder Bot initialized")
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        
        # Conversation handler for adding medicines
        add_medicine_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start_command),
                MessageHandler(filters.Regex('^➕ Додати ліки$'), self.handle_add_medicine),
                MessageHandler(filters.Regex('^➕ Додати ще$'), self.handle_add_medicine),
                MessageHandler(filters.Regex('^🌍 Змінити часовий пояс$'), self.handle_change_timezone),
                MessageHandler(filters.Regex('^🗑️ Видалити ліки$'), self.handle_delete_medicine),
                MessageHandler(filters.Regex('^🗑️ Видалити обрані ліки$'), self.handle_delete_medicine),
                MessageHandler(filters.Regex('^⚠️ Видалити ВСІ ліки$'), self.handle_delete_all_medicines)
            ],
            states={
                SELECTING_TIMEZONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_timezone_selection)
                ],
                ADDING_MEDICINE_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_medicine_name)
                ],
                ADDING_MEDICINE_TIME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_medicine_time)
                ],
                ADDING_MEDICINE_DOSAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_medicine_dosage)
                ],
                CONFIRMING_MEDICINE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_medicine_confirmation)
                ],
                ADDING_MORE_TIMES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_adding_more_times)
                ],
                CHANGING_TIMEZONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_timezone_change_selection)
                ],
                DELETING_MEDICINE_SELECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_medicine_selection_for_deletion)
                ],
                DELETING_REMINDER_SELECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reminder_selection_for_deletion)
                ],
                CONFIRMING_DELETION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_deletion_confirmation)
                ],
                CONFIRMING_DELETE_ALL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_delete_all_confirmation)
                ]
            },
            fallbacks=[
                MessageHandler(filters.Regex('^❌ Скасувати$'), self.handle_cancel),
                CommandHandler('cancel', self.handle_cancel)
            ]
        )
        
        # Add handlers to application
        self.application.add_handler(add_medicine_handler)
        
        # Other message handlers
        self.application.add_handler(MessageHandler(
            filters.Regex('^📋 Мої ліки$'), 
            self.handle_show_medicines
        ))
        
        self.application.add_handler(MessageHandler(
            filters.Regex('^❓ Допомога$'), 
            self.handle_help
        ))
        
        # Catch-all handler for unknown messages
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_unknown
        ))
        
        self.logger.info("Bot handlers configured")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not await check_user_access(update, context):
            return
        
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Check if user exists
        user = self.db.get_user(user_id)
        
        if not user:
            # New user - show timezone selection
            await self.show_timezone_selection(update, context)
            return SELECTING_TIMEZONE
        else:
            # Existing user - show main menu
            await self.show_main_menu(update, context)
            return ConversationHandler.END
    
    async def show_timezone_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show timezone selection for new users"""
        timezones = get_timezone_list()
        keyboard = []
        
        timezone_labels = {
            "Відень": "Відень UTC+1/+2",
            "Київ": "Київ UTC+2/+3", 
            "Харків": "Харків UTC+2/+3",
            "Сіетл": "Сіетл UTC-8/-7",
            "Старобільськ": "Старобільськ UTC+3"
        }
        
        for city_name in timezones.keys():
            label = timezone_labels.get(city_name, f"{city_name}")
            keyboard.append([KeyboardButton(label)])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            "🌍 Ласкаво просимо до Медичного Помічника!\n\n"
            "Оберіть ваш часовий пояс:",
            reply_markup=reply_markup
        )
    
    async def handle_timezone_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle timezone selection"""
        selected = update.message.text
        timezone_name = selected.split()[0]  # Extract city name
        
        timezones = get_timezone_list()
        if timezone_name in timezones:
            user_id = update.effective_user.id
            username = update.effective_user.username
            timezone = timezones[timezone_name]
            
            # Save user to database
            if self.db.add_user(user_id, username, timezone):
                await update.message.reply_text(
                    f"✅ Часовий пояс встановлено: {timezone_name}\n\n"
                    "Тепер ви можете користуватися ботом!"
                )
                await self.show_main_menu(update, context)
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "❌ Помилка збереження. Спробуйте ще раз."
                )
                return SELECTING_TIMEZONE
        else:
            await update.message.reply_text(
                "❌ Неправильний вибір. Оберіть зі списку."
            )
            return SELECTING_TIMEZONE
    
    async def handle_change_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle timezone change request"""
        if not await check_user_access(update, context):
            return ConversationHandler.END
        
        # Get current user timezone
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ Помилка: користувач не знайдений")
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        current_tz = user['timezone']
        # Find city name for current timezone
        timezones = get_timezone_list()
        current_city = None
        for city, tz in timezones.items():
            if tz == current_tz:
                current_city = city
                break
        
        # Show timezone selection
        timezone_labels = {
            "Відень": "Відень UTC+1/+2",
            "Київ": "Київ UTC+2/+3", 
            "Харків": "Харків UTC+2/+3",
            "Сіетл": "Сіетл UTC-8/-7",
            "Старобільськ": "Старобільськ UTC+3"
        }
        
        keyboard = []
        for city_name, tz_name in timezones.items():
            label = timezone_labels.get(city_name, city_name)
            if tz_name == current_tz:
                keyboard.append([KeyboardButton(f"✅ {label} (поточний)")])
            else:
                keyboard.append([KeyboardButton(label)])
        
        keyboard.append([KeyboardButton("❌ Скасувати")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            f"🌍 Зміна часового поясу\n\n"
            f"Поточний: {current_city or 'Невідомо'}\n\n"
            "Оберіть новий часовий пояс:",
            reply_markup=reply_markup
        )
        return CHANGING_TIMEZONE
    
    async def handle_timezone_change_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new timezone selection"""
        if update.message.text == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        selected = update.message.text
        # Remove checkmark and "(поточний)" if present
        selected = selected.replace("✅ ", "").replace(" (поточний)", "")
        timezone_name = selected.split()[0]  # Extract city name
        
        timezones = get_timezone_list()
        if timezone_name in timezones:
            user_id = update.effective_user.id
            username = update.effective_user.username
            new_timezone = timezones[timezone_name]
            
            # Update user timezone in database
            if self.db.add_user(user_id, username, new_timezone):
                await update.message.reply_text(
                    f"✅ Часовий пояс змінено на: {timezone_name}\n\n"
                    "Всі ваші нагадування тепер будуть надходити за новим часом."
                )
                await self.show_main_menu(update, context)
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "❌ Помилка збереження. Спробуйте ще раз."
                )
                return CHANGING_TIMEZONE
        else:
            await update.message.reply_text(
                "❌ Неправильний вибір. Оберіть зі списку."
            )
            return CHANGING_TIMEZONE
    
    async def handle_delete_medicine(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle medicine deletion request"""
        if not await check_user_access(update, context):
            return ConversationHandler.END
        
        user_id = update.effective_user.id
        medicines = self.db.get_user_medicines(user_id)
        
        if not medicines:
            await update.message.reply_text(
                "❌ У вас немає збережених ліків для видалення."
            )
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        # Create medicine list for selection
        keyboard = []
        for i, medicine in enumerate(medicines, 1):
            reminder_count = len([r for r in medicine['reminders'] if r['active']])
            keyboard.append([KeyboardButton(f"{i}. {medicine['name']} ({reminder_count} нагадувань)")])
        
        keyboard.append([KeyboardButton("❌ Скасувати")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        # Store medicines in context for later use
        context.user_data['medicines_for_deletion'] = medicines
        
        await update.message.reply_text(
            "🗑️ Видалення ліків\n\n"
            "Оберіть ліки, які хочете видалити:",
            reply_markup=reply_markup
        )
        return DELETING_MEDICINE_SELECT
    
    async def handle_medicine_selection_for_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle medicine selection for deletion"""
        if update.message.text == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        try:
            # Parse selection (e.g., "1. Aspirin (2 нагадувань)")
            selection_text = update.message.text
            medicine_index = int(selection_text.split('.')[0]) - 1
            
            medicines = context.user_data.get('medicines_for_deletion', [])
            if 0 <= medicine_index < len(medicines):
                selected_medicine = medicines[medicine_index]
                context.user_data['selected_medicine'] = selected_medicine
                
                active_reminders = [r for r in selected_medicine['reminders'] if r['active']]
                
                if len(active_reminders) <= 1:
                    # Only one or no reminders - delete entire medicine
                    context.user_data['deletion_type'] = 'medicine'
                    
                    await update.message.reply_text(
                        f"🗑️ Підтвердження видалення\n\n"
                        f"Ви хочете видалити ліки:\n"
                        f"💊 {selected_medicine['name']}\n\n"
                        f"Це видалить всі нагадування для цих ліків.\n\n"
                        f"Підтвердити видалення?",
                        reply_markup=ReplyKeyboardMarkup([
                            [KeyboardButton("✅ Так, видалити"), KeyboardButton("❌ Скасувати")]
                        ], resize_keyboard=True, one_time_keyboard=True)
                    )
                    return CONFIRMING_DELETION
                else:
                    # Multiple reminders - ask what to delete
                    keyboard = []
                    
                    # Option to delete entire medicine
                    keyboard.append([KeyboardButton(f"🗑️ Видалити всі ліки '{selected_medicine['name']}'")])
                    
                    # Options to delete individual reminders
                    for reminder in active_reminders:
                        keyboard.append([KeyboardButton(
                            f"🕐 Видалити нагадування {reminder['time']} - {reminder['dosage']}"
                        )])
                    
                    keyboard.append([KeyboardButton("❌ Скасувати")])
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                    
                    await update.message.reply_text(
                        f"🗑️ Що видалити?\n\n"
                        f"💊 {selected_medicine['name']} має {len(active_reminders)} нагадувань:\n\n" +
                        "\n".join([f"🕐 {r['time']} - {r['dosage']}" for r in active_reminders]) + "\n\n"
                        "Оберіть що видалити:",
                        reply_markup=reply_markup
                    )
                    return DELETING_REMINDER_SELECT
            else:
                await update.message.reply_text("❌ Неправильний вибір. Оберіть зі списку.")
                return DELETING_MEDICINE_SELECT
                
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Неправильний формат. Оберіть зі списку.")
            return DELETING_MEDICINE_SELECT
    
    async def handle_reminder_selection_for_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reminder selection for deletion"""
        if update.message.text == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        selected_medicine = context.user_data.get('selected_medicine')
        if not selected_medicine:
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        selection_text = update.message.text
        
        if selection_text.startswith("🗑️ Видалити всі ліки"):
            # Delete entire medicine
            context.user_data['deletion_type'] = 'medicine'
            
            await update.message.reply_text(
                f"🗑️ Підтвердження видалення\n\n"
                f"Ви хочете видалити ВСІ ліки:\n"
                f"💊 {selected_medicine['name']}\n\n"
                f"Це видалить всі нагадування для цих ліків.\n\n"
                f"Підтвердити видалення?",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("✅ Так, видалити"), KeyboardButton("❌ Скасувати")]
                ], resize_keyboard=True, one_time_keyboard=True)
            )
            return CONFIRMING_DELETION
        
        elif selection_text.startswith("🕐 Видалити нагадування"):
            # Delete specific reminder
            try:
                # Parse time from "🕐 Видалити нагадування 08:00 - 1 таблетка"
                time_part = selection_text.split("🕐 Видалити нагадування ")[1]
                reminder_time = time_part.split(" - ")[0]
                
                # Find the reminder with this time
                selected_reminder = None
                for reminder in selected_medicine['reminders']:
                    if reminder['time'] == reminder_time and reminder['active']:
                        selected_reminder = reminder
                        break
                
                if selected_reminder:
                    context.user_data['deletion_type'] = 'reminder'
                    context.user_data['selected_reminder'] = selected_reminder
                    
                    await update.message.reply_text(
                        f"🗑️ Підтвердження видалення\n\n"
                        f"Ви хочете видалити нагадування:\n"
                        f"💊 {selected_medicine['name']}\n"
                        f"🕐 {selected_reminder['time']} - {selected_reminder['dosage']}\n\n"
                        f"Підтвердити видалення?",
                        reply_markup=ReplyKeyboardMarkup([
                            [KeyboardButton("✅ Так, видалити"), KeyboardButton("❌ Скасувати")]
                        ], resize_keyboard=True, one_time_keyboard=True)
                    )
                    return CONFIRMING_DELETION
                else:
                    await update.message.reply_text("❌ Нагадування не знайдено.")
                    return DELETING_REMINDER_SELECT
                    
            except (IndexError, ValueError):
                await update.message.reply_text("❌ Неправильний формат. Оберіть зі списку.")
                return DELETING_REMINDER_SELECT
        
        else:
            await update.message.reply_text("❌ Неправильний вибір. Оберіть зі списку.")
            return DELETING_REMINDER_SELECT
    
    async def handle_deletion_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deletion confirmation"""
        if update.message.text == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        if update.message.text != "✅ Так, видалити":
            await update.message.reply_text("❌ Неправильний вибір. Оберіть зі списку.")
            return CONFIRMING_DELETION
        
        user_id = update.effective_user.id
        deletion_type = context.user_data.get('deletion_type')
        selected_medicine = context.user_data.get('selected_medicine')
        
        if deletion_type == 'medicine' and selected_medicine:
            # Delete entire medicine
            success = self.db.delete_medicine(selected_medicine['id'], user_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ Ліки '{selected_medicine['name']}' успішно видалено!\n"
                    f"Всі нагадування для цих ліків також видалено."
                )
            else:
                await update.message.reply_text("❌ Помилка при видаленні ліків.")
        
        elif deletion_type == 'reminder':
            # Delete specific reminder
            selected_reminder = context.user_data.get('selected_reminder')
            if selected_reminder:
                success = self.db.delete_reminder(selected_reminder['id'], user_id)
                
                if success:
                    await update.message.reply_text(
                        f"✅ Нагадування видалено!\n"
                        f"💊 {selected_medicine['name']}\n"
                        f"🕐 {selected_reminder['time']} - {selected_reminder['dosage']}"
                    )
                else:
                    await update.message.reply_text("❌ Помилка при видаленні нагадування.")
            else:
                await update.message.reply_text("❌ Нагадування не знайдено.")
        
        else:
            await update.message.reply_text("❌ Помилка обробки запиту.")
        
        # Clear context and return to main menu
        context.user_data.clear()
        await self.show_main_menu(update, context)
        return ConversationHandler.END
    
    async def handle_delete_all_medicines(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete all medicines request"""
        if not await check_user_access(update, context):
            return ConversationHandler.END
        
        user_id = update.effective_user.id
        medicines = self.db.get_user_medicines(user_id)
        
        if not medicines:
            await update.message.reply_text(
                "❌ У вас немає збережених ліків для видалення."
            )
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        total_medicines = len(medicines)
        total_reminders = sum(len([r for r in medicine['reminders'] if r['active']]) for medicine in medicines)
        
        await update.message.reply_text(
            f"⚠️ УВАГА! НЕБЕЗПЕЧНА ДІЯ!\n\n"
            f"Ви збираєтеся ВИДАЛИТИ ВСІ ваші ліки:\n"
            f"📊 Всього ліків: {total_medicines}\n"
            f"📊 Всього нагадувань: {total_reminders}\n\n"
            f"⚠️ ЦЕ ДІЯ НЕЗВОРОТНА!\n"
            f"Всі ваші ліки та нагадування будуть ПОВНІСТЮ ВИДАЛЕНІ!\n\n"
            f"Ви ВПЕВНЕНІ, що хочете продовжити?",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("⚠️ ТАК, видалити ВСЕ"), KeyboardButton("❌ НІ, скасувати")]
            ], resize_keyboard=True, one_time_keyboard=True)
        )
        return CONFIRMING_DELETE_ALL
    
    async def handle_delete_all_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete all confirmation with double confirmation"""
        # Check if we're in final confirmation stage
        if context.user_data.get('final_delete_all_confirmation'):
            # Final confirmation stage
            if update.message.text == "❌ НІ, не видаляти":
                await update.message.reply_text("✅ Скасовано. Ваші ліки в безпеці!")
                context.user_data.clear()
                await self.show_main_menu(update, context)
                return ConversationHandler.END
            
            if update.message.text != "🚨 ПІДТВЕРДЖУЮ ВИДАЛЕННЯ":
                await update.message.reply_text("❌ Неправильний вибір. Оберіть зі списку.")
                return CONFIRMING_DELETE_ALL
            
            # Actually delete all medicines
            user_id = update.effective_user.id
            deleted_count = self.db.delete_all_user_medicines(user_id)
            
            if deleted_count > 0:
                await update.message.reply_text(
                    f"✅ ВИДАЛЕННЯ ЗАВЕРШЕНО!\n\n"
                    f"🗑️ Видалено {deleted_count} ліків\n"
                    f"🗑️ Видалено всі пов'язані нагадування\n\n"
                    f"Ваш список ліків тепер пустий."
                )
            else:
                await update.message.reply_text("❌ Помилка при видаленні ліків.")
            
            context.user_data.clear()
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        else:
            # First confirmation stage
            if update.message.text == "❌ НІ, скасувати":
                await update.message.reply_text("✅ Скасовано. Ваші ліки залишилися на місці.")
                await self.show_main_menu(update, context)
                return ConversationHandler.END
            
            if update.message.text != "⚠️ ТАК, видалити ВСЕ":
                await update.message.reply_text("❌ Неправильний вибір. Оберіть зі списку.")
                return CONFIRMING_DELETE_ALL
            
            # SECOND CONFIRMATION - Double safety
            user_id = update.effective_user.id
            medicines = self.db.get_user_medicines(user_id)
            total_medicines = len(medicines)
            
            await update.message.reply_text(
                f"🚨 ОСТАННЯ ПЕРЕВІРКА!\n\n"
                f"Ви точно хочете видалити ВСІ {total_medicines} ліків?\n\n"
                f"⚠️ ПІСЛЯ НАТИСКАННЯ 'ПІДТВЕРДЖУЮ' \n"
                f"ВСІ ВАШІ ЛІКИ БУДУТЬ ВИДАЛЕНІ НАЗАВЖДИ!\n\n"
                f"Це ваш останній шанс передумати!",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("🚨 ПІДТВЕРДЖУЮ ВИДАЛЕННЯ")],
                    [KeyboardButton("❌ НІ, не видаляти")]
                ], resize_keyboard=True, one_time_keyboard=True)
            )
            
            # Store that we're in final confirmation
            context.user_data['final_delete_all_confirmation'] = True
            return CONFIRMING_DELETE_ALL
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        keyboard = [
            [KeyboardButton("➕ Додати ліки")],
            [KeyboardButton("📋 Мої ліки")],
            [KeyboardButton("🗑️ Видалити ліки")],
            [KeyboardButton("🌍 Змінити часовий пояс")],
            [KeyboardButton("❓ Допомога")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🏠 Головне меню\n\n"
            "Оберіть дію:",
            reply_markup=reply_markup
        )
    
    async def handle_add_medicine(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding medicine process"""
        if not await check_user_access(update, context):
            return ConversationHandler.END
        
        # Clear any previous medicine data
        context.user_data.clear()
        
        keyboard = [[KeyboardButton("❌ Скасувати")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "💊 Додавання ліків\n\n"
            "Введіть назву ліків:",
            reply_markup=reply_markup
        )
        return ADDING_MEDICINE_NAME
    
    async def handle_medicine_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle medicine name input"""
        if update.message.text == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        medicine_name = update.message.text.strip()
        if not medicine_name or len(medicine_name) > 100:
            await update.message.reply_text(
                "❌ Неправильна назва ліків. Спробуйте ще раз.\n"
                "Назва повинна містити від 1 до 100 символів."
            )
            return ADDING_MEDICINE_NAME
        
        # Store medicine name in context
        context.user_data['medicine_name'] = medicine_name
        
        # Show time input options
        keyboard = [
            [KeyboardButton("Ранок 08:00"), KeyboardButton("День 14:00"), KeyboardButton("Вечір 20:00")],
            [KeyboardButton("❌ Скасувати")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"💊 {medicine_name}\n\n"
            "Введіть час у форматі ГГ:ХХ\n"
            "Приклади: 08:00, 14:30, 20:15\n\n"
            "Або оберіть готовий варіант:",
            reply_markup=reply_markup
        )
        return ADDING_MEDICINE_TIME
    
    async def handle_medicine_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle medicine time input"""
        if update.message.text == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        time_input = update.message.text
        
        # Handle preset times
        if time_input == "Ранок 08:00":
            time_str = "08:00"
        elif time_input == "День 14:00":
            time_str = "14:00"
        elif time_input == "Вечір 20:00":
            time_str = "20:00"
        else:
            time_str = validate_time_format(time_input)
        
        if not time_str:
            await update.message.reply_text(
                "❌ Неправильний формат часу. Спробуйте ще раз.\n"
                "Приклад: 08:00"
            )
            return ADDING_MEDICINE_TIME
        
        # Store time in context
        context.user_data['medicine_time'] = time_str
        
        keyboard = [[KeyboardButton("❌ Скасувати")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"💊 {context.user_data['medicine_name']}\n"
            f"🕐 {time_str}\n\n"
            "Введіть дозу (приклад: 1 таблетка):",
            reply_markup=reply_markup
        )
        return ADDING_MEDICINE_DOSAGE
    
    async def handle_medicine_dosage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle medicine dosage input"""
        if update.message.text == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        
        dosage = validate_dosage(update.message.text)
        
        if not dosage:
            await update.message.reply_text(
                "❌ Неправильний формат дози. Спробуйте ще раз.\n"
                "Приклад: 1 таблетка, 2 капсули, 5 мл"
            )
            return ADDING_MEDICINE_DOSAGE
        
        # Store dosage in context
        context.user_data['medicine_dosage'] = dosage
        
        # Show confirmation
        keyboard = [
            [KeyboardButton("✅ Зберегти")],
            [KeyboardButton("✏️ Змінити"), KeyboardButton("❌ Скасувати")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Підтвердіть додавання:\n\n"
            f"💊 {context.user_data['medicine_name']}\n"
            f"🕐 {context.user_data['medicine_time']}\n"
            f"💊 {dosage}",
            reply_markup=reply_markup
        )
        return CONFIRMING_MEDICINE
    
    async def handle_medicine_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle medicine confirmation"""
        choice = update.message.text
        
        if choice == "❌ Скасувати":
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        elif choice == "✏️ Змінити":
            # Go back to name input
            keyboard = [[KeyboardButton("❌ Скасувати")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "💊 Додавання ліків\n\n"
                "Введіть назву ліків:",
                reply_markup=reply_markup
            )
            return ADDING_MEDICINE_NAME
        elif choice == "✅ Зберегти":
            # Save to database
            user_id = update.effective_user.id
            
            # Check if we already have a medicine_id (adding more times)
            if 'medicine_id' not in context.user_data:
                # First time - create new medicine
                medicine_id = self.db.add_medicine(
                    user_id, 
                    context.user_data['medicine_name']
                )
                context.user_data['medicine_id'] = medicine_id
            else:
                # Adding more times - reuse existing medicine
                medicine_id = context.user_data['medicine_id']
            
            if medicine_id:
                success = self.db.add_reminder(
                    medicine_id,
                    context.user_data['medicine_time'],
                    context.user_data['medicine_dosage']
                )
                
                if success:
                    keyboard = [
                        [KeyboardButton("Так"), KeyboardButton("Ні")],
                        [KeyboardButton("🏠 Головне меню")]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    await update.message.reply_text(
                        "✅ Ліки успішно додано!\n\n"
                        "Додати ще один час для цих ліків?",
                        reply_markup=reply_markup
                    )
                    return ADDING_MORE_TIMES
                else:
                    await update.message.reply_text("❌ Помилка збереження. Спробуйте ще раз.")
                    await self.show_main_menu(update, context)
                    return ConversationHandler.END
            else:
                await update.message.reply_text("❌ Помилка збереження. Спробуйте ще раз.")
                await self.show_main_menu(update, context)
                return ConversationHandler.END
    
    async def handle_adding_more_times(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding more reminder times"""
        choice = update.message.text
        
        if choice == "🏠 Головне меню" or choice == "Ні":
            # Clear context when finishing
            context.user_data.clear()
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        elif choice == "Так":
            # Continue with same medicine, add another time
            keyboard = [
                [KeyboardButton("Ранок 08:00"), KeyboardButton("День 14:00"), KeyboardButton("Вечір 20:00")],
                [KeyboardButton("❌ Скасувати")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"💊 {context.user_data['medicine_name']}\n\n"
                "Введіть ще один час:",
                reply_markup=reply_markup
            )
            return ADDING_MEDICINE_TIME
        else:
            # Clear context when finishing
            context.user_data.clear()
            await self.show_main_menu(update, context)
            return ConversationHandler.END
    
    async def handle_show_medicines(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's medicines"""
        if not await check_user_access(update, context):
            return
        
        user_id = update.effective_user.id
        medicines = self.db.get_user_medicines(user_id)
        
        message = format_medicine_list(medicines)
        
        # Create keyboard based on whether user has medicines
        if medicines:
            keyboard = [
                [KeyboardButton("➕ Додати ще")],
                [KeyboardButton("🗑️ Видалити обрані ліки")],
                [KeyboardButton("⚠️ Видалити ВСІ ліки")],
                [KeyboardButton("🏠 Головне меню")]
            ]
        else:
            keyboard = [
                [KeyboardButton("➕ Додати ще")],
                [KeyboardButton("🏠 Головне меню")]
            ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = (
            "❓ Довідка по Медичному Помічнику\n\n"
            "📋 ОСНОВНІ ФУНКЦІЇ:\n\n"
            
            "➕ ДОДАТИ ЛІКИ\n"
            "• Додає нові ліки з нагадуваннями\n"
            "• Можна додати кілька часів для одних ліків\n"
            "• Підтримує гнучкі формати часу\n\n"
            
            "📋 МОЇ ЛІКИ\n"
            "• Показує всі збережені ліки\n"
            "• Групує нагадування по лікам\n"
            "• Сортує за часом\n\n"
            
            "🗑️ ВИДАЛИТИ ЛІКИ\n"
            "• Видалення окремих нагадувань\n"
            "• Видалення цілих ліків\n"
            "• Видалення ВСІХ ліків (подвійне підтвердження)\n\n"
            
            "🌍 ЗМІНИТИ ЧАСОВИЙ ПОЯС\n"
            "• Відень (UTC+1/+2) - Австрія\n"
            "• Київ, Харків (UTC+2/+3) - Україна\n"
            "• Сіетл (UTC-8/-7) - США, захід\n"
            "• Старобільськ (UTC+3) - окупована територія\n"
            "• Нагадування адаптуються автоматично\n\n"
            
            "⏰ ФОРМАТИ ЧАСУ:\n"
            "• 8 → 08:00\n"
            "• 830 → 08:30\n"
            "• 1245 → 12:45\n"
            "• 08:00, 14:30, 20:15\n\n"
            
            "💊 ФОРМАТИ ДОЗИ:\n"
            "• 1 таблетка, 2 капсули\n"
            "• 5 мл, пів таблетки\n"
            "• 1/2 таблетки\n\n"
            
            "🔐 БЕЗПЕКА:\n"
            "• Тільки авторизовані користувачі\n"
            "• Підтвердження для видалення\n"
            "• Автоматичні резервні копії\n\n"
            
            "💊 Нагадування надходять автоматично у вказаний час відповідно до вашого часового поясу!"
        )
        
        keyboard = [[KeyboardButton("🏠 Головне меню")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(help_text, reply_markup=reply_markup)
    
    async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle conversation cancellation"""
        await self.show_main_menu(update, context)
        return ConversationHandler.END
    
    async def handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown messages"""
        if not await check_user_access(update, context):
            return
        
        # Check for main menu buttons
        text = update.message.text
        
        if text == "➕ Додати ліки" or text == "➕ Додати ще":
            # This should be handled by ConversationHandler, but just in case
            return await self.handle_add_medicine(update, context)
        elif text == "📋 Мої ліки":
            await self.handle_show_medicines(update, context)
        elif text == "🗑️ Видалити ліки" or text == "🗑️ Видалити обрані ліки":
            return await self.handle_delete_medicine(update, context)
        elif text == "⚠️ Видалити ВСІ ліки":
            return await self.handle_delete_all_medicines(update, context)
        elif text == "🌍 Змінити часовий пояс":
            return await self.handle_change_timezone(update, context)
        elif text == "❓ Допомога":
            await self.handle_help(update, context)
        elif text == "🏠 Головне меню":
            await self.show_main_menu(update, context)
        else:
            await update.message.reply_text(
                "❌ Не розумію команду. Оберіть дію з меню."
            )
            await self.show_main_menu(update, context)
    
    def run(self):
        """Run the bot"""
        self.logger.info("Starting Medicine Reminder Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function"""
    bot = MedicineBot()
    bot.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)