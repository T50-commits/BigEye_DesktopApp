"""
Tests for client/core/auth_manager.py
Covers: has_valid_token, login, register, logout, refresh_balance,
        session persistence, user_name/user_email properties.
"""
import json
import time
import base64
import pytest
from unittest.mock import patch, MagicMock, call

from core.auth_manager import AuthManager


def _make_jwt(payload: dict) -> str:
    """Create a fake JWT with given payload."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(b"fakesig").decode().rstrip("=")
    return f"{header}.{body}.{sig}"


@pytest.fixture
def auth():
    return AuthManager()


# ═══════════════════════════════════════
# has_valid_token
# ═══════════════════════════════════════

class TestHasValidToken:

    def test_no_saved_token(self, auth):
        with patch("core.auth_manager.load_from_keyring", return_value=None):
            assert auth.has_valid_token() is False

    def test_expired_token_clears_session(self, auth):
        expired_token = _make_jwt({"sub": "u1", "exp": time.time() - 3600})
        with patch("core.auth_manager.load_from_keyring", return_value=expired_token), \
             patch("core.auth_manager.delete_from_keyring") as mock_delete:
            assert auth.has_valid_token() is False
            # Should have called clear_session → delete_from_keyring
            assert mock_delete.call_count >= 1

    def test_valid_token_sets_api_client(self, auth):
        valid_token = _make_jwt({"sub": "u1", "email": "test@example.com", "exp": time.time() + 3600})
        with patch("core.auth_manager.load_from_keyring", return_value=valid_token), \
             patch("core.auth_manager.api") as mock_api:
            result = auth.has_valid_token()
            assert result is True
            mock_api.set_token.assert_called_once_with(valid_token)

    def test_valid_token_extracts_email(self, auth):
        valid_token = _make_jwt({"sub": "u1", "email": "user@test.com", "exp": time.time() + 3600})
        with patch("core.auth_manager.load_from_keyring", return_value=valid_token), \
             patch("core.auth_manager.api"):
            auth.has_valid_token()
            assert auth.user_email == "user@test.com"


# ═══════════════════════════════════════
# login
# ═══════════════════════════════════════

class TestLogin:

    def test_login_saves_session(self, auth):
        with patch("core.auth_manager.get_hardware_id", return_value="hw-12345678"), \
             patch("core.auth_manager.api") as mock_api, \
             patch("core.auth_manager.save_to_keyring") as mock_save:
            mock_api.login.return_value = {
                "token": "jwt-abc",
                "user_id": "u1",
                "email": "test@example.com",
                "full_name": "Test User",
                "credits": 100,
            }
            result = auth.login("test@example.com", "password")
            assert result["token"] == "jwt-abc"
            # Should save token and user data to keyring
            assert mock_save.call_count == 2

    def test_login_sets_user_name(self, auth):
        with patch("core.auth_manager.get_hardware_id", return_value="hw-12345678"), \
             patch("core.auth_manager.api") as mock_api, \
             patch("core.auth_manager.save_to_keyring"):
            mock_api.login.return_value = {
                "token": "jwt-abc",
                "full_name": "John Doe",
                "email": "john@test.com",
            }
            auth.login("john@test.com", "pass")
            assert auth._user_name == "John Doe"
            assert auth._user_email == "john@test.com"


# ═══════════════════════════════════════
# register
# ═══════════════════════════════════════

class TestRegister:

    def test_register_saves_session(self, auth):
        with patch("core.auth_manager.get_hardware_id", return_value="hw-12345678"), \
             patch("core.auth_manager.api") as mock_api, \
             patch("core.auth_manager.save_to_keyring") as mock_save:
            mock_api.register.return_value = {
                "token": "jwt-xyz",
                "user_id": "u2",
                "email": "new@example.com",
                "full_name": "New User",
                "credits": 0,
            }
            result = auth.register("new@example.com", "password", "New User", "0812345678")
            assert result["token"] == "jwt-xyz"
            assert mock_save.call_count == 2


# ═══════════════════════════════════════
# logout
# ═══════════════════════════════════════

class TestLogout:

    def test_logout_clears_everything(self, auth):
        auth._user_name = "Test"
        auth._user_email = "test@test.com"
        with patch("core.auth_manager.delete_from_keyring") as mock_delete, \
             patch("core.auth_manager.api") as mock_api:
            auth.logout()
            assert auth._user_name == ""
            assert auth._user_email == ""
            mock_api.clear_token.assert_called_once()
            assert mock_delete.call_count == 2


# ═══════════════════════════════════════
# refresh_balance
# ═══════════════════════════════════════

class TestRefreshBalance:

    def test_refresh_balance_returns_int(self, auth):
        with patch("core.auth_manager.api") as mock_api:
            mock_api.get_balance.return_value = 500
            assert auth.refresh_balance() == 500


# ═══════════════════════════════════════
# user_name property (lazy load from keyring)
# ═══════════════════════════════════════

class TestUserNameProperty:

    def test_returns_cached_name(self, auth):
        auth._user_name = "Cached"
        assert auth.user_name == "Cached"

    def test_loads_from_keyring_when_empty(self, auth):
        user_data = json.dumps({"name": "From Keyring", "email": "kr@test.com"})
        with patch("core.auth_manager.load_from_keyring", return_value=user_data):
            assert auth.user_name == "From Keyring"

    def test_returns_empty_when_keyring_empty(self, auth):
        with patch("core.auth_manager.load_from_keyring", return_value=None):
            assert auth.user_name == ""

    def test_returns_empty_on_invalid_json(self, auth):
        with patch("core.auth_manager.load_from_keyring", return_value="not-json"):
            assert auth.user_name == ""


# ═══════════════════════════════════════
# _save_session
# ═══════════════════════════════════════

class TestSaveSession:

    def test_no_token_does_not_save(self, auth):
        with patch("core.auth_manager.save_to_keyring") as mock_save:
            auth._save_session({"email": "test@test.com"})
            mock_save.assert_not_called()

    def test_saves_token_and_user_data(self, auth):
        with patch("core.auth_manager.save_to_keyring") as mock_save:
            auth._save_session({
                "token": "jwt-123",
                "full_name": "Test",
                "email": "test@test.com",
            })
            assert mock_save.call_count == 2
            # First call: save JWT
            first_call = mock_save.call_args_list[0]
            assert first_call[0][2] == "jwt-123"
