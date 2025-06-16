from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging
from database import Database
from handlers.auth import check_user_access
from utils.helpers import get_timezone_list, format_medicine_list

# Conversation states
(SELECTING_TIMEZONE, ADDING_MEDICINE_NAME, ADDING_MEDICINE_TIME, 
 ADDING_MEDICINE_DOSAGE, CONFIRMING_MEDICINE, ADDING_MORE_TIMES,
 EDITING_MEDICINE_SELECT, EDITING_MEDICINE_ACTION) = range(8)

class BotHandlers:
    def __init__(self, database: Database):
        self.db = database
    
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
        
        for city_name in timezones.keys():
            keyboard.append([KeyboardButton(f"{city_name} UTC+2")])
        
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
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        keyboard = [
            [KeyboardButton("➕ Додати ліки")],
            [KeyboardButton("📋 Мої ліки")],
            [KeyboardButton("✏️ Змінити ліки")],
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
            from utils.helpers import validate_time_format
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
        
        from utils.helpers import validate_dosage
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
            medicine_id = self.db.add_medicine(
                user_id, 
                context.user_data['medicine_name']
            )
            
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
            await self.show_main_menu(update, context)
            return ConversationHandler.END
    
    async def handle_show_medicines(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's medicines"""
        if not await check_user_access(update, context):
            return
        
        user_id = update.effective_user.id
        medicines = self.db.get_user_medicines(user_id)
        
        message = format_medicine_list(medicines)
        
        keyboard = [
            [KeyboardButton("✏️ Змінити"), KeyboardButton("➕ Додати ще")],
            [KeyboardButton("🏠 Головне меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = (
            "❓ Допомога\n\n"
            "🔹 Додати ліки - додає нові ліки з нагадуваннями\n"
            "🔹 Мої ліки - показує всі збережені ліки\n"
            "🔹 Змінити ліки - дозволяє редагувати або видаляти ліки\n\n"
            "📋 Формати вводу:\n"
            "• Час: 08:00, 14:30, 20:15\n"
            "• Доза: 1 таблетка, 2 капсули, 5 мл\n\n"
            "💊 Нагадування надходять автоматично у вказаний час."
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
        
        if text == "➕ Додати ліки":
            return await self.handle_add_medicine(update, context)
        elif text == "📋 Мої ліки":
            await self.handle_show_medicines(update, context)
        elif text == "✏️ Змінити ліки":
            # TODO: Implement medicine editing
            await update.message.reply_text("⚠️ Функція в розробці")
            await self.show_main_menu(update, context)
        elif text == "❓ Допомога":
            await self.handle_help(update, context)
        elif text == "🏠 Головне меню":
            await self.show_main_menu(update, context)
        else:
            await update.message.reply_text(
                "❌ Не розумію команду. Оберіть дію з меню."
            )
            await self.show_main_menu(update, context)