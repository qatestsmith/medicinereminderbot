# Medication Reminder Bot - Final Requirements Document
## Ukrainian Interface | Raspberry Pi 5 | Docker | Elderly-Focused

---

## 1. Project Overview

**Product Vision:** A simple, reliable Telegram bot for elderly users to receive medication reminders with proper dosage information.

**Mission Statement:** "Правильне лікування – довше життя" (Correct treatment – longer life)

**Target Problem:** Elderly people forget to take medications on time, leading to health complications and treatment inefficiency.

---

## 2. Target Audience & Scale

**Primary Users:** Elderly people (65+ years) managing daily medications  
**User Count:** Maximum 20 concurrent users  
**Tech Level:** Basic Telegram users, prefer simple interfaces  
**Access Method:** Admin-controlled approval via pre-configured user list  

---

## 3. Core Functionality (MVP)

### Essential Features:
✅ **Ukrainian button-based interface** (large, clear buttons)  
✅ **Medicine management** (add, edit, delete)  
✅ **Multiple daily reminders** per medicine with individual dosages  
✅ **24-hour time format** for all time inputs and displays  
✅ **Automatic reminder delivery** (basic sending, no acknowledgment)  
✅ **Admin-controlled user access** via text file  
✅ **Timezone selection** during user onboarding  

### User Interface Flow:

#### Main Menu:
```
🏠 Головне меню

[➕ Додати ліки]
[📋 Мої ліки] 
[✏️ Змінити ліки]
[❓ Допомога]
```

#### Add Medicine Flow:
```
Step 1: "Введіть назву ліків:"
Step 2: "Введіть час у форматі ГГ:ХХ
         Приклади: 08:00, 14:30, 20:15
         [Ранок 08:00] [День 14:00] [Вечір 20:00]"
Step 3: "Введіть дозу (приклад: 1 таблетка):"
Step 4: "Підтвердіть додавання:
         💊 [Medicine Name]
         🕐 [Time]
         💊 [Dosage]
         [✅ Зберегти] [✏️ Змінити] [❌ Скасувати]"
Step 5: "Додати ще один час? [Так]/[Ні]/[Головне меню]"
```

#### Medicine List Display:
```
📋 Ваші ліки:

1. 💊 Аспірин
   🕐 08:00 - 1 таблетка
   🕐 20:00 - 2 таблетки

2. 💊 Вітаміни  
   🕐 09:00 - 1 капсула

[✏️ Змінити] [➕ Додати ще]
```

#### Reminder Message Format:
```
💊 08:00 - Час прийняти Аспірин (1 таблетка)
```

---

## 4. Technical Architecture

### Platform & Deployment:
- **Hardware:** Raspberry Pi 5 (4GB+ RAM recommended)
- **Operating System:** Raspberry Pi OS
- **Containerization:** Docker with docker-compose
- **Language:** Python 3.11+
- **Framework:** python-telegram-bot library

### Database Design (SQLite):
```sql
-- Users table
users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    timezone TEXT,
    created_at TIMESTAMP
)

-- Medicines table  
medicines (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    name TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
)

-- Reminders table
reminders (
    id INTEGER PRIMARY KEY,
    medicine_id INTEGER,
    time TEXT,  -- Format: "08:00"
    dosage TEXT, -- Format: "1 таблетка"
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP,
    FOREIGN KEY (medicine_id) REFERENCES medicines (id)
)

-- Reminder logs table (for tracking)
reminder_logs (
    id INTEGER PRIMARY KEY,
    reminder_id INTEGER,
    sent_at TIMESTAMP,
    FOREIGN KEY (reminder_id) REFERENCES reminders (id)
)
```

### File Structure:
```
/app/
├── bot.py                 # Main bot application
├── database.py            # Database operations
├── handlers/              # Telegram handlers
├── utils/                 # Helper functions
├── config/
│   ├── bot_token.txt     # Bot token (gitignored)
│   ├── allowed_users.txt # Approved telegram IDs (gitignored)
│   ├── timezones.json    # Available timezone options
│   └── settings.json     # Bot configuration
├── data/
│   └── database.db       # SQLite database (gitignored)
├── logs/
│   └── bot.log           # Application logs (gitignored)
├── backups/              # Manual backups (gitignored)
├── requirements.txt      # Python dependencies
├── Dockerfile
├── docker-compose.yml
└── backup.py             # Manual backup utility
```

---

## 5. User Experience Specifications

### Error Handling (Elderly-Friendly):
- **Simple error messages:** "❌ Неправильний формат. Спробуйте ще раз."
- **Clear examples:** Always provide correct format examples
- **Easy recovery:** [Скасувати] button available at every step
- **Input validation:** Accept flexible formats but convert to standard

