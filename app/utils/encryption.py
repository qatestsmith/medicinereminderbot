#!/usr/bin/env python3
import os
import logging
from cryptography.fernet import Fernet
from typing import Optional, Union
import base64
import getpass

class SecureStorage:
    """Handles encryption/decryption of sensitive files like bot tokens and user lists"""
    
    def __init__(self, key_file: str = "config/secret.key"):
        self.key_file = key_file
        self.key_path = os.path.join(os.path.dirname(__file__), "..", key_file)
        self._fernet = None
        self.logger = logging.getLogger(__name__)
    
    def _get_fernet(self) -> Fernet:
        """Initialize Fernet cipher with key"""
        if self._fernet is None:
            key = self._load_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create new one"""
        if os.path.exists(self.key_path):
            return self._load_key()
        else:
            return self._create_key()
    
    def _load_key(self) -> bytes:
        """Load encryption key from file"""
        try:
            with open(self.key_path, 'rb') as key_file:
                return key_file.read()
        except Exception as e:
            self.logger.error(f"Failed to load encryption key: {e}")
            raise
    
    def _create_key(self) -> bytes:
        """Create new encryption key"""
        try:
            # Generate key
            key = Fernet.generate_key()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
            
            # Save key
            with open(self.key_path, 'wb') as key_file:
                key_file.write(key)
            
            # Secure permissions (owner only)
            os.chmod(self.key_path, 0o600)
            
            self.logger.info(f"New encryption key created at {self.key_path}")
            return key
            
        except Exception as e:
            self.logger.error(f"Failed to create encryption key: {e}")
            raise
    
    def encrypt_file(self, file_path: str, output_path: str = None) -> bool:
        """Encrypt a plain text file"""
        try:
            if output_path is None:
                output_path = file_path + ".enc"
            
            # Read plain text
            with open(file_path, 'r', encoding='utf-8') as f:
                plain_text = f.read()
            
            # Encrypt
            encrypted_data = self._get_fernet().encrypt(plain_text.encode('utf-8'))
            
            # Write encrypted file
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Secure permissions
            os.chmod(output_path, 0o600)
            
            self.logger.info(f"File encrypted: {file_path} -> {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt {file_path}: {e}")
            return False
    
    def decrypt_file(self, encrypted_path: str, output_path: str = None) -> Optional[str]:
        """Decrypt an encrypted file and return content"""
        try:
            # Read encrypted data
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            decrypted_data = self._get_fernet().decrypt(encrypted_data)
            plain_text = decrypted_data.decode('utf-8')
            
            # Optionally save to file
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(plain_text)
                self.logger.info(f"File decrypted: {encrypted_path} -> {output_path}")
            
            return plain_text
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt {encrypted_path}: {e}")
            return None
    
    def encrypt_string(self, text: str) -> str:
        """Encrypt a string and return base64 encoded result"""
        try:
            encrypted_data = self._get_fernet().encrypt(text.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to encrypt string: {e}")
            return ""
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt a base64 encoded encrypted string"""
        try:
            encrypted_data = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted_data = self._get_fernet().decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to decrypt string: {e}")
            return ""
    
    def encrypt_text_to_file(self, text: str, file_path: str) -> bool:
        """Encrypt text and save to file"""
        try:
            encrypted_data = self._get_fernet().encrypt(text.encode('utf-8'))
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Secure permissions
            os.chmod(file_path, 0o600)
            
            self.logger.info(f"Text encrypted to file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt text to {file_path}: {e}")
            return False
    
    def load_encrypted_text(self, file_path: str) -> Optional[str]:
        """Load and decrypt text from encrypted file"""
        try:
            if not os.path.exists(file_path):
                self.logger.warning(f"Encrypted file not found: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._get_fernet().decrypt(encrypted_data)
            return decrypted_data.decode('utf-8').strip()
            
        except Exception as e:
            self.logger.error(f"Failed to load encrypted text from {file_path}: {e}")
            return None
    
    def key_exists(self) -> bool:
        """Check if encryption key exists"""
        return os.path.exists(self.key_path)
    
    def backup_key(self, backup_path: str) -> bool:
        """Create a backup of the encryption key"""
        try:
            if not self.key_exists():
                self.logger.error("No encryption key to backup")
                return False
            
            import shutil
            shutil.copy2(self.key_path, backup_path)
            os.chmod(backup_path, 0o600)
            
            self.logger.info(f"Encryption key backed up to: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup key: {e}")
            return False

def setup_secure_config():
    """Interactive setup for encrypting existing config files"""
    storage = SecureStorage()
    
    print("🔐 Setting up encrypted configuration...")
    print("This will encrypt your bot token and user list for security.")
    print()
    
    # Check for existing files
    token_file = "config/bot_token.txt"
    users_file = "config/allowed_users.txt"
    
    if os.path.exists(token_file):
        print(f"Found existing token file: {token_file}")
        if input("Encrypt it? (y/N): ").lower() == 'y':
            if storage.encrypt_file(token_file, token_file + ".enc"):
                print(f"✅ Token encrypted to {token_file}.enc")
                if input("Delete original file? (y/N): ").lower() == 'y':
                    os.remove(token_file)
                    print("✅ Original token file deleted")
    
    if os.path.exists(users_file):
        print(f"Found existing users file: {users_file}")
        if input("Encrypt it? (y/N): ").lower() == 'y':
            if storage.encrypt_file(users_file, users_file + ".enc"):
                print(f"✅ Users encrypted to {users_file}.enc")
                if input("Delete original file? (y/N): ").lower() == 'y':
                    os.remove(users_file)
                    print("✅ Original users file deleted")
    
    # Create new encrypted files if needed
    if not os.path.exists(token_file) and not os.path.exists(token_file + ".enc"):
        print("\nNo bot token found. Please enter your bot token:")
        token = getpass.getpass("Bot Token: ")
        if token:
            storage.encrypt_text_to_file(token, token_file + ".enc")
            print(f"✅ Token encrypted and saved to {token_file}.enc")
    
    if not os.path.exists(users_file) and not os.path.exists(users_file + ".enc"):
        print("\nNo users file found. Creating encrypted users file...")
        print("Enter allowed user IDs (one per line, empty line to finish):")
        users = []
        while True:
            user = input("User ID: ").strip()
            if not user:
                break
            users.append(user)
        
        if users:
            users_text = "\n".join(users)
            storage.encrypt_text_to_file(users_text, users_file + ".enc")
            print(f"✅ Users encrypted and saved to {users_file}.enc")
    
    # Backup key
    backup_path = f"config/secret.key.backup.{int(time.time())}"
    if storage.backup_key(backup_path):
        print(f"✅ Encryption key backed up to {backup_path}")
    
    print("\n🔐 Encryption setup complete!")
    print("⚠️  IMPORTANT: Keep your secret.key file safe and backed up!")
    print("    Without it, you cannot decrypt your sensitive data.")

if __name__ == "__main__":
    import time
    setup_secure_config()