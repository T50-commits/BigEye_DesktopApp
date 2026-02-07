"""
BigEye Pro — Security Utilities
JWT token management, password hashing, AES encryption.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from app.config import settings

logger = logging.getLogger("bigeye-api")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# JWT
def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT token with user_id and email."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Decode and validate JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# AES-256 encryption
def encrypt_aes(plaintext: str) -> str:
    """Encrypt plaintext with AES-256-CBC. Returns hex(iv + ciphertext)."""
    key = bytes.fromhex(settings.AES_KEY)
    cipher = AES.new(key, AES.MODE_CBC)
    ct = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return (cipher.iv + ct).hex()


def decrypt_aes(hex_data: str) -> str:
    """Decrypt AES-256-CBC hex data."""
    key = bytes.fromhex(settings.AES_KEY)
    raw = bytes.fromhex(hex_data)
    iv = raw[:16]
    ct = raw[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return unpad(cipher.decrypt(ct), AES.block_size).decode("utf-8")