### Input Validation Examples:
```python
# Time formats (all convert to 24h)
"08:00" ✅ → "08:00"
"8:00" ✅ → "08:00"  
"8" ✅ → "08:00"
"25:00" ❌ → "Неправильний час. Приклад: 08:00"

# Dosage formats
"1 таблетка" ✅
"2 таб" ✅  
"0.5 таблетки" ✅
"пів таблетки" ✅
```

### User Onboarding Process:
1. User starts bot → Check telegram_id in allowed_users.txt
2. If not approved → "Вибачте, доступ заборонено"
3. If approved but new → "Ласкаво просимо! Оберіть часовий пояс:"
   ```
   [Київ UTC+2] [Львів UTC+2] [Одеса UTC+2] 
   [Дніпро UTC+2] [Харків UTC+2]
   ```
4. Save user preferences → Show main menu
5. Existing users → Go directly to main menu

---

## 6. Administrative Features

### User Management:
- **Access Control:** Simple text file with approved telegram IDs
- **File Location:** `/app/config/allowed_users.txt`
- **Format:** One telegram ID per line
- **Updates:** Bot reads file automatically (no restart required)

### Backup System:
- **Method:** Manual command execution
- **Primary:** `docker exec medication-bot python backup.py`
- **Future:** Admin bot command `/admin_backup` (Phase 2)
- **Storage:** Local `/app/backups/` directory
- **Format:** `backup_YYYY-MM-DD_HH-MM.db`

### Monitoring & Logging:
```python
# Log levels and content
INFO: User actions (add/edit medicine, successful reminders)
ERROR: Failed reminders, database errors, access denials
DEBUG: Detailed flow tracking (development only)

# Log rotation: Daily, keep 7 days
# Location: /app/logs/bot.log
```

---

## 7. Operational Requirements

### Deployment Configuration:
```yaml
# docker-compose.yml essentials
services:
  medication-bot:
    build: .
    container_name: med-reminder-bot
    restart: unless-stopped  # Auto-restart on crash
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./logs:/app/logs
      - ./backups:/app/backups
    environment:
      - TZ=Europe/Kiev
    mem_limit: 512m
    cpus: 0.5
```

### System Requirements:
- **Auto-start:** Container starts automatically on Pi boot
- **Auto-restart:** Container restarts automatically if crashed
- **Resource limits:** 512MB RAM, 0.5 CPU cores maximum
- **Storage:** ~1GB total footprint

### Security & Privacy:
```bash
# Files excluded from version control (.gitignore)
config/bot_token.txt
config/allowed_users.txt  
data/database.db
logs/*.log
backups/*.db
```

---

## 8. Development Phases

### Phase 1 - Core MVP (3-4 weeks):
- ✅ Basic Ukrainian interface with button navigation
- ✅ SQLite database setup and CRUD operations
- ✅ User authentication via allowed_users.txt
- ✅ Medicine and reminder management (add/edit/delete)
- ✅ Timezone selection and time format handling
- ✅ Automatic reminder scheduling and delivery
- ✅ Docker containerization for Pi 5
- ✅ Basic error handling and input validation
- ✅ Manual backup functionality

### Phase 2 - Enhanced Features (2-3 weeks):
- ⏳ User acknowledgment system ([Прийняв]/[Пропустив])
- ⏳ Admin bot commands (/admin_backup, /admin_stats)
- ⏳ Enhanced error recovery and retry logic
- ⏳ System health monitoring and notifications
- ⏳ Improved help system with examples

### Phase 3 - Advanced Features (Future):
- ⏳ Caregiver notifications for missed medications
- ⏳ Retry logic for failed message delivery
- ⏳ Voice message support
- ⏳ Enhanced analytics and reporting
- ⏳ Export functionality for medical records

---

## 9. Success Criteria

### Technical Metrics:
- **Uptime:** 99%+ container availability
- **Response Time:** <2 seconds for all user interactions
- **Data Integrity:** Zero data loss with proper backups
- **Resource Usage:** Stay within 512MB RAM limit

### User Experience Metrics:
- **Error Rate:** <5% user input errors requiring clarification
- **Setup Success:** 100% successful user onboarding
- **Reminder Delivery:** 99%+ successful reminder sending
- **User Satisfaction:** Positive feedback from elderly users

### Operational Metrics:
- **Backup Reliability:** Weekly successful manual backups
- **System Recovery:** <5 minute recovery time from crashes
- **Administration:** Simple one-command user management

---

## 10. Dependencies & Libraries

### Core Python Dependencies:
```txt
python-telegram-bot==20.7
APScheduler==3.10.4
sqlite3 (built-in)
pytz==2023.3
logging (built-in)
datetime (built-in)
json (built-in)
```

### Development Dependencies:
```txt
pytest==7.4.0 (testing)
black==23.7.0 (code formatting)
```

---

This requirements document provides a complete roadmap for developing a robust, elderly-friendly medication reminder bot optimized for Raspberry Pi 5 deployment. The focus on simplicity, reliability, and Ukrainian interface ensures the bot will effectively serve its target audience while maintaining technical excellence.
