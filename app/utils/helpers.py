import re
import logging
from typing import Optional, List
import pytz
from datetime import datetime
import json
import os

def load_config(config_path: str = "config/settings.json") -> dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {}

def load_bot_token(token_path: str = "config/bot_token.txt") -> Optional[str]:
    try:
        with open(token_path, 'r', encoding='utf-8') as f:
            token = f.read().strip()
            return token if token and not token.startswith('#') else None
    except Exception as e:
        logging.error(f"Error loading bot token: {e}")
        return None

def load_allowed_users(users_path: str = "config/allowed_users.txt") -> dict:
    """
    Load allowed users from file. Returns dict with user_ids and usernames.
    Format: {"user_ids": [123, 456], "usernames": ["user1", "user2"]}
    """
    try:
        with open(users_path, 'r', encoding='utf-8') as f:
            user_ids = []
            usernames = []
            
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Try to parse as user ID (numeric)
                    try:
                        user_id = int(line)
                        user_ids.append(user_id)
                    except ValueError:
                        # If not numeric, treat as username
                        if line.startswith('@'):
                            username = line[1:]  # Remove @ prefix
                        else:
                            username = line
                        
                        # Validate username format (Telegram usernames are 5-32 chars, alphanumeric + underscore)
                        if 5 <= len(username) <= 32 and username.replace('_', '').isalnum():
                            usernames.append(username.lower())
                        else:
                            logging.warning(f"Invalid username format on line {line_num}: {line}")
            
            return {"user_ids": user_ids, "usernames": usernames}
    except Exception as e:
        logging.error(f"Error loading allowed users: {e}")
        return {"user_ids": [], "usernames": []}

def load_allowed_users_legacy(users_path: str = "config/allowed_users.txt") -> List[int]:
    """Legacy function for backward compatibility - returns only user IDs"""
    allowed = load_allowed_users(users_path)
    return allowed["user_ids"]

def validate_time_format(time_str: str) -> Optional[str]:
    """
    Validate and normalize time format to HH:MM (24h)
    Accepts: "8", "08", "8:00", "08:00", "8:30", "08:30", "830", "1245", "800"
    """
    time_str = time_str.strip()
    
    # Try different patterns
    
    # Pattern 1: HH:MM or H:MM (with colon)
    match = re.match(r'^([0-9]|[01][0-9]|2[0-3]):([0-5][0-9])$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # Pattern 2: Just hour (e.g., "8", "08", "14")
    match = re.match(r'^([0-9]|[01][0-9]|2[0-3])$', time_str)
    if match:
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"
    
    # Pattern 3: HHMM format (e.g., "830" -> "8:30", "1245" -> "12:45", "800" -> "8:00")
    match = re.match(r'^([0-9]{3,4})$', time_str)
    if match:
        time_digits = match.group(1)
        
        if len(time_digits) == 3:  # e.g., "830"
            hour = int(time_digits[0])
            minute = int(time_digits[1:3])
        elif len(time_digits) == 4:  # e.g., "1245"
            hour = int(time_digits[0:2])
            minute = int(time_digits[2:4])
        else:
            return None
        
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # Pattern 4: HMM format (e.g., "800" -> "8:00" when entered as 3 digits starting with single digit hour)
    match = re.match(r'^([0-9])([0-9]{2})$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    return None

def validate_dosage(dosage_str: str) -> Optional[str]:
    """
    Validate and normalize dosage format
    """
    dosage_str = dosage_str.strip()
    
    if not dosage_str:
        return None
    
    # Common dosage patterns
    valid_patterns = [
        r'^\d+(\.\d+)?\s*(таблетк[аи]|таб\.?|капсул[аи]|кап\.?|краплі?|мл\.?|г\.?)$',
        r'^пів\s*(таблетк[аи]|капсул[аи])$',
        r'^\d+/\d+\s*(таблетк[аи]|капсул[аи])$'
    ]
    
    for pattern in valid_patterns:
        if re.match(pattern, dosage_str, re.IGNORECASE):
            return dosage_str
    
    # If no pattern matches but it's not empty, allow but log warning
    if len(dosage_str) <= 50:  # reasonable length limit
        logging.warning(f"Unusual dosage format: {dosage_str}")
        return dosage_str
    
    return None

def get_timezone_list() -> dict:
    """Load available timezones from config"""
    try:
        with open("config/timezones.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading timezones: {e}")
        return {"Київ": "Europe/Kiev"}

def format_time_for_display(time_str: str) -> str:
    """Format time for user display"""
    return time_str

def format_medicine_list(medicines: List[dict]) -> str:
    """Format medicines list for display"""
    if not medicines:
        return "📋 У вас ще немає збережених ліків."
    
    result = "📋 Ваші ліки:\n\n"
    for i, medicine in enumerate(medicines, 1):
        result += f"{i}. 💊 {medicine['name']}\n"
        
        if medicine['reminders']:
            # Sort reminders by time for better display
            active_reminders = [r for r in medicine['reminders'] if r['active']]
            active_reminders.sort(key=lambda x: x['time'])
            
            if active_reminders:
                for reminder in active_reminders:
                    result += f"   🕐 {reminder['time']} - {reminder['dosage']}\n"
            else:
                result += "   (немає активних нагадувань)\n"
        else:
            result += "   (немає нагадувань)\n"
        
        result += "\n"
    
    return result

def format_reminder_message(medicine_name: str, dosage: str, time: str) -> str:
    """Format reminder message for users"""
    return f"💊 {time} - Час прийняти {medicine_name} ({dosage})"

def setup_logging(log_path: str = "logs/bot.log", level: str = "INFO"):
    """Setup logging configuration"""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )