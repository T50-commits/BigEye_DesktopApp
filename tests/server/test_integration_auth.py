"""
Integration Test — User Authentication & Balance Check Flow

Simulates a COMPLETE real user session in a SINGLE test function:

    1. Register  → POST /auth/register    → 200 + JWT + user_id
    2. Login     → POST /auth/login       → 200 + JWT (same user)
    3. Extract   → parse access_token (JWT) from login response
    4. Protected → GET  /credit/balance   → 200 + credits using extracted token
    5. Assert    → initial balance == 0 (no sign-up bonus)

Uses:
    - FastAPI TestClient (synchronous, no real server)
    - In-memory Firestore mock from conftest.py (no real DB writes)
    - Real JWT creation + decoding via app.security (dependency injection verified)

The test proves that:
    ✓ Registration creates a user in Firestore and returns a valid JWT
    ✓ Login finds the user by email, verifies bcrypt password, checks hardware_id
    ✓ The JWT from login works as a Bearer token on protected endpoints
    ✓ get_current_user dependency correctly decodes the JWT and fetches the user
    ✓ /credit/balance returns the correct initial balance
"""
import pytest


PREFIX = "/api/v1"


class TestAuthAndBalanceFlow:
    """
    Full integration flow: register → login → token → balance.
    Executed as a SINGLE test function to simulate a real user session.
    """

    def test_register_login_and_check_balance(self, client, fake_db, seed_app_settings):
        """
        End-to-end: brand-new user registers, logs in, and checks their balance.
        """
        # ── Test Data ──
        EMAIL = "newuser@bigeyepro.com"
        PASSWORD = "SuperSecret_42!"
        FULL_NAME = "Integration Test User"
        HARDWARE_ID = "hw_integration_test_12345678"

        # ════════════════════════════════════════════
        # Step 1 — REGISTER
        # ════════════════════════════════════════════
        register_resp = client.post(f"{PREFIX}/auth/register", json={
            "email": EMAIL,
            "password": PASSWORD,
            "full_name": FULL_NAME,
            "hardware_id": HARDWARE_ID,
        })

        # The server returns 200 (FastAPI default for response_model)
        assert register_resp.status_code == 200, \
            f"Register failed: {register_resp.status_code} — {register_resp.json()}"

        register_data = register_resp.json()

        # Verify response shape
        assert "token" in register_data, "Register response must contain 'token'"
        assert "user_id" in register_data, "Register response must contain 'user_id'"
        assert register_data["email"] == EMAIL.lower()
        assert register_data["full_name"] == FULL_NAME
        assert register_data["credits"] == 0, "New user should start with 0 credits"

        register_token = register_data["token"]
        user_id = register_data["user_id"]

        # Verify user was persisted in the (mocked) Firestore
        users_store = fake_db.collection("users")._store
        assert user_id in users_store, "User doc must exist in Firestore"
        db_user = users_store[user_id]
        assert db_user["email"] == EMAIL.lower()
        assert db_user["status"] == "active"
        assert db_user["credits"] == 0

        # ════════════════════════════════════════════
        # Step 2 — LOGIN (same credentials)
        # ════════════════════════════════════════════
        login_resp = client.post(f"{PREFIX}/auth/login", json={
            "email": EMAIL,
            "password": PASSWORD,
            "hardware_id": HARDWARE_ID,
        })

        assert login_resp.status_code == 200, \
            f"Login failed: {login_resp.status_code} — {login_resp.json()}"

        login_data = login_resp.json()

        # Verify response shape
        assert "token" in login_data, "Login response must contain 'token'"
        assert login_data["email"] == EMAIL.lower()
        assert login_data["full_name"] == FULL_NAME
        assert login_data["credits"] == 0
        assert login_data["user_id"] == user_id, "Login must return the same user_id"

        # ════════════════════════════════════════════
        # Step 3 — EXTRACT TOKEN
        # ════════════════════════════════════════════
        access_token = login_data["token"]

        # Both tokens must be valid non-empty JWT strings.
        # Note: they may be identical if both calls land in the same second
        # (JWT iat/exp have 1-second granularity), which is fine.
        assert access_token, "Token must not be empty"
        assert register_token, "Register token must not be empty"

        # Verify the JWT can be decoded and contains correct claims
        from app.security import decode_jwt_token
        claims = decode_jwt_token(access_token)
        assert claims["sub"] == user_id
        assert claims["email"] == EMAIL.lower()

        # ════════════════════════════════════════════
        # Step 4 — PROTECTED ACCESS: GET /credit/balance
        # ════════════════════════════════════════════
        auth_header = {"Authorization": f"Bearer {access_token}"}

        balance_resp = client.get(f"{PREFIX}/credit/balance", headers=auth_header)

        assert balance_resp.status_code == 200, \
            f"Balance check failed: {balance_resp.status_code} — {balance_resp.json()}"

        balance_data = balance_resp.json()

        # ════════════════════════════════════════════
        # Step 5 — ASSERTIONS
        # ════════════════════════════════════════════

        # Balance should be 0 for a brand-new user (no sign-up bonus)
        assert balance_data["credits"] == 0, \
            f"Initial balance should be 0, got {balance_data['credits']}"

        # Exchange rate and credit_rates should be present (from seed_app_settings)
        assert "exchange_rate" in balance_data
        assert "credit_rates" in balance_data
        assert balance_data["exchange_rate"] == 4  # from seed_app_settings

        # active_promos should be a list (possibly empty)
        assert isinstance(balance_data["active_promos"], list)

        # ── Verify the register token ALSO works (both JWTs are valid) ──
        register_header = {"Authorization": f"Bearer {register_token}"}
        balance2 = client.get(f"{PREFIX}/credit/balance", headers=register_header)
        assert balance2.status_code == 200
        assert balance2.json()["credits"] == 0

    def test_register_login_wrong_password_then_correct(self, client, fake_db, seed_app_settings):
        """
        Extended flow: register → login with WRONG password (401) →
        login with CORRECT password (200) → balance check.
        Verifies that a failed login does not break the session.
        """
        EMAIL = "wrongpass@bigeyepro.com"
        PASSWORD = "CorrectPassword_99"
        HW_ID = "hw_wrongpass_test_123456789"

        # Register
        r = client.post(f"{PREFIX}/auth/register", json={
            "email": EMAIL, "password": PASSWORD,
            "full_name": "Wrong Pass Test", "hardware_id": HW_ID,
        })
        assert r.status_code == 200

        # Login with WRONG password → 401
        bad_login = client.post(f"{PREFIX}/auth/login", json={
            "email": EMAIL, "password": "TotallyWrong",
            "hardware_id": HW_ID,
        })
        assert bad_login.status_code == 401
        assert "invalid" in bad_login.json()["detail"].lower()

        # Audit log should record the failed attempt
        audit_logs = fake_db.collection("audit_logs")._store
        failed_events = [
            v for v in audit_logs.values()
            if v.get("event_type") == "LOGIN_FAILED_WRONG_PASSWORD"
        ]
        assert len(failed_events) >= 1

        # Login with CORRECT password → 200
        good_login = client.post(f"{PREFIX}/auth/login", json={
            "email": EMAIL, "password": PASSWORD,
            "hardware_id": HW_ID,
        })
        assert good_login.status_code == 200
        token = good_login.json()["token"]

        # Balance check with valid token
        balance = client.get(f"{PREFIX}/credit/balance",
                             headers={"Authorization": f"Bearer {token}"})
        assert balance.status_code == 200
        assert balance.json()["credits"] == 0

    def test_register_login_from_different_device_blocked(self, client, fake_db, seed_app_settings):
        """
        Register on device A → login from device B → 403 device mismatch.
        Then login from device A → 200 success → balance check works.
        """
        EMAIL = "device@bigeyepro.com"
        PASSWORD = "DeviceTest_77"
        DEVICE_A = "device_a_hardware_id_1234567"
        DEVICE_B = "device_b_hardware_id_9876543"

        # Register on device A
        r = client.post(f"{PREFIX}/auth/register", json={
            "email": EMAIL, "password": PASSWORD,
            "full_name": "Device Test", "hardware_id": DEVICE_A,
        })
        assert r.status_code == 200

        # Login from device B → 403
        bad = client.post(f"{PREFIX}/auth/login", json={
            "email": EMAIL, "password": PASSWORD,
            "hardware_id": DEVICE_B,
        })
        assert bad.status_code == 403
        assert "different device" in bad.json()["detail"].lower()

        # Login from device A → 200
        good = client.post(f"{PREFIX}/auth/login", json={
            "email": EMAIL, "password": PASSWORD,
            "hardware_id": DEVICE_A,
        })
        assert good.status_code == 200
        token = good.json()["token"]

        # Balance works
        balance = client.get(f"{PREFIX}/credit/balance",
                             headers={"Authorization": f"Bearer {token}"})
        assert balance.status_code == 200
        assert balance.json()["credits"] == 0

    def test_duplicate_register_blocked(self, client, fake_db, seed_app_settings):
        """
        Register once → register again with same email → 409 conflict.
        Original account still works.
        """
        EMAIL = "duplicate@bigeyepro.com"
        PASSWORD = "DupTest_55"
        HW_ID = "hw_dup_test_1234567890123"

        # First register → 200
        r1 = client.post(f"{PREFIX}/auth/register", json={
            "email": EMAIL, "password": PASSWORD,
            "full_name": "Original", "hardware_id": HW_ID,
        })
        assert r1.status_code == 200

        # Second register → 409
        r2 = client.post(f"{PREFIX}/auth/register", json={
            "email": EMAIL, "password": "AnotherPass_99",
            "full_name": "Duplicate", "hardware_id": "hw_another_device_1234567",
        })
        assert r2.status_code == 409
        assert "already registered" in r2.json()["detail"].lower()

        # Original account still works
        login = client.post(f"{PREFIX}/auth/login", json={
            "email": EMAIL, "password": PASSWORD,
            "hardware_id": HW_ID,
        })
        assert login.status_code == 200
        token = login.json()["token"]

        balance = client.get(f"{PREFIX}/credit/balance",
                             headers={"Authorization": f"Bearer {token}"})
        assert balance.status_code == 200

    def test_invalid_token_rejected_on_balance(self, client, fake_db, seed_app_settings):
        """
        A fabricated/invalid JWT should be rejected by the protected endpoint.
        """
        resp = client.get(f"{PREFIX}/credit/balance",
                          headers={"Authorization": "Bearer fake.invalid.jwt"})
        assert resp.status_code == 401

    def test_no_token_rejected_on_balance(self, client, fake_db, seed_app_settings):
        """
        No Authorization header → 403 (FastAPI's HTTPBearer returns 403 when missing).
        """
        resp = client.get(f"{PREFIX}/credit/balance")
        assert resp.status_code == 403
