"""
Tests for client/utils/security.py
Covers: get_hardware_id, AES encrypt/decrypt, keyring helpers, JWT decode/expiry.
"""
import time
import base64
import json
import pytest
from unittest.mock import patch, MagicMock

from utils.security import (
    get_hardware_id,
    decrypt_aes,
    encrypt_aes,
    save_to_keyring,
    load_from_keyring,
    delete_from_keyring,
    decode_jwt_payload,
    is_token_expired,
)


# ═══════════════════════════════════════
# Hardware ID
# ═══════════════════════════════════════

class TestGetHardwareId:

    def test_returns_32_char_hex(self):
        hw_id = get_hardware_id()
        assert len(hw_id) == 32
        int(hw_id, 16)  # valid hex

    def test_deterministic(self):
        """Same machine should produce the same ID."""
        id1 = get_hardware_id()
        id2 = get_hardware_id()
        assert id1 == id2

    def test_fallback_on_exception(self):
        """Even if platform.machine() fails, should still return a valid ID."""
        with patch("utils.security.platform.machine", side_effect=Exception("fail")):
            # The function has a fallback path
            hw_id = get_hardware_id()
            assert len(hw_id) == 32


# ═══════════════════════════════════════
# AES Encryption / Decryption (Client-side)
# ═══════════════════════════════════════

# Use a known 256-bit key (64 hex chars)
TEST_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


class TestClientAES:

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "Hello, BigEye Pro!"
        encrypted = encrypt_aes(plaintext, TEST_KEY)
        decrypted = decrypt_aes(encrypted, TEST_KEY)
        assert decrypted == plaintext

    def test_encrypt_produces_base64(self):
        encrypted = encrypt_aes("test", TEST_KEY)
        # Should be valid base64
        base64.b64decode(encrypted)

    def test_decrypt_hex_format(self):
        """Client decrypt_aes supports hex input (from server encrypt_aes)."""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        key = bytes.fromhex(TEST_KEY)
        cipher = AES.new(key, AES.MODE_CBC)
        ct = cipher.encrypt(pad(b"hello world", AES.block_size))
        hex_data = (cipher.iv + ct).hex()
        result = decrypt_aes(hex_data, TEST_KEY)
        assert result == "hello world"

    def test_decrypt_base64_format(self):
        """Client decrypt_aes supports base64 input."""
        encrypted = encrypt_aes("test data", TEST_KEY)
        # encrypt_aes returns base64
        result = decrypt_aes(encrypted, TEST_KEY)
        assert result == "test data"

    def test_decrypt_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            decrypt_aes("00" * 15, TEST_KEY)  # 15 bytes < 32 minimum

    def test_decrypt_bad_ciphertext_length_raises(self):
        """Ciphertext not multiple of block size should raise."""
        # 16 bytes IV + 17 bytes (not multiple of 16)
        bad_data = ("00" * 16) + ("00" * 17)
        with pytest.raises(ValueError, match="not a multiple"):
            decrypt_aes(bad_data, TEST_KEY)

    def test_roundtrip_unicode(self):
        text = "สวัสดี BigEye Pro 🎉"
        encrypted = encrypt_aes(text, TEST_KEY)
        assert decrypt_aes(encrypted, TEST_KEY) == text

    def test_roundtrip_empty_string(self):
        encrypted = encrypt_aes("", TEST_KEY)
        assert decrypt_aes(encrypted, TEST_KEY) == ""

    def test_different_ciphertext_each_time(self):
        """Random IV means different ciphertext for same plaintext."""
        e1 = encrypt_aes("same", TEST_KEY)
        e2 = encrypt_aes("same", TEST_KEY)
        assert e1 != e2

    def test_cross_compatibility_server_client(self):
        """Server encrypt (hex) → Client decrypt should work."""
        from app.security import encrypt_aes as server_encrypt
        # Server uses settings.AES_KEY which is all zeros
        from app.config import settings
        server_encrypted = server_encrypt("cross-compat test")
        # Client decrypt with same key
        result = decrypt_aes(server_encrypted, settings.AES_KEY)
        assert result == "cross-compat test"


# ═══════════════════════════════════════
# Keyring Helpers
# ═══════════════════════════════════════

class TestKeyringHelpers:

    @patch("keyring.set_password")
    def test_save_to_keyring_success(self, mock_set):
        assert save_to_keyring("svc", "key", "value") is True
        mock_set.assert_called_once_with("svc", "key", "value")

    @patch("keyring.set_password", side_effect=Exception("keyring error"))
    def test_save_to_keyring_failure(self, mock_set):
        assert save_to_keyring("svc", "key", "value") is False

    @patch("keyring.get_password", return_value="stored_value")
    def test_load_from_keyring_success(self, mock_get):
        assert load_from_keyring("svc", "key") == "stored_value"

    @patch("keyring.get_password", return_value=None)
    def test_load_from_keyring_not_found(self, mock_get):
        assert load_from_keyring("svc", "key") is None

    @patch("keyring.get_password", side_effect=Exception("keyring error"))
    def test_load_from_keyring_failure(self, mock_get):
        assert load_from_keyring("svc", "key") is None

    @patch("keyring.delete_password")
    def test_delete_from_keyring_success(self, mock_del):
        assert delete_from_keyring("svc", "key") is True
        mock_del.assert_called_once_with("svc", "key")

    @patch("keyring.delete_password", side_effect=Exception("not found"))
    def test_delete_from_keyring_failure(self, mock_del):
        assert delete_from_keyring("svc", "key") is False


# ═══════════════════════════════════════
# JWT Token Helpers
# ═══════════════════════════════════════

def _make_jwt(payload: dict) -> str:
    """Create a fake JWT (header.payload.signature) with given payload."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(b"fakesig").decode().rstrip("=")
    return f"{header}.{body}.{sig}"


class TestDecodeJwtPayload:

    def test_decode_valid_jwt(self):
        token = _make_jwt({"sub": "user-001", "email": "test@example.com"})
        payload = decode_jwt_payload(token)
        assert payload is not None
        assert payload["sub"] == "user-001"
        assert payload["email"] == "test@example.com"

    def test_decode_invalid_format(self):
        assert decode_jwt_payload("not-a-jwt") is None
        assert decode_jwt_payload("only.two") is None
        assert decode_jwt_payload("") is None

    def test_decode_invalid_base64(self):
        assert decode_jwt_payload("a.!!!invalid!!!.c") is None

    def test_decode_with_padding(self):
        """JWT payloads often lack base64 padding — should still work."""
        payload = {"sub": "u1", "name": "Test"}
        token = _make_jwt(payload)
        result = decode_jwt_payload(token)
        assert result["sub"] == "u1"


class TestIsTokenExpired:

    def test_valid_token_not_expired(self):
        future_exp = time.time() + 3600
        token = _make_jwt({"sub": "u1", "exp": future_exp})
        assert is_token_expired(token) is False

    def test_expired_token(self):
        past_exp = time.time() - 3600
        token = _make_jwt({"sub": "u1", "exp": past_exp})
        assert is_token_expired(token) is True

    def test_no_exp_claim(self):
        token = _make_jwt({"sub": "u1"})
        assert is_token_expired(token) is True

    def test_invalid_token(self):
        assert is_token_expired("garbage") is True

    def test_empty_token(self):
        assert is_token_expired("") is True
