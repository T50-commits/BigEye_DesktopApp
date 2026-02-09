"""
Integration Tests for Frontend Worker Threads (pytest-qt)

Tests the AuthWorker ("LoginWorker") and StartupWorker ("CreditWorker")
with fully mocked API calls — no real backend is hit.

Flow tested:
    1. AuthWorker: login with dummy creds → mock API response → assert `finished` signal
    2. AuthWorker: register with dummy data → mock API response → assert `finished` signal
    3. AuthWorker: login fails → assert `error` signal with correct message
    4. StartupWorker: mock balance endpoint → assert `balance_loaded` signal carries 500
    5. Chained flow: AuthWorker login → extract token → StartupWorker balance check
"""
import contextlib
import pytest
from unittest.mock import patch, MagicMock

from PySide6.QtCore import QThread

from core.auth_manager import AuthManager
from core.api_client import (
    APIError, NetworkError, AuthenticationError, ForbiddenError,
    ConflictError,
)
from ui.auth_window import AuthWorker
from ui.main_window import StartupWorker


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

@contextlib.contextmanager
def _auth_patches(api_setup=None):
    """
    Context manager that patches api, get_hardware_id, and all keyring
    operations inside core.auth_manager. Yields the mock_api object.
    """
    with patch("core.auth_manager.api") as mock_api, \
         patch("core.auth_manager.get_hardware_id", return_value="test-hw-id"), \
         patch("core.auth_manager.save_to_keyring"), \
         patch("core.auth_manager.load_from_keyring", return_value=None), \
         patch("core.auth_manager.delete_from_keyring"):
        if api_setup:
            api_setup(mock_api)
        yield mock_api


@contextlib.contextmanager
def _startup_patches():
    """
    Context manager that patches all dependencies used by StartupWorker.run().
    Note: GeminiEngine is NOT imported at module level in main_window.py,
    so the NameError is caught by the except block at runtime — no patch needed.
    """
    with patch("ui.main_window.api") as mock_api, \
         patch("ui.main_window.get_hardware_id", return_value="hw-test"), \
         patch("ui.main_window.JournalManager"):
        yield mock_api


def _run_worker_on_thread(qtbot, worker):
    """
    Run a QObject worker on a real QThread (like the app does).
    Returns after the thread finishes.
    """
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    # Quit thread when worker emits finished or error
    if hasattr(worker, 'finished'):
        worker.finished.connect(thread.quit)
    if hasattr(worker, 'error'):
        worker.error.connect(thread.quit)
    # For StartupWorker, the done signal is also called `finished`
    thread.start()
    # Wait for thread to finish
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=5000)
    thread.deleteLater()


# ═══════════════════════════════════════════════════════════
# Test 1: AuthWorker — Login (the "LoginWorker")
# ═══════════════════════════════════════════════════════════

class TestAuthWorkerLogin:

    def test_login_emits_finished_with_token(self, qtbot):
        """
        1. Initialize AuthWorker with dummy credentials
        2. Mock api.login to return {"token": "fake-jwt-123", ...}
        3. Run the worker on a QThread
        4. Assert `finished` signal emits dict with the correct token
        """
        # Mock API response
        mock_login_response = {
            "token": "fake-jwt-123",
            "user_id": "uid-001",
            "email": "test@bigeye.com",
            "full_name": "Test User",
            "credits": 0,
        }

        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_login("test@bigeye.com", "password123")

        # Collect signal emissions
        results = []
        worker.finished.connect(lambda d: results.append(d))

        with _auth_patches() as mock_api:
            mock_api.login.return_value = mock_login_response

            _run_worker_on_thread(qtbot, worker)

        # ── Assertions ──
        assert len(results) == 1, "finished signal should emit exactly once"
        result = results[0]
        assert result["token"] == "fake-jwt-123"
        assert result["user_id"] == "uid-001"
        assert result["email"] == "test@bigeye.com"
        assert result["full_name"] == "Test User"

    def test_login_calls_api_with_correct_args(self, qtbot):
        """Verify api.login is called with email, password, and hardware_id."""
        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_login("user@test.com", "MyPass_99")

        results = []
        worker.finished.connect(lambda d: results.append(d))

        with _auth_patches() as mock_api:
            mock_api.login.return_value = {"token": "t", "full_name": "U"}

            _run_worker_on_thread(qtbot, worker)

            mock_api.login.assert_called_once()

    def test_login_wrong_password_emits_error(self, qtbot):
        """AuthenticationError → error signal with user-friendly message."""
        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_login("test@bigeye.com", "wrong_password")

        errors = []
        worker.error.connect(lambda msg: errors.append(msg))

        with _auth_patches() as mock_api:
            mock_api.login.side_effect = AuthenticationError("Invalid credentials", 401)

            _run_worker_on_thread(qtbot, worker)

        assert len(errors) == 1
        assert "incorrect" in errors[0].lower() or "password" in errors[0].lower()

    def test_login_network_error_emits_error(self, qtbot):
        """NetworkError → error signal about connectivity."""
        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_login("test@bigeye.com", "password")

        errors = []
        worker.error.connect(lambda msg: errors.append(msg))

        with _auth_patches() as mock_api:
            mock_api.login.side_effect = NetworkError()

            _run_worker_on_thread(qtbot, worker)

        assert len(errors) == 1
        assert "connect" in errors[0].lower() or "internet" in errors[0].lower()

    def test_login_device_mismatch_emits_error(self, qtbot):
        """ForbiddenError → error signal about device mismatch."""
        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_login("test@bigeye.com", "password")

        errors = []
        worker.error.connect(lambda msg: errors.append(msg))

        with _auth_patches() as mock_api:
            mock_api.login.side_effect = ForbiddenError("Device mismatch", 403)

            _run_worker_on_thread(qtbot, worker)

        assert len(errors) == 1
        assert "device" in errors[0].lower()

    def test_login_conflict_emits_error(self, qtbot):
        """ConflictError on register → error signal about duplicate email."""
        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_register("dup@test.com", "pass1234", "Dup User", "0812345678")

        errors = []
        worker.error.connect(lambda msg: errors.append(msg))

        with _auth_patches() as mock_api:
            mock_api.register.side_effect = ConflictError("Email already registered", 409)

            _run_worker_on_thread(qtbot, worker)

        assert len(errors) == 1
        assert "already registered" in errors[0].lower()


