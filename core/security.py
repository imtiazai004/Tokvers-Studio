"""Password hashing (bcrypt) and secret encryption (Fernet) for BYOK keys."""
import bcrypt
from cryptography.fernet import Fernet

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _cipher() -> Fernet:
    key = settings.encryption_key
    if not key:
        raise RuntimeError("ENCRYPTION_KEY not set — required to encrypt workspace API keys.")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plain: str) -> str:
    """Encrypt a per-workspace secret (e.g. a BYOK provider key) for storage."""
    if not plain:
        return ""
    return _cipher().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    return _cipher().decrypt(token.encode()).decode()
