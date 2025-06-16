import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os

class Database:
    def __init__(self, db_path: str = "data/database.db"):
        self.db_path = db_path
        self.ensure_directory()
        self.init_db()
    
    def ensure_directory(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    timezone TEXT DEFAULT 'Europe/Kiev',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Medicines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medicines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
                )
            ''')
            
            # Reminders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medicine_id INTEGER,
                    time TEXT NOT NULL,
                    dosage TEXT NOT NULL,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (medicine_id) REFERENCES medicines (id) ON DELETE CASCADE
                )
            ''')
            
            # Reminder logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminder_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reminder_id) REFERENCES reminders (id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            logging.info("Database initialized successfully")
    
    def add_user(self, telegram_id: int, username: str = None, timezone: str = "Europe/Kiev") -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (telegram_id, username, timezone)
                    VALUES (?, ?, ?)
                ''', (telegram_id, username, timezone))
                conn.commit()
                logging.info(f"User {telegram_id} added/updated successfully")
                return True
        except Exception as e:
            logging.error(f"Error adding user {telegram_id}: {e}")
            return False
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'telegram_id': row[0],
                        'username': row[1],
                        'timezone': row[2],
                        'created_at': row[3]
                    }
                return None
        except Exception as e:
            logging.error(f"Error getting user {telegram_id}: {e}")
            return None
    
    def add_medicine(self, user_id: int, name: str) -> Optional[int]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO medicines (user_id, name) VALUES (?, ?)
                ''', (user_id, name))
                medicine_id = cursor.lastrowid
                conn.commit()
                logging.info(f"Medicine '{name}' added for user {user_id}")
                return medicine_id
        except Exception as e:
            logging.error(f"Error adding medicine for user {user_id}: {e}")
            return None
    
    def add_reminder(self, medicine_id: int, time: str, dosage: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO reminders (medicine_id, time, dosage) VALUES (?, ?, ?)
                ''', (medicine_id, time, dosage))
                conn.commit()
                logging.info(f"Reminder added for medicine {medicine_id} at {time}")
                return True
        except Exception as e:
            logging.error(f"Error adding reminder for medicine {medicine_id}: {e}")
            return False
    
    def get_user_medicines(self, user_id: int) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT m.id, m.name, r.id as reminder_id, r.time, r.dosage, r.active
                    FROM medicines m
                    LEFT JOIN reminders r ON m.id = r.medicine_id
                    WHERE m.user_id = ?
                    ORDER BY m.name, r.time
                ''', (user_id,))
                
                rows = cursor.fetchall()
                medicines = {}
                
                for row in rows:
                    med_id = row[0]
                    if med_id not in medicines:
                        medicines[med_id] = {
                            'id': med_id,
                            'name': row[1],
                            'reminders': []
                        }
                    
                    if row[2]:  # has reminder
                        medicines[med_id]['reminders'].append({
                            'id': row[2],
                            'time': row[3],
                            'dosage': row[4],
                            'active': row[5]
                        })
                
                return list(medicines.values())
        except Exception as e:
            logging.error(f"Error getting medicines for user {user_id}: {e}")
            return []
    
    def delete_medicine(self, medicine_id: int, user_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM medicines WHERE id = ? AND user_id = ?
                ''', (medicine_id, user_id))
                conn.commit()
                logging.info(f"Medicine {medicine_id} deleted for user {user_id}")
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting medicine {medicine_id}: {e}")
            return False
    
    def delete_reminder(self, reminder_id: int, user_id: int) -> bool:
        """Delete a specific reminder (check ownership via medicine)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM reminders 
                    WHERE id = ? AND medicine_id IN (
                        SELECT id FROM medicines WHERE user_id = ?
                    )
                ''', (reminder_id, user_id))
                conn.commit()
                logging.info(f"Reminder {reminder_id} deleted for user {user_id}")
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting reminder {reminder_id}: {e}")
            return False
    
    def get_medicine_with_reminders(self, medicine_id: int, user_id: int) -> Optional[Dict]:
        """Get a specific medicine with its reminders"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT m.id, m.name, r.id as reminder_id, r.time, r.dosage, r.active
                    FROM medicines m
                    LEFT JOIN reminders r ON m.id = r.medicine_id
                    WHERE m.id = ? AND m.user_id = ?
                    ORDER BY r.time
                ''', (medicine_id, user_id))
                
                rows = cursor.fetchall()
                if not rows:
                    return None
                
                medicine = {
                    'id': rows[0][0],
                    'name': rows[0][1],
                    'reminders': []
                }
                
                for row in rows:
                    if row[2]:  # has reminder
                        medicine['reminders'].append({
                            'id': row[2],
                            'time': row[3],
                            'dosage': row[4],
                            'active': row[5]
                        })
                
                return medicine
        except Exception as e:
            logging.error(f"Error getting medicine {medicine_id} for user {user_id}: {e}")
            return None
    
    def delete_all_user_medicines(self, user_id: int) -> int:
        """Delete all medicines for a user. Returns count of deleted medicines."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First get count of medicines to be deleted
                cursor.execute('SELECT COUNT(*) FROM medicines WHERE user_id = ?', (user_id,))
                count = cursor.fetchone()[0]
                
                # Delete all medicines (reminders will be deleted due to CASCADE)
                cursor.execute('DELETE FROM medicines WHERE user_id = ?', (user_id,))
                conn.commit()
                
                logging.info(f"All {count} medicines deleted for user {user_id}")
                return count
        except Exception as e:
            logging.error(f"Error deleting all medicines for user {user_id}: {e}")
            return 0
    
    def get_all_active_reminders(self) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT r.id, r.time, r.dosage, m.name, u.telegram_id, u.timezone
                    FROM reminders r
                    JOIN medicines m ON r.medicine_id = m.id
                    JOIN users u ON m.user_id = u.telegram_id
                    WHERE r.active = 1
                    ORDER BY r.time
                ''')
                
                rows = cursor.fetchall()
                return [{
                    'reminder_id': row[0],
                    'time': row[1],
                    'dosage': row[2],
                    'medicine_name': row[3],
                    'telegram_id': row[4],
                    'timezone': row[5]
                } for row in rows]
        except Exception as e:
            logging.error(f"Error getting active reminders: {e}")
            return []
    
    def log_reminder_sent(self, reminder_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO reminder_logs (reminder_id) VALUES (?)
                ''', (reminder_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error logging reminder {reminder_id}: {e}")
            return False
    
    def get_recent_reminder_logs(self, reminder_id: int, minutes: int = 2) -> List[Dict]:
        """Check if reminder was sent recently to avoid duplicates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, sent_at FROM reminder_logs 
                    WHERE reminder_id = ? 
                    AND datetime(sent_at) > datetime('now', '-{} minutes')
                    ORDER BY sent_at DESC
                '''.format(minutes), (reminder_id,))
                
                rows = cursor.fetchall()
                return [{
                    'id': row[0],
                    'sent_at': row[1]
                } for row in rows]
        except Exception as e:
            logging.error(f"Error checking recent reminder logs for {reminder_id}: {e}")
            return []