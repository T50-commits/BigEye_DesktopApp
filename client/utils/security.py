"""
BigEye Pro — Security Module (Task B-02)
Hardware ID generation, AES encryption/decryption, keyring helpers.
"""
import hashlib
import platform
import uuid
import base64
import logging
import json
import time

logger = logging.getLogger("bigeye")


# ═══════════════════════════════════════
# Hardware ID
# ═══════════════════════════════════════

def get_hardware_id() -> str:
    """
    Generate a deterministic hardware ID for device binding.
    Combines hostname, machine architecture, and MAC address.
    Returns a 32-character hex string (SHA-256 truncated).
    """
    try:
        node = platform.node() or "unknown"
        machine = platform.machine() or "unknown"
        mac = uuid.getnode()
        # uuid.getnode() returns a random value if MAC can't be determined;
        # bit 0 of the first octet is set in that case
        if (mac >> 40) & 1:
            mac_str = "no-mac"
        else:
            mac_str = str(mac)
        info = f"{node}-{machine}-{mac_str}"
        return hashlib.sha256(info.encode("utf-8")).hexdigest()[:32]
    except Exception as e:
        logger.warning(f"Hardware ID generation fallback: {e}")
        fallback = f"{platform.node()}-{uuid.getnode()}"
        return hashlib.sha256(fallback.encode("utf-8")).hexdigest()[:32]


# ═══════════════════════════════════════
# AES Encryption / Decryption
# ═══════════════════════════════════════

def decrypt_aes(encrypted_data: str, key_hex: str) -> str:
    """
    Decrypt AES-CBC encrypted data.
    Supports both hex and base64 encoded input: hex( IV + ciphertext ) or base64( IV + ciphertext ).
    Returns decrypted plaintext string.
    Raises ValueError on any decryption failure.
    """
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

    try:
        key = bytes.fromhex(key_hex)
        # Auto-detect format: hex strings contain only [0-9a-fA-F]
        try:
            raw = bytes.fromhex(encrypted_data)
        except ValueError:
            raw = base64.b64decode(encrypted_data)
        if len(raw) < 32:
            raise ValueError("Encrypted data too short (must be at least IV + 1 block)")
        iv = raw[:16]
        ciphertext = raw[16:]
        if len(ciphertext) % 16 != 0:
            raise ValueError("Ciphertext length is not a multiple of block size")
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return plaintext.decode("utf-8")
    except (ValueError, KeyError) as e:
        raise ValueError(f"AES decryption failed: {e}") from e


def encrypt_aes(plaintext: str, key_hex: str) -> str:
    """
    Encrypt plaintext using AES-CBC.
    Returns base64( IV_16bytes + ciphertext_PKCS7 ).
    Used for testing / local encryption if needed.
    """
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    import os as _os

    key = bytes.fromhex(key_hex)
    iv = _os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext.encode("utf-8"), AES.block_size)
    ciphertext = cipher.encrypt(padded)
    return base64.b64encode(iv + ciphertext).decode("ascii")


# ═══════════════════════════════════════
# Keyring Helpers
# ═══════════════════════════════════════

def save_to_keyring(service: str, key: str, value: str) -> bool:
    """
    Save a value to the system keyring.
    Returns True on success, False on failure.
    """
    try:
        import keyring
        keyring.set_password(service, key, value)
        return True
    except Exception as e:
        logger.error(f"Keyring save failed [{service}/{key}]: {e}")
        return False


def load_from_keyring(service: str, key: str) -> str | None:
    """
    Load a value from the system keyring.
    Returns the stored string or None if not found / error.
    """
    try:
        import keyring
        return keyring.get_password(service, key)
    except Exception as e:
        logger.error(f"Keyring load failed [{service}/{key}]: {e}")
        return None


def delete_from_keyring(service: str, key: str) -> bool:
    """
    Delete a value from the system keyring.
    Returns True on success, False on failure (including not found).
    """
    try:
        import keyring
        keyring.delete_password(service, key)
        return True
    except Exception as e:
        # PasswordDeleteError = key not found — not a real error
        logger.debug(f"Keyring delete [{service}/{key}]: {e}")
        return False


# ═══════════════════════════════════════
# JWT Token Helpers
# ═══════════════════════════════════════

def decode_jwt_payload(token: str) -> dict | None:
    """
    Decode JWT payload without verification (for reading claims only).
    Returns the payload dict or None on failure.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # Add padding for base64
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a JWT token is expired.
    Returns True if expired or unparseable, False if still valid.
    """
    payload = decode_jwt_payload(token)
    if not payload:
        return True
    exp = payload.get("exp")
    if not exp:
        return True
    return float(exp) < time.time()
