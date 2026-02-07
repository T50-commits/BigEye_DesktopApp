"""
BigEye Pro — Auth Manager
Handles JWT token management, login/register, and session persistence.
"""
import json
from core.config import KEYRING_SERVICE, KEYRING_JWT, KEYRING_USER
from core.api_client import api
from utils.security import (
    get_hardware_id, save_to_keyring, load_from_keyring, delete_from_keyring,
    decode_jwt_payload, is_token_expired,
)


class AuthManager:
    """Manages authentication state and token persistence."""

    def __init__(self):
        self._user_name = ""
        self._user_email = ""

    def has_valid_token(self) -> bool:
        """Check if a saved JWT token exists and is not expired."""
        token = load_from_keyring(KEYRING_SERVICE, KEYRING_JWT)
        if not token:
            return False

        if is_token_expired(token):
            self.clear_session()
            return False

        # Token is valid — set it on the API client
        api.set_token(token)
        payload = decode_jwt_payload(token)
        if payload:
            self._user_name = payload.get("name", "")
            self._user_email = payload.get("email", "")
        return True

    def login(self, email: str, password: str) -> dict:
        """Login and save session."""
        hw_id = get_hardware_id()
        result = api.login(email, password, hw_id)
        self._save_session(result)
        return result

    def register(self, email: str, password: str, name: str, phone: str) -> dict:
        """Register and save session."""
        hw_id = get_hardware_id()
        result = api.register(email, password, name, phone, hw_id)
        self._save_session(result)
        return result

    def logout(self):
        """Clear session and API token."""
        self.clear_session()
        api.clear_token()

    def refresh_balance(self) -> int:
        """Get current credit balance from server."""
        return api.get_balance()

    def _save_session(self, result: dict):
        """Save JWT token and user info to keyring."""
        token = result.get("token", "")
        if token:
            save_to_keyring(KEYRING_SERVICE, KEYRING_JWT, token)
            self._user_name = result.get("name", result.get("user", {}).get("name", ""))
            self._user_email = result.get("email", result.get("user", {}).get("email", ""))
            user_data = json.dumps({"name": self._user_name, "email": self._user_email})
            save_to_keyring(KEYRING_SERVICE, KEYRING_USER, user_data)

    def clear_session(self):
        """Remove saved token and user data."""
        delete_from_keyring(KEYRING_SERVICE, KEYRING_JWT)
        delete_from_keyring(KEYRING_SERVICE, KEYRING_USER)
        self._user_name = ""
        self._user_email = ""

    @property
    def user_name(self) -> str:
        if not self._user_name:
            raw = load_from_keyring(KEYRING_SERVICE, KEYRING_USER)
            if raw:
                try:
                    data = json.loads(raw)
                    self._user_name = data.get("name", "")
                except Exception:
                    pass
        return self._user_name

    @property
    def user_email(self) -> str:
        return self._user_email
