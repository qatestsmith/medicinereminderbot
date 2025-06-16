#!/usr/bin/env python3
"""
Configuration Encryption Setup Script

This script helps you encrypt your sensitive configuration files (bot token and user list)
for secure storage. Even if these files are leaked, they cannot be decrypted without the secret key.

Usage:
    python encrypt_config.py

Features:
- Encrypts existing plain text config files
- Creates new encrypted config files
- Backs up encryption key
- Provides secure file permissions
"""

import os
import sys
import time
import getpass
from pathlib import Path

# Add app directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from utils.encryption import SecureStorage

def print_header():
    print("🔐" + "="*60)
    print("    Medicine Reminder Bot - Configuration Encryption")
    print("="*62)
    print()

def print_success(message):
    print(f"✅ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def confirm_action(prompt):
    """Get user confirmation for an action"""
    while True:
        response = input(f"{prompt} (y/N): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no', '']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")

def setup_encrypted_token():
    """Setup encrypted bot token"""
    print("\n📱 Bot Token Setup")
    print("-" * 20)
    
    token_file = "app/config/bot_token.txt"
    encrypted_file = token_file + ".enc"
    storage = SecureStorage()
    
    # Check existing files
    has_plain = os.path.exists(token_file)
    has_encrypted = os.path.exists(encrypted_file)
    
    if has_encrypted:
        print_info(f"Encrypted token already exists: {encrypted_file}")
        if has_plain:
            print_warning(f"Plain text token also exists: {token_file}")
            if confirm_action("Delete the plain text token file for security"):
                os.remove(token_file)
                print_success("Plain text token file deleted")
        return True
    
    if has_plain:
        print_info(f"Found plain text token: {token_file}")
        if confirm_action("Encrypt this token file"):
            if storage.encrypt_file(token_file, encrypted_file):
                print_success(f"Token encrypted and saved to {encrypted_file}")
                if confirm_action("Delete the original plain text file"):
                    os.remove(token_file)
                    print_success("Original token file deleted")
                return True
            else:
                print_error("Failed to encrypt token file")
                return False
    else:
        print_info("No bot token found. Please enter your bot token.")
        print_info("You can get this from @BotFather on Telegram")
        print()
        
        while True:
            token = getpass.getpass("🤖 Bot Token: ").strip()
            if not token:
                print_error("Token cannot be empty")
                continue
            
            if not token.startswith(('1', '2', '5', '6')):  # Basic bot token validation
                print_warning("This doesn't look like a valid bot token")
                if not confirm_action("Use it anyway"):
                    continue
            
            # Encrypt and save
            if storage.encrypt_text_to_file(token, encrypted_file):
                print_success(f"Token encrypted and saved to {encrypted_file}")
                return True
            else:
                print_error("Failed to encrypt token")
                return False

def setup_encrypted_users():
    """Setup encrypted users list"""
    print("\n👥 Allowed Users Setup")
    print("-" * 25)
    
    users_file = "app/config/allowed_users.txt"
    encrypted_file = users_file + ".enc"
    storage = SecureStorage()
    
    # Check existing files
    has_plain = os.path.exists(users_file)
    has_encrypted = os.path.exists(encrypted_file)
    
    if has_encrypted:
        print_info(f"Encrypted users file already exists: {encrypted_file}")
        if has_plain:
            print_warning(f"Plain text users file also exists: {users_file}")
            if confirm_action("Delete the plain text users file for security"):
                os.remove(users_file)
                print_success("Plain text users file deleted")
        return True
    
    if has_plain:
        print_info(f"Found plain text users file: {users_file}")
        if confirm_action("Encrypt this users file"):
            if storage.encrypt_file(users_file, encrypted_file):
                print_success(f"Users file encrypted and saved to {encrypted_file}")
                if confirm_action("Delete the original plain text file"):
                    os.remove(users_file)
                    print_success("Original users file deleted")
                return True
            else:
                print_error("Failed to encrypt users file")
                return False
    else:
        print_info("No users file found. Let's create one.")
        print_info("You can add Telegram user IDs or usernames (one per line)")
        print_info("Examples:")
        print_info("  123456789     (user ID)")
        print_info("  @username     (username)")
        print_info("  username      (username without @)")
        print()
        
        users = []
        print("Enter allowed users (press Enter on empty line to finish):")
        
        while True:
            user = input("👤 User ID or username: ").strip()
            if not user:
                break
            users.append(user)
            print_success(f"Added: {user}")
        
        if users:
            users_text = "\n".join(users)
            if storage.encrypt_text_to_file(users_text, encrypted_file):
                print_success(f"Users file encrypted and saved to {encrypted_file}")
                return True
            else:
                print_error("Failed to encrypt users file")
                return False
        else:
            print_warning("No users added. You can add them later.")
            return True

def backup_encryption_key():
    """Create backup of encryption key"""
    print("\n🔑 Encryption Key Backup")
    print("-" * 25)
    
    storage = SecureStorage()
    timestamp = int(time.time())
    backup_dir = "app/config"
    backup_file = f"{backup_dir}/secret.key.backup.{timestamp}"
    
    if storage.backup_key(backup_file):
        print_success(f"Encryption key backed up to: {backup_file}")
        print_warning("Keep this backup safe! You'll need it to decrypt your files.")
        return True
    else:
        print_error("Failed to backup encryption key")
        return False

def display_security_info():
    """Display important security information"""
    print("\n🛡️  Security Information")
    print("-" * 25)
    print_info("Your sensitive files are now encrypted with AES-256.")
    print_info("The encryption key is stored in: app/config/secret.key")
    print()
    print_warning("IMPORTANT SECURITY NOTES:")
    print("• Keep your secret.key file safe and backed up")
    print("• Without the key, you CANNOT decrypt your files")
    print("• Don't commit the secret.key to version control")
    print("• The .gitignore already excludes sensitive files")
    print("• Original plain text files have been deleted")
    print()
    print_info("Encrypted files:")
    
    encrypted_files = []
    if os.path.exists("app/config/bot_token.txt.enc"):
        encrypted_files.append("app/config/bot_token.txt.enc")
    if os.path.exists("app/config/allowed_users.txt.enc"):
        encrypted_files.append("app/config/allowed_users.txt.enc")
    
    for file in encrypted_files:
        print(f"  • {file}")
    
    if not encrypted_files:
        print("  • None (setup was not completed)")

def verify_setup():
    """Verify the encryption setup works"""
    print("\n🔍 Verifying Setup")
    print("-" * 20)
    
    storage = SecureStorage()
    success = True
    
    # Test token loading
    encrypted_token = "app/config/bot_token.txt.enc"
    if os.path.exists(encrypted_token):
        token = storage.load_encrypted_text(encrypted_token)
        if token:
            print_success("Bot token can be decrypted")
        else:
            print_error("Failed to decrypt bot token")
            success = False
    
    # Test users loading
    encrypted_users = "app/config/allowed_users.txt.enc"
    if os.path.exists(encrypted_users):
        users = storage.load_encrypted_text(encrypted_users)
        if users:
            print_success("Users file can be decrypted")
        else:
            print_error("Failed to decrypt users file")
            success = False
    
    if success:
        print_success("All encrypted files verified successfully!")
    else:
        print_error("Some files could not be verified")
    
    return success

def main():
    """Main setup function"""
    print_header()
    
    print("This script will help you encrypt your bot's sensitive configuration files.")
    print("This includes your bot token and allowed users list.")
    print()
    
    if not confirm_action("Do you want to proceed with encryption setup"):
        print("Setup cancelled.")
        return
    
    # Ensure directories exist
    os.makedirs("app/config", exist_ok=True)
    
    success = True
    
    # Setup encrypted token
    if not setup_encrypted_token():
        success = False
    
    # Setup encrypted users
    if not setup_encrypted_users():
        success = False
    
    # Backup encryption key
    if not backup_encryption_key():
        success = False
    
    # Verify setup
    if not verify_setup():
        success = False
    
    # Display final information
    display_security_info()
    
    if success:
        print("\n" + "="*62)
        print_success("🎉 Encryption setup completed successfully!")
        print("Your sensitive files are now protected.")
        print("="*62)
    else:
        print("\n" + "="*62)
        print_error("⚠️  Setup completed with some issues.")
        print("Please review the messages above.")
        print("="*62)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the error and try again.")