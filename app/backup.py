#!/usr/bin/env python3
import os
import shutil
import sqlite3
import logging
from datetime import datetime
import argparse
import sys

class DatabaseBackup:
    def __init__(self, db_path: str = "data/database.db", backup_dir: str = "backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.ensure_backup_directory()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def ensure_backup_directory(self):
        """Ensure backup directory exists"""
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self) -> str:
        """Create a backup of the database"""
        try:
            if not os.path.exists(self.db_path):
                self.logger.error(f"Database file not found: {self.db_path}")
                return None
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Create backup using SQLite backup API for consistency
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            # Verify backup
            if self.verify_backup(backup_path):
                self.logger.info(f"Backup created successfully: {backup_path}")
                return backup_path
            else:
                self.logger.error(f"Backup verification failed: {backup_path}")
                os.remove(backup_path)
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return None
    
    def verify_backup(self, backup_path: str) -> bool:
        """Verify backup integrity"""
        try:
            with sqlite3.connect(backup_path) as conn:
                cursor = conn.cursor()
                
                # Check if main tables exist and have data
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                expected_tables = ['users', 'medicines', 'reminders', 'reminder_logs']
                existing_tables = [table[0] for table in tables]
                
                for expected_table in expected_tables:
                    if expected_table not in existing_tables:
                        self.logger.error(f"Missing table in backup: {expected_table}")
                        return False
                
                # Test a simple query
                cursor.execute("SELECT COUNT(*) FROM users")
                cursor.fetchone()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return False
    
    def list_backups(self) -> list:
        """List all available backups"""
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("backup_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        'filename': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime)
                    })
            
            # Sort by creation time, newest first
            backups.sort(key=lambda x: x['created'], reverse=True)
            return backups
            
        except Exception as e:
            self.logger.error(f"Error listing backups: {e}")
            return []
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Verify backup before restoring
            if not self.verify_backup(backup_path):
                self.logger.error(f"Backup verification failed: {backup_path}")
                return False
            
            # Create backup of current database
            current_backup = None
            if os.path.exists(self.db_path):
                current_backup = f"{self.db_path}.restore-backup"
                shutil.copy2(self.db_path, current_backup)
                self.logger.info(f"Current database backed up to: {current_backup}")
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            
            # Verify restored database
            if self.verify_backup(self.db_path):
                self.logger.info(f"Database restored successfully from: {backup_path}")
                
                # Remove temporary backup if restore successful
                if current_backup and os.path.exists(current_backup):
                    os.remove(current_backup)
                
                return True
            else:
                # Restore failed, revert to original
                if current_backup and os.path.exists(current_backup):
                    shutil.copy2(current_backup, self.db_path)
                    os.remove(current_backup)
                    self.logger.error("Restore failed, reverted to original database")
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            return False
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """Remove backups older than specified days"""
        try:
            cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            removed_count = 0
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("backup_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_dir, filename)
                    if os.path.getctime(filepath) < cutoff_date:
                        os.remove(filepath)
                        removed_count += 1
                        self.logger.info(f"Removed old backup: {filename}")
            
            self.logger.info(f"Cleanup completed. Removed {removed_count} old backups.")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return 0

def main():
    parser = argparse.ArgumentParser(description='Database backup utility')
    parser.add_argument('action', choices=['create', 'list', 'restore', 'cleanup'], 
                       help='Action to perform')
    parser.add_argument('--backup-file', help='Backup file path for restore action')
    parser.add_argument('--keep-days', type=int, default=30, 
                       help='Days to keep backups (for cleanup action)')
    parser.add_argument('--db-path', default='data/database.db', 
                       help='Database file path')
    parser.add_argument('--backup-dir', default='backups', 
                       help='Backup directory')
    
    args = parser.parse_args()
    
    backup_tool = DatabaseBackup(args.db_path, args.backup_dir)
    
    if args.action == 'create':
        backup_path = backup_tool.create_backup()
        if backup_path:
            print(f"Backup created: {backup_path}")
            sys.exit(0)
        else:
            print("Backup failed")
            sys.exit(1)
    
    elif args.action == 'list':
        backups = backup_tool.list_backups()
        if backups:
            print("Available backups:")
            for backup in backups:
                size_mb = backup['size'] / (1024 * 1024)
                print(f"  {backup['filename']} - {size_mb:.2f}MB - {backup['created']}")
        else:
            print("No backups found")
    
    elif args.action == 'restore':
        if not args.backup_file:
            print("Error: --backup-file is required for restore action")
            sys.exit(1)
        
        if backup_tool.restore_backup(args.backup_file):
            print(f"Database restored from: {args.backup_file}")
            sys.exit(0)
        else:
            print("Restore failed")
            sys.exit(1)
    
    elif args.action == 'cleanup':
        removed = backup_tool.cleanup_old_backups(args.keep_days)
        print(f"Cleaned up {removed} old backups")

if __name__ == "__main__":
    main()