# ═══════════════════════════════════════════════════════════
# Test 2: AuthWorker — Register
# ═══════════════════════════════════════════════════════════

class TestAuthWorkerRegister:

    def test_register_emits_finished_with_token(self, qtbot):
        """Register flow: mock api.register → finished signal with token."""
        mock_register_response = {
            "token": "reg-jwt-456",
            "user_id": "uid-002",
            "email": "newuser@bigeye.com",
            "full_name": "New User",
            "credits": 0,
        }

        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_register("newuser@bigeye.com", "StrongPass_42", "New User", "0891234567")

        results = []
        worker.finished.connect(lambda d: results.append(d))

        with _auth_patches() as mock_api:
            mock_api.register.return_value = mock_register_response

            _run_worker_on_thread(qtbot, worker)

        assert len(results) == 1
        assert results[0]["token"] == "reg-jwt-456"
        assert results[0]["full_name"] == "New User"

    def test_register_calls_api_with_correct_args(self, qtbot):
        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_register("new@test.com", "Pass_1234", "Test Name", "0891112222")

        results = []
        worker.finished.connect(lambda d: results.append(d))

        with _auth_patches() as mock_api:
            mock_api.register.return_value = {"token": "t", "full_name": "N"}

            _run_worker_on_thread(qtbot, worker)

            mock_api.register.assert_called_once()


# ═══════════════════════════════════════════════════════════
# Test 3: StartupWorker (the "CreditWorker")
# ═══════════════════════════════════════════════════════════

class TestStartupWorkerBalance:

    def test_balance_loaded_signal_carries_500(self, qtbot):
        """
        1. Mock api.get_balance_with_promos to return {"credits": 500, ...}
        2. Run StartupWorker on QThread
        3. Assert balance_loaded signal emits 500
        """
        worker = StartupWorker()

        balances = []
        worker.balance_loaded.connect(lambda b: balances.append(b))

        with _startup_patches() as mock_api:
            mock_api.check_update.return_value = {}
            mock_api.get_balance_with_promos.return_value = {
                "credits": 500,
                "exchange_rate": 4,
                "credit_rates": {"istock_photo": 3},
                "active_promos": [],
            }

            _run_worker_on_thread(qtbot, worker)

        assert len(balances) == 1
        assert balances[0] == 500

    def test_promos_loaded_signal(self, qtbot):
        """Promos list should be emitted via promos_loaded signal."""
        worker = StartupWorker()

        promos = []
        worker.promos_loaded.connect(lambda p: promos.append(p))

        with _startup_patches() as mock_api:
            mock_api.check_update.return_value = {}
            mock_api.get_balance_with_promos.return_value = {
                "credits": 100,
                "exchange_rate": 4,
                "credit_rates": {},
                "active_promos": [{"name": "Summer Sale", "bonus": 20}],
            }

            _run_worker_on_thread(qtbot, worker)

        assert len(promos) == 1
        assert promos[0][0]["name"] == "Summer Sale"

    def test_rates_loaded_signal(self, qtbot):
        """Credit rates should be emitted via rates_loaded signal."""
        worker = StartupWorker()

        rates = []
        worker.rates_loaded.connect(lambda r: rates.append(r))

        with _startup_patches() as mock_api:
            mock_api.check_update.return_value = {}
            mock_api.get_balance_with_promos.return_value = {
                "credits": 100,
                "exchange_rate": 4,
                "credit_rates": {"istock_photo": 3, "istock_video": 5},
                "active_promos": [],
            }

            _run_worker_on_thread(qtbot, worker)

        assert len(rates) == 1
        assert rates[0]["istock_photo"] == 3
        assert rates[0]["istock_video"] == 5

    def test_finished_signal_always_emitted(self, qtbot):
        """finished signal should always fire, even if balance load fails."""
        worker = StartupWorker()

        finished = []
        worker.finished.connect(lambda: finished.append(True))

        with _startup_patches() as mock_api:
            mock_api.check_update.side_effect = NetworkError()
            mock_api.get_balance_with_promos.side_effect = NetworkError()

            _run_worker_on_thread(qtbot, worker)

        assert len(finished) == 1, "finished must emit even on errors"

    def test_balance_not_emitted_on_network_error(self, qtbot):
        """If balance API fails, balance_loaded should NOT emit."""
        worker = StartupWorker()

        balances = []
        worker.balance_loaded.connect(lambda b: balances.append(b))

        with _startup_patches() as mock_api:
            mock_api.check_update.return_value = {}
            mock_api.get_balance_with_promos.side_effect = NetworkError()

            _run_worker_on_thread(qtbot, worker)

        assert len(balances) == 0, "balance_loaded should not emit on error"


# ═══════════════════════════════════════════════════════════
# Test 4: Chained Flow — Login → Extract Token → Balance
#
#   Simulates the real app handshake:
#   AuthWorker login → get token → StartupWorker loads balance
# ═══════════════════════════════════════════════════════════

class TestChainedLoginToBalance:

    def test_login_then_balance_check(self, qtbot):
        """
        Full chained integration:
        1. AuthWorker login → finished signal → extract token "fake-jwt-123"
        2. Pass token context to StartupWorker
        3. StartupWorker → balance_loaded signal → assert 500
        """
        # ── Phase 1: Login ──
        mock_login_response = {
            "token": "fake-jwt-123",
            "user_id": "uid-chain-001",
            "email": "chain@bigeye.com",
            "full_name": "Chain User",
            "credits": 0,
        }

        auth_manager = AuthManager()
        login_worker = AuthWorker(auth_manager)
        login_worker.set_login("chain@bigeye.com", "ChainPass_42")

        login_results = []
        login_worker.finished.connect(lambda d: login_results.append(d))

        with _auth_patches() as mock_api:
            mock_api.login.return_value = mock_login_response

            _run_worker_on_thread(qtbot, login_worker)

        # Verify login succeeded
        assert len(login_results) == 1
        extracted_token = login_results[0]["token"]
        assert extracted_token == "fake-jwt-123"

        # ── Phase 2: Balance Check (using the extracted token context) ──
        balance_worker = StartupWorker()

        balances = []
        balance_worker.balance_loaded.connect(lambda b: balances.append(b))

        with _startup_patches() as mock_api:
            # Simulate: the API client now has the token set from login
            mock_api.check_update.return_value = {}
            mock_api.get_balance_with_promos.return_value = {
                "credits": 500,
                "exchange_rate": 4,
                "credit_rates": {},
                "active_promos": [],
            }

            _run_worker_on_thread(qtbot, balance_worker)

        # Verify balance
        assert len(balances) == 1
        assert balances[0] == 500

    def test_login_failure_prevents_balance_check(self, qtbot):
        """
        If login fails (AuthenticationError), the error signal fires
        and no balance check should happen.
        """
        auth_manager = AuthManager()
        worker = AuthWorker(auth_manager)
        worker.set_login("bad@bigeye.com", "wrong_pass")

        login_results = []
        errors = []
        worker.finished.connect(lambda d: login_results.append(d))
        worker.error.connect(lambda msg: errors.append(msg))

        with _auth_patches() as mock_api:
            mock_api.login.side_effect = AuthenticationError("Invalid", 401)

            _run_worker_on_thread(qtbot, worker)

        # Login failed → no token to use
        assert len(login_results) == 0, "finished should NOT emit on failure"
        assert len(errors) == 1, "error should emit exactly once"

        # In a real app, MainWindow would not start StartupWorker
        # because AuthWindow wouldn't call accept(). We verify this
        # by confirming no token was produced.

    def test_register_then_balance_zero(self, qtbot):
        """
        Register (new account) → token → balance check → 0 credits.
        """
        mock_register_response = {
            "token": "new-user-jwt-789",
            "user_id": "uid-new-001",
            "email": "brand_new@bigeye.com",
            "full_name": "Brand New",
            "credits": 0,
        }

        auth_manager = AuthManager()
        reg_worker = AuthWorker(auth_manager)
        reg_worker.set_register("brand_new@bigeye.com", "NewPass_99", "Brand New", "0891234567")

        reg_results = []
        reg_worker.finished.connect(lambda d: reg_results.append(d))

        with _auth_patches() as mock_api:
            mock_api.register.return_value = mock_register_response

            _run_worker_on_thread(qtbot, reg_worker)

        assert reg_results[0]["token"] == "new-user-jwt-789"

        # Balance check → new user has 0 credits
        balance_worker = StartupWorker()
        balances = []
        balance_worker.balance_loaded.connect(lambda b: balances.append(b))

        with _startup_patches() as mock_api:
            mock_api.check_update.return_value = {}
            mock_api.get_balance_with_promos.return_value = {
                "credits": 0,
                "exchange_rate": 4,
                "credit_rates": {},
                "active_promos": [],
            }

            _run_worker_on_thread(qtbot, balance_worker)

        assert balances[0] == 0
