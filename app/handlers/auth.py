from telegram import Update
from telegram.ext import ContextTypes
import logging
from utils.helpers import load_allowed_users

async def check_user_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is authorized to use the bot"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    allowed = load_allowed_users()
    allowed_user_ids = allowed["user_ids"]
    allowed_usernames = allowed["usernames"]
    
    # Check by user ID first
    if user_id in allowed_user_ids:
        return True
    
    # Check by username if user has one
    if username and username.lower() in allowed_usernames:
        logging.info(f"User @{username} (ID: {user_id}) authorized by username")
        return True
    
    # Access denied
    user_info = f"@{username}" if username else f"ID: {user_id}"
    await update.message.reply_text(
        "❌ Вибачте, доступ заборонено.\n"
        "Зверніться до адміністратора для отримання доступу."
    )
    logging.warning(f"Unauthorized access attempt from user {user_info} (ID: {user_id})")
    return False