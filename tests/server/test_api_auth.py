"""
Integration tests for /api/v1/auth/register and /api/v1/auth/login
via TestClient with fully mocked Firestore.

Covers:
  - Happy path: register new user, login with correct credentials
  - Edge cases: duplicate email (409), wrong password (401), banned user (403),
    device mismatch (403), invalid JWT (401), missing fields (422),
    password too short (422), hardware_id too short (422)
"""
import copy
import pytest
from app.security import hash_password

PREFIX = "/api/v1/auth"


# ═══════════════════════════════════════
# POST /auth/register
# ═══════════════════════════════════════

class TestRegister:

    def test_register_happy_path(self, client, fake_db):
        """Register a brand-new user → 200 with token."""
        resp = client.post(f"{PREFIX}/register", json={
            "email": "newuser@example.com",
            "password": "Secret123",
            "full_name": "New User",
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "newuser@example.com"
        assert body["full_name"] == "New User"
        assert body["credits"] == 0
        assert "token" in body
        assert "user_id" in body

        # Verify user was persisted in fake DB
        users = fake_db.collection("users")._store
        assert len(users) == 1
        uid = body["user_id"]
        assert users[uid]["email"] == "newuser@example.com"
        assert users[uid]["status"] == "active"

    def test_register_creates_audit_log(self, client, fake_db):
        """Registration should create an audit log entry."""
        client.post(f"{PREFIX}/register", json={
            "email": "audit@example.com",
            "password": "Secret123",
            "full_name": "Audit Test",
            "hardware_id": "hw_id_1234567890123456",
        })
        logs = fake_db.collection("audit_logs")._store
        assert len(logs) >= 1
        log_entry = list(logs.values())[0]
        assert log_entry["event_type"] == "USER_REGISTER"

    def test_register_duplicate_email_409(self, client, fake_db):
        """Registering with an existing email → 409."""
        # Seed existing user
        fake_db.collection("users")._store["existing-user"] = {
            "email": "taken@example.com",
            "password_hash": "xxx",
            "full_name": "Existing",
            "status": "active",
        }
        resp = client.post(f"{PREFIX}/register", json={
            "email": "taken@example.com",
            "password": "Secret123",
            "full_name": "Duplicate",
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_email_case_insensitive(self, client, fake_db):
        """Email should be lowercased — registering 'USER@EXAMPLE.COM' then
        'user@example.com' should conflict."""
        client.post(f"{PREFIX}/register", json={
            "email": "USER@EXAMPLE.COM",
            "password": "Secret123",
            "full_name": "Upper",
            "hardware_id": "hw_id_1234567890123456",
        })
        resp = client.post(f"{PREFIX}/register", json={
            "email": "user@example.com",
            "password": "Secret123",
            "full_name": "Lower",
            "hardware_id": "hw_id_9876543210987654",
        })
        assert resp.status_code == 409

    def test_register_password_too_short_422(self, client):
        resp = client.post(f"{PREFIX}/register", json={
            "email": "short@example.com",
            "password": "12345",  # min_length=6
            "full_name": "Short Pass",
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 422

    def test_register_hardware_id_too_short_422(self, client):
        resp = client.post(f"{PREFIX}/register", json={
            "email": "hw@example.com",
            "password": "Secret123",
            "full_name": "Short HW",
            "hardware_id": "short",  # min_length=8
        })
        assert resp.status_code == 422

    def test_register_invalid_email_422(self, client):
        resp = client.post(f"{PREFIX}/register", json={
            "email": "not-an-email",
            "password": "Secret123",
            "full_name": "Bad Email",
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 422

    def test_register_missing_full_name_422(self, client):
        resp = client.post(f"{PREFIX}/register", json={
            "email": "noname@example.com",
            "password": "Secret123",
            "full_name": "",  # min_length=1
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 422

    def test_register_optional_fields(self, client, fake_db):
        """phone and os_type are optional — should default to empty."""
        resp = client.post(f"{PREFIX}/register", json={
            "email": "minimal@example.com",
            "password": "Secret123",
            "full_name": "Minimal",
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 200
        uid = resp.json()["user_id"]
        user = fake_db.collection("users")._store[uid]
        assert user["phone"] == ""
        assert user["metadata"]["os"] == ""

    def test_register_with_phone_and_os(self, client, fake_db):
        resp = client.post(f"{PREFIX}/register", json={
            "email": "full@example.com",
            "password": "Secret123",
            "full_name": "Full Info",
            "hardware_id": "hw_id_1234567890123456",
            "phone": "0812345678",
            "os_type": "macOS",
        })
        assert resp.status_code == 200
        uid = resp.json()["user_id"]
        user = fake_db.collection("users")._store[uid]
        assert user["phone"] == "0812345678"
        assert user["metadata"]["os"] == "macOS"


# ═══════════════════════════════════════
# POST /auth/login
# ═══════════════════════════════════════

class TestLogin:

    def test_login_happy_path(self, client, seed_user):
        """Login with correct credentials → 200 with token."""
        user_id, _, user_data = seed_user
        resp = client.post(f"{PREFIX}/login", json={
            "email": "test@example.com",
            "password": "Password123",
            "hardware_id": "abcdef1234567890abcdef1234567890",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "test@example.com"
        assert body["full_name"] == "Test User"
        assert body["credits"] == 500
        assert "token" in body

    def test_login_wrong_password_401(self, client, seed_user):
        resp = client.post(f"{PREFIX}/login", json={
            "email": "test@example.com",
            "password": "WrongPassword",
            "hardware_id": "abcdef1234567890abcdef1234567890",
        })
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_nonexistent_email_401(self, client, fake_db):
        resp = client.post(f"{PREFIX}/login", json={
            "email": "nobody@example.com",
            "password": "Password123",
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 401

    def test_login_banned_user_403(self, client, fake_db):
        """Banned user should get 403."""
        fake_db.collection("users")._store["banned-user"] = {
            "email": "banned@example.com",
            "password_hash": hash_password("Password123"),
            "full_name": "Banned User",
            "hardware_id": "hw_id_1234567890123456",
            "status": "banned",
            "credits": 0,
        }
        resp = client.post(f"{PREFIX}/login", json={
            "email": "banned@example.com",
            "password": "Password123",
            "hardware_id": "hw_id_1234567890123456",
        })
        assert resp.status_code == 403
        assert "suspended" in resp.json()["detail"].lower()

    def test_login_device_mismatch_403(self, client, seed_user):
        """Login from a different device → 403."""
        resp = client.post(f"{PREFIX}/login", json={
            "email": "test@example.com",
            "password": "Password123",
            "hardware_id": "different_device_id_12345678",
        })
        assert resp.status_code == 403
        assert "different device" in resp.json()["detail"].lower()

    def test_login_creates_audit_on_wrong_password(self, client, seed_user, fake_db):
        """Failed login should create audit log."""
        client.post(f"{PREFIX}/login", json={
            "email": "test@example.com",
            "password": "WrongPassword",
            "hardware_id": "abcdef1234567890abcdef1234567890",
        })
        logs = fake_db.collection("audit_logs")._store
        assert any(
            v.get("event_type") == "LOGIN_FAILED_WRONG_PASSWORD"
            for v in logs.values()
        )

    def test_login_creates_audit_on_device_mismatch(self, client, seed_user, fake_db):
        client.post(f"{PREFIX}/login", json={
            "email": "test@example.com",
            "password": "Password123",
            "hardware_id": "different_device_id_12345678",
        })
        logs = fake_db.collection("audit_logs")._store
        assert any(
            v.get("event_type") == "LOGIN_FAILED_DEVICE_MISMATCH"
            for v in logs.values()
        )

    def test_login_updates_last_login(self, client, seed_user, fake_db):
        """Successful login should update last_login timestamp."""
        user_id, _, _ = seed_user
        old_login = fake_db.collection("users")._store[user_id]["last_login"]
        client.post(f"{PREFIX}/login", json={
            "email": "test@example.com",
            "password": "Password123",
            "hardware_id": "abcdef1234567890abcdef1234567890",
        })
        new_login = fake_db.collection("users")._store[user_id]["last_login"]
        assert new_login != old_login

    def test_login_with_app_version(self, client, seed_user, fake_db):
        user_id, _, _ = seed_user
        client.post(f"{PREFIX}/login", json={
            "email": "test@example.com",
            "password": "Password123",
            "hardware_id": "abcdef1234567890abcdef1234567890",
            "app_version": "2.1.0",
        })
        assert fake_db.collection("users")._store[user_id]["app_version"] == "2.1.0"

    def test_login_email_case_insensitive(self, client, seed_user):
        """Login with uppercase email should still work."""
        resp = client.post(f"{PREFIX}/login", json={
            "email": "TEST@EXAMPLE.COM",
            "password": "Password123",
            "hardware_id": "abcdef1234567890abcdef1234567890",
        })
        assert resp.status_code == 200


# ═══════════════════════════════════════
# JWT Validation (via protected endpoint)
# ═══════════════════════════════════════

class TestJWTValidation:

    def test_no_token_returns_403(self, client, fake_db):
        """Accessing a protected endpoint without a token → 403 (no credentials)."""
        resp = client.get("/api/v1/credit/balance")
        assert resp.status_code == 403

    def test_invalid_token_returns_401(self, client, fake_db):
        resp = client.get("/api/v1/credit/balance", headers={
            "Authorization": "Bearer invalid.jwt.token",
        })
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, fake_db):
        """Manually create an expired token."""
        from jose import jwt as jose_jwt
        from datetime import timedelta
        from app.config import settings
        from datetime import datetime, timezone
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {"sub": "user-001", "email": "x@x.com", "exp": past}
        token = jose_jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        resp = client.get("/api/v1/credit/balance", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401

    def test_token_for_deleted_user_returns_401(self, client, fake_db):
        """Token is valid but user no longer exists → 401."""
        from app.security import create_jwt_token
        token = create_jwt_token("deleted-user-999", "ghost@example.com")
        resp = client.get("/api/v1/credit/balance", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401
        assert "not found" in resp.json()["detail"].lower()

    def test_token_for_banned_user_returns_403(self, client, fake_db):
        """Token is valid but user is banned → 403."""
        from app.security import create_jwt_token
        fake_db.collection("users")._store["banned-uid"] = {
            "email": "banned@test.com",
            "status": "banned",
            "credits": 0,
        }
        token = create_jwt_token("banned-uid", "banned@test.com")
        resp = client.get("/api/v1/credit/balance", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 403
        assert "suspended" in resp.json()["detail"].lower()
