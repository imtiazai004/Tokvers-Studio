"""Password hashing (bcrypt) and secret encryption (Fernet) for BYOK keys."""
import bcrypt
from cryptography.fernet import Fernet

from .config import settings


def _pw_bytes(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes and newer versions raise on longer
    # input; truncate consistently so hashing and verifying always agree.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(password), hashed.encode("utf-8"))
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
