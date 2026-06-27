"""Encryption utilities for sensitive data like passwords."""

from cryptography.fernet import Fernet
import os

# Generate or load encryption key from environment
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Generate new key and print it (for setup)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"\nGenerated new encryption key. Set this in .env:\nENCRYPTION_KEY={ENCRYPTION_KEY}\n")

cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_password(password: str) -> str:
    """Encrypt password using Fernet (AES-128)"""
    if not password:
        return ""
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    """Decrypt password"""
    if not encrypted:
        return ""
    try:
        return cipher.decrypt(encrypted.encode()).decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        return ""
