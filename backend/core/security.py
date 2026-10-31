import hmac
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jwt

from backend.core.config import settings

# Salted PBKDF2 Password Hashing
ROUNDS = 100_000


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 16 bytes salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ROUNDS)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed salt:key."""
    try:
        salt_hex, key_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, ROUNDS)
        return hmac.compare_digest(key, new_key)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None


def generate_api_key() -> Tuple[str, str]:
    """
    Generate an API key and its secure SHA-256 hash.
    Returns (raw_key, hashed_key). The raw key is shown only once to user.
    """
    raw_key = f"cbk_live_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(raw_key)
    return raw_key, hashed_key


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
