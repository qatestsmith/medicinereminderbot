#!/usr/bin/env python3
"""
User Management Script for Medicine Reminder Bot

This script helps you manage allowed users for your bot securely.
It handles encryption/decryption automatically.

Usage:
    python manage_users.py

Features:
- List current users
- Add new users (by ID or username)
- Remove users
- Validate user format
- Automatic encryption/decryption
"""

import os
import sys
import re
from typing import List, Dict, Tuple

# Add app directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from utils.encryption import SecureStorage

class UserManager:
    def __init__(self):
        self.storage = SecureStorage()
        self.users_file = "app/config/allowed_users.txt"
        self.encrypted_file = self.users_file + ".enc"
        
    def load_users(self) -> Tuple[List[str], List[str]]:
        """Load users from encrypted file. Returns (user_ids, usernames)"""
        content = ""
        
        if os.path.exists(self.encrypted_file):
            content = self.storage.load_encrypted_text(self.encrypted_file) or ""
        elif os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                content = f.read()
        
        user_ids = []
        usernames = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if line.isdigit():
                    user_ids.append(line)
                else:
                    # Remove @ if present
                    username = line[1:] if line.startswith('@') else line
                    usernames.append(username)
        
        return user_ids, usernames
    
    def save_users(self, user_ids: List[str], usernames: List[str]) -> bool:
        """Save users to encrypted file"""
        content_lines = []
        
        # Add header comment
        content_lines.append("# Allowed users for Medicine Reminder Bot")
        content_lines.append("# Format: user_id (numbers) or username (text)")
        content_lines.append("")
        
        # Add user IDs
        if user_ids:
            content_lines.append("# User IDs:")
            content_lines.extend(user_ids)
            content_lines.append("")
        
        # Add usernames
        if usernames:
            content_lines.append("# Usernames:")
            content_lines.extend(usernames)
        
        content = '\n'.join(content_lines)
        
        # Save encrypted
        success = self.storage.encrypt_text_to_file(content, self.encrypted_file)
        
        # Remove plain text file if it exists
        if success and os.path.exists(self.users_file):
            os.remove(self.users_file)
        
        return success
    
    def validate_user_id(self, user_id: str) -> bool:
        """Validate Telegram user ID format"""
        return user_id.isdigit() and 5 <= len(user_id) <= 15
    
    def validate_username(self, username: str) -> bool:
        """Validate Telegram username format"""
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
        
        # Telegram usernames: 5-32 chars, alphanumeric + underscore
        return (5 <= len(username) <= 32 and 
                username.replace('_', '').isalnum() and
                not username.isdigit())  # Don't confuse with user ID
    
    def format_username(self, username: str) -> str:
        """Format username (remove @ prefix)"""
        return username[1:] if username.startswith('@') else username
    
    def list_users(self):
        """Display current users"""
        user_ids, usernames = self.load_users()
        
        print("📋 Current Allowed Users")
        print("=" * 30)
        
        if not user_ids and not usernames:
            print("❌ No users configured")
            return
        
        if user_ids:
            print("\n👤 User IDs:")
            for i, user_id in enumerate(user_ids, 1):
                print(f"  {i}. {user_id}")
        
        if usernames:
            print("\n📝 Usernames:")
            for i, username in enumerate(usernames, 1):
                print(f"  {i}. @{username}")
        
        print(f"\nTotal: {len(user_ids)} user IDs, {len(usernames)} usernames")
    
    def add_user(self):
        """Add a new user"""
        print("\n➕ Add New User")
        print("-" * 20)
        print("You can add either:")
        print("• User ID (numbers): 123456789")
        print("• Username: @username or username")
        print()
        
        while True:
            user_input = input("👤 Enter user ID or username (or 'back' to return): ").strip()
            
            if user_input.lower() in ['back', 'b', '']:
                return
            
            # Check if it's a user ID
            if user_input.isdigit():
                if self.validate_user_id(user_input):
                    user_ids, usernames = self.load_users()
                    
                    if user_input in user_ids:
                        print(f"❌ User ID {user_input} already exists")
                        continue
                    
                    user_ids.append(user_input)
                    if self.save_users(user_ids, usernames):
                        print(f"✅ Added user ID: {user_input}")
                        return
                    else:
                        print("❌ Failed to save users")
                        return
                else:
                    print("❌ Invalid user ID format (should be 5-15 digits)")
                    continue
            
            # Check if it's a username
            elif self.validate_username(user_input):
                username = self.format_username(user_input).lower()
                user_ids, usernames = self.load_users()
                
                if username in usernames:
                    print(f"❌ Username @{username} already exists")
                    continue
                
                usernames.append(username)
                if self.save_users(user_ids, usernames):
                    print(f"✅ Added username: @{username}")
                    return
                else:
                    print("❌ Failed to save users")
                    return
            
            else:
                print("❌ Invalid format. Use user ID (numbers) or username (5-32 chars, letters/numbers/_)")
    
    def remove_user(self):
        """Remove a user"""
        user_ids, usernames = self.load_users()
        
        if not user_ids and not usernames:
            print("❌ No users to remove")
            return
        
        print("\n🗑️  Remove User")
        print("-" * 15)
        
        # Create numbered list
        all_users = []
        print("Select user to remove:")
        
        index = 1
        for user_id in user_ids:
            print(f"  {index}. User ID: {user_id}")
            all_users.append(('id', user_id))
            index += 1
        
        for username in usernames:
            print(f"  {index}. Username: @{username}")
            all_users.append(('username', username))
            index += 1
        
        print(f"  0. Back to main menu")
        
        while True:
            try:
                choice = input("\n🔢 Enter number: ").strip()
                
                if choice == '0' or choice.lower() in ['back', 'b']:
                    return
                
                choice = int(choice)
                if 1 <= choice <= len(all_users):
                    user_type, user_value = all_users[choice - 1]
                    
                    # Confirm deletion
                    user_display = f"User ID {user_value}" if user_type == 'id' else f"Username @{user_value}"
                    confirm = input(f"❓ Remove {user_display}? (y/N): ").lower().strip()
                    
                    if confirm in ['y', 'yes']:
                        # Remove user
                        if user_type == 'id':
                            user_ids.remove(user_value)
                        else:
                            usernames.remove(user_value)
                        
                        if self.save_users(user_ids, usernames):
                            print(f"✅ Removed {user_display}")
                            return
                        else:
                            print("❌ Failed to save users")
                            return
                    else:
                        print("❌ Cancelled")
                        return
                else:
                    print(f"❌ Invalid choice. Enter 1-{len(all_users)} or 0")
                    
            except ValueError:
                print("❌ Please enter a valid number")
    
    def search_user(self):
        """Search for a user"""
        user_ids, usernames = self.load_users()
        
        if not user_ids and not usernames:
            print("❌ No users configured")
            return
        
        print("\n🔍 Search User")
        print("-" * 15)
        
        search_term = input("👤 Enter user ID or username to search: ").strip()
        if not search_term:
            return
        
        # Remove @ if searching username
        if search_term.startswith('@'):
            search_term = search_term[1:]
        
        found = False
        
        # Search user IDs
        if search_term.isdigit():
            if search_term in user_ids:
                print(f"✅ Found user ID: {search_term}")
                found = True
        
        # Search usernames
        search_lower = search_term.lower()
        for username in usernames:
            if search_lower in username.lower():
                print(f"✅ Found username: @{username}")
                found = True
        
        if not found:
            print(f"❌ User '{search_term}' not found")
    
    def import_users(self):
        """Import users from file"""
        print("\n📥 Import Users")
        print("-" * 15)
        print("Create a text file with users (one per line) and specify the path.")
        print("Format: user IDs (numbers) or usernames")
        print()
        
        file_path = input("📁 Enter file path (or 'back' to return): ").strip()
        
        if file_path.lower() in ['back', 'b', '']:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            user_ids, usernames = self.load_users()
            new_user_ids = []
            new_usernames = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.isdigit() and self.validate_user_id(line):
                        if line not in user_ids:
                            new_user_ids.append(line)
                    elif self.validate_username(line):
                        username = self.format_username(line).lower()
                        if username not in usernames:
                            new_usernames.append(username)
                    else:
                        print(f"⚠️  Invalid format on line {line_num}: {line}")
            
            if new_user_ids or new_usernames:
                user_ids.extend(new_user_ids)
                usernames.extend(new_usernames)
                
                if self.save_users(user_ids, usernames):
                    print(f"✅ Imported {len(new_user_ids)} user IDs and {len(new_usernames)} usernames")
                else:
                    print("❌ Failed to save users")
            else:
                print("❌ No new valid users found in file")
                
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
        except Exception as e:
            print(f"❌ Error reading file: {e}")
    
    def export_users(self):
        """Export users to file"""
        user_ids, usernames = self.load_users()
        
        if not user_ids and not usernames:
            print("❌ No users to export")
            return
        
        print("\n📤 Export Users")
        print("-" * 15)
        
        file_path = input("📁 Enter export file path (e.g., users_backup.txt): ").strip()
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Medicine Reminder Bot - Users Export\n")
                f.write(f"# Exported on {__import__('datetime').datetime.now()}\n\n")
                
                if user_ids:
                    f.write("# User IDs:\n")
                    for user_id in user_ids:
                        f.write(f"{user_id}\n")
                    f.write("\n")
                
                if usernames:
                    f.write("# Usernames:\n")
                    for username in usernames:
                        f.write(f"@{username}\n")
            
            print(f"✅ Users exported to: {file_path}")
            
        except Exception as e:
            print(f"❌ Error exporting users: {e}")

def print_header():
    print("👥" + "="*50)
    print("    Medicine Reminder Bot - User Management")
    print("="*52)

def print_menu():
    print("\n📋 What would you like to do?")
    print("-" * 30)
    print("1. 📝 List current users")
    print("2. ➕ Add new user")
    print("3. 🗑️  Remove user")
    print("4. 🔍 Search user")
    print("5. 📥 Import users from file")
    print("6. 📤 Export users to file")
    print("0. 🚪 Exit")

def main():
    print_header()
    manager = UserManager()
    
    while True:
        print_menu()
        
        try:
            choice = input("\n🔢 Enter your choice: ").strip()
            
            if choice == '0':
                print("👋 Goodbye!")
                break
            elif choice == '1':
                manager.list_users()
            elif choice == '2':
                manager.add_user()
            elif choice == '3':
                manager.remove_user()
            elif choice == '4':
                manager.search_user()
            elif choice == '5':
                manager.import_users()
            elif choice == '6':
                manager.export_users()
            else:
                print("❌ Invalid choice. Please enter 0-6")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")