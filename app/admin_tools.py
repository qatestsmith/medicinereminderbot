#!/usr/bin/env python3
"""
Admin tools for managing allowed users
"""
import argparse
import sys
from utils.helpers import load_allowed_users

def list_users():
    """List all allowed users"""
    allowed = load_allowed_users()
    
    print("📋 Allowed Users:")
    print("=" * 50)
    
    if allowed["user_ids"]:
        print("\n👤 User IDs:")
        for user_id in allowed["user_ids"]:
            print(f"  • {user_id}")
    
    if allowed["usernames"]:
        print("\n📝 Usernames:")
        for username in allowed["usernames"]:
            print(f"  • @{username}")
    
    if not allowed["user_ids"] and not allowed["usernames"]:
        print("  (No users configured)")
    
    total = len(allowed["user_ids"]) + len(allowed["usernames"])
    print(f"\nTotal: {total} allowed users")

def add_user(identifier: str):
    """Add a user to allowed list"""
    try:
        # Try to parse as user ID
        user_id = int(identifier)
        with open("config/allowed_users.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{user_id}")
        print(f"✅ Added user ID: {user_id}")
    except ValueError:
        # Treat as username
        username = identifier.lstrip('@')
        if 5 <= len(username) <= 32 and username.replace('_', '').isalnum():
            with open("config/allowed_users.txt", "a", encoding="utf-8") as f:
                f.write(f"\n{username}")
            print(f"✅ Added username: @{username}")
        else:
            print(f"❌ Invalid username format: {identifier}")
            return False
    return True

def remove_user(identifier: str):
    """Remove a user from allowed list"""
    try:
        with open("config/allowed_users.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        new_lines = []
        removed = False
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#'):
                # Check if this line matches the identifier to remove
                if line_stripped == identifier or line_stripped == identifier.lstrip('@'):
                    removed = True
                    print(f"✅ Removed: {line_stripped}")
                    continue
            new_lines.append(line)
        
        if removed:
            with open("config/allowed_users.txt", "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        else:
            print(f"❌ User not found: {identifier}")
            return False
        
    except Exception as e:
        print(f"❌ Error removing user: {e}")
        return False
    
    return True

def validate_config():
    """Validate the current allowed_users.txt configuration"""
    print("🔍 Validating configuration...")
    
    allowed = load_allowed_users()
    user_ids = allowed["user_ids"]
    usernames = allowed["usernames"]
    
    print(f"✅ Found {len(user_ids)} valid user IDs")
    print(f"✅ Found {len(usernames)} valid usernames")
    
    # Check for potential issues
    try:
        with open("config/allowed_users.txt", "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line_stripped = line.strip()
                if line_stripped and not line_stripped.startswith('#'):
                    try:
                        int(line_stripped)  # Valid user ID
                    except ValueError:
                        # Check username
                        username = line_stripped.lstrip('@')
                        if not (5 <= len(username) <= 32 and username.replace('_', '').isalnum()):
                            print(f"⚠️  Warning: Invalid format on line {line_num}: {line_stripped}")
    except Exception as e:
        print(f"❌ Error reading config: {e}")

def main():
    parser = argparse.ArgumentParser(description='Admin tools for managing allowed users')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    subparsers.add_parser('list', help='List all allowed users')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a user (ID or username)')
    add_parser.add_argument('user', help='User ID (numeric) or username')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a user')
    remove_parser.add_argument('user', help='User ID (numeric) or username')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate configuration file')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_users()
    elif args.command == 'add':
        add_user(args.user)
    elif args.command == 'remove':
        remove_user(args.user)
    elif args.command == 'validate':
        validate_config()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()