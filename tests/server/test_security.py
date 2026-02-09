"""
Tests for server/app/security.py
Covers: password hashing, JWT create/decode, AES encrypt/decrypt.
"""
import time
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from app.security import (
    hash_password,
    verify_password,
    create_jwt_token,
    decode_jwt_token,
    encrypt_aes,
    decrypt_aes,
    pwd_context,
)
from app.config import settings


# ═══════════════════════════════════════
# Password Hashing
# ═══════════════════════════════════════

class TestPasswordHashing:

    def test_hash_returns_bcrypt_string(self):
        h = hash_password("secret123")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_hash_is_not_plaintext(self):
        h = hash_password("secret123")
        assert h != "secret123"

    def test_verify_correct_password(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_verify_empty_password(self):
        h = hash_password("something")
        assert verify_password("", h) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt uses random salt, so two hashes of the same password differ."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        assert verify_password("same", h1)
        assert verify_password("same", h2)


# ═══════════════════════════════════════
# JWT Tokens
# ═══════════════════════════════════════

class TestJWT:

    def test_create_and_decode_roundtrip(self):
        token = create_jwt_token("user-123", "user@example.com")
        payload = decode_jwt_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "user@example.com"
        assert "exp" in payload
        assert "iat" in payload

    def test_token_contains_correct_claims(self):
        token = create_jwt_token("uid-abc", "abc@test.com")
        payload = decode_jwt_token(token)
        assert payload["sub"] == "uid-abc"
        assert payload["email"] == "abc@test.com"

    def test_token_expiry_is_in_future(self):
        token = create_jwt_token("u1", "u1@test.com")
        payload = decode_jwt_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp > now
        # Should be approximately JWT_EXPIRE_HOURS in the future
        expected = now + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        delta = abs((exp - expected).total_seconds())
        assert delta < 5  # within 5 seconds tolerance

    def test_decode_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_jwt_token("not.a.valid.token")

    def test_decode_tampered_token_raises(self):
        token = create_jwt_token("u1", "u1@test.com")
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_jwt_token(tampered)

    def test_decode_expired_token_raises(self):
        """Manually create an already-expired token."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {"sub": "u1", "email": "u1@test.com", "exp": past, "iat": past}
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(JWTError):
            decode_jwt_token(token)

    def test_decode_wrong_secret_raises(self):
        payload = {
            "sub": "u1", "email": "u1@test.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        with pytest.raises(JWTError):
            decode_jwt_token(token)


# ═══════════════════════════════════════
# AES-256 Encryption
# ═══════════════════════════════════════

class TestAES:

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "Hello, BigEye Pro!"
        encrypted = encrypt_aes(plaintext)
        decrypted = decrypt_aes(encrypted)
        assert decrypted == plaintext

    def test_encrypt_produces_hex_string(self):
        encrypted = encrypt_aes("test")
        # Should be valid hex
        int(encrypted, 16)

    def test_encrypt_different_each_time(self):
        """AES-CBC uses random IV, so same plaintext → different ciphertext."""
        e1 = encrypt_aes("same text")
        e2 = encrypt_aes("same text")
        assert e1 != e2

    def test_decrypt_with_wrong_data_raises(self):
        with pytest.raises(Exception):
            decrypt_aes("00" * 15)  # too short

    def test_roundtrip_unicode(self):
        text = "สวัสดี BigEye Pro 🎉"
        encrypted = encrypt_aes(text)
        assert decrypt_aes(encrypted) == text

    def test_roundtrip_empty_string(self):
        encrypted = encrypt_aes("")
        assert decrypt_aes(encrypted) == ""

    def test_roundtrip_long_text(self):
        text = "A" * 10000
        encrypted = encrypt_aes(text)
        assert decrypt_aes(encrypted) == text

    def test_ciphertext_length_is_multiple_of_block(self):
        encrypted = encrypt_aes("test data")
        raw = bytes.fromhex(encrypted)
        # IV is 16 bytes, ciphertext should be multiple of 16
        ciphertext = raw[16:]
        assert len(ciphertext) % 16 == 0
