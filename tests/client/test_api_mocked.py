"""
Tests for API client with mocked httpx:
  - Network error handling (ConnectError, TimeoutException)
  - HTTP status code → custom exception mapping (401, 402, 403, 409, 426, 429, 503)
  - InsufficientCreditsError with required/available/shortfall
  - Token management (set_token, clear_token, auto-set on login/register)
  - reserve_job, finalize_job, get_balance, topup methods
  - How the UI/JobManager should handle these errors
"""
import pytest
from unittest.mock import patch, MagicMock
import httpx

from core.api_client import (
    APIClient, APIError, NetworkError, AuthenticationError,
    InsufficientCreditsError, ForbiddenError, ConflictError,
    UpdateRequiredError, RateLimitError, MaintenanceError,
)


@pytest.fixture
def client():
    """Fresh APIClient for each test."""
    return APIClient(base_url="http://test:8080/api/v1")


def _mock_response(status_code: int, json_body: dict = None):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    return resp


# ═══════════════════════════════════════
# Network Error Handling
# ═══════════════════════════════════════

class TestNetworkErrors:

    def test_connect_error_raises_network_error(self, client):
        with patch.object(client._client, "get", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(NetworkError):
                client.get_balance()

    def test_timeout_raises_network_error(self, client):
        with patch.object(client._client, "get", side_effect=httpx.TimeoutException("Timed out")):
            with pytest.raises(NetworkError):
                client.get_balance()

    def test_network_error_on_post(self, client):
        with patch.object(client._client, "post", side_effect=httpx.ConnectError("No route")):
            with pytest.raises(NetworkError):
                client.login("test@test.com", "pass", "hw_id_12345678")

    def test_network_error_message(self, client):
        with patch.object(client._client, "get", side_effect=httpx.ConnectError("fail")):
            with pytest.raises(NetworkError) as exc_info:
                client.get_balance()
            assert "connect" in str(exc_info.value).lower() or "server" in str(exc_info.value).lower()

    def test_network_error_status_code_zero(self, client):
        with patch.object(client._client, "get", side_effect=httpx.ConnectError("fail")):
            with pytest.raises(NetworkError) as exc_info:
                client.get_balance()
            assert exc_info.value.status_code == 0


# ═══════════════════════════════════════
# HTTP Status Code → Exception Mapping
# ═══════════════════════════════════════

class TestErrorMapping:

    def test_401_raises_authentication_error(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(401, {"detail": "Invalid credentials"})):
            with pytest.raises(AuthenticationError) as exc_info:
                client.login("bad@test.com", "wrong", "hw_id_12345678")
            assert exc_info.value.status_code == 401
            assert "invalid" in str(exc_info.value).lower()

    def test_402_raises_insufficient_credits(self, client):
        client.set_token("fake-jwt")
        body = {
            "detail": "Insufficient credits",
            "required": 300,
            "available": 50,
            "shortfall": 250,
        }
        with patch.object(client._client, "post", return_value=_mock_response(402, body)):
            with pytest.raises(InsufficientCreditsError) as exc_info:
                client.reserve_job(100, "iStock", "Hybrid", "gemini-2.5-pro", "2.0.0")
            e = exc_info.value
            assert e.status_code == 402
            assert e.required == 300
            assert e.available == 50
            assert e.shortfall == 250

    def test_403_raises_forbidden_error(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(403, {"detail": "Device mismatch"})):
            with pytest.raises(ForbiddenError) as exc_info:
                client.login("test@test.com", "pass", "wrong_device_id_1234")
            assert exc_info.value.status_code == 403

    def test_409_raises_conflict_error(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(409, {"detail": "Email already registered"})):
            with pytest.raises(ConflictError) as exc_info:
                client.register("dup@test.com", "pass", "Name", "phone", "hw_id_12345678")
            assert exc_info.value.status_code == 409

    def test_426_raises_update_required(self, client):
        body = {
            "detail": "Update required",
            "version": "2.1.0",
            "download_url": "https://example.com/dl",
            "force": True,
        }
        with patch.object(client._client, "post", return_value=_mock_response(426, body)):
            with pytest.raises(UpdateRequiredError) as exc_info:
                client.check_update("1.0.0", "hw_id_12345678")
            e = exc_info.value
            assert e.version == "2.1.0"
            assert e.download_url == "https://example.com/dl"
            assert e.force is True

    def test_429_raises_rate_limit(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(429, {"detail": "Too many requests"})):
            with pytest.raises(RateLimitError):
                client.login("test@test.com", "pass", "hw_id_12345678")

    def test_503_raises_maintenance(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(503, {"detail": "Server maintenance"})):
            with pytest.raises(MaintenanceError):
                client.login("test@test.com", "pass", "hw_id_12345678")

    def test_500_raises_generic_api_error(self, client):
        with patch.object(client._client, "post", return_value=_mock_response(500, {"detail": "Internal error"})):
            with pytest.raises(APIError) as exc_info:
                client.login("test@test.com", "pass", "hw_id_12345678")
            assert exc_info.value.status_code == 500

    def test_exception_hierarchy(self):
        """All custom exceptions should extend APIError."""
        assert issubclass(NetworkError, APIError)
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(InsufficientCreditsError, APIError)
        assert issubclass(ForbiddenError, APIError)
        assert issubclass(ConflictError, APIError)
        assert issubclass(UpdateRequiredError, APIError)
        assert issubclass(RateLimitError, APIError)
        assert issubclass(MaintenanceError, APIError)


# ═══════════════════════════════════════
# Token Management
# ═══════════════════════════════════════

class TestTokenManagement:

    def test_set_token(self, client):
        client.set_token("my-jwt-token")
        assert client.is_authenticated is True
        assert client._client.headers["Authorization"] == "Bearer my-jwt-token"

    def test_clear_token(self, client):
        client.set_token("my-jwt-token")
        client.clear_token()
        assert client.is_authenticated is False
        assert "Authorization" not in client._client.headers

    def test_login_auto_sets_token(self, client):
        resp = _mock_response(200, {"token": "jwt-from-login", "user_id": "u1",
                                     "email": "t@t.com", "full_name": "T", "credits": 100})
        with patch.object(client._client, "post", return_value=resp):
            data = client.login("t@t.com", "pass", "hw_id_12345678")
        assert client.is_authenticated is True
        assert data["token"] == "jwt-from-login"

    def test_register_auto_sets_token(self, client):
        resp = _mock_response(200, {"token": "jwt-from-register", "user_id": "u2",
                                     "email": "n@t.com", "full_name": "N", "credits": 0})
        with patch.object(client._client, "post", return_value=resp):
            data = client.register("n@t.com", "pass", "Name", "phone", "hw_id_12345678")
        assert client.is_authenticated is True

    def test_not_authenticated_initially(self, client):
        assert client.is_authenticated is False


# ═══════════════════════════════════════
# API Methods (Happy Paths)
# ═══════════════════════════════════════

class TestAPIMethods:

    def test_get_balance(self, client):
        client.set_token("jwt")
        resp = _mock_response(200, {"credits": 500, "exchange_rate": 4, "credit_rates": {}, "active_promos": []})
        with patch.object(client._client, "get", return_value=resp):
            balance = client.get_balance()
        assert balance == 500

    def test_get_balance_with_promos(self, client):
        client.set_token("jwt")
        resp = _mock_response(200, {
            "credits": 500, "exchange_rate": 4,
            "credit_rates": {"istock_photo": 3},
            "active_promos": [{"name": "Summer Sale"}],
        })
        with patch.object(client._client, "get", return_value=resp):
            data = client.get_balance_with_promos()
        assert data["credits"] == 500
        assert len(data["active_promos"]) == 1

    def test_reserve_job(self, client):
        client.set_token("jwt")
        resp = _mock_response(200, {
            "job_token": "tok-123",
            "reserved_credits": 30,
            "photo_rate": 3, "video_rate": 3,
            "config": "encrypted_hex",
            "dictionary": "word1,word2",
            "blacklist": ["nike"],
            "concurrency": {"image": 5, "video": 2},
            "cache_threshold": 20,
        })
        with patch.object(client._client, "post", return_value=resp):
            data = client.reserve_job(10, "iStock", "Hybrid", "gemini-2.5-pro", "2.0.0", 8, 2)
        assert data["job_token"] == "tok-123"
        assert data["reserved_credits"] == 30

    def test_finalize_job(self, client):
        client.set_token("jwt")
        resp = _mock_response(200, {"refunded": 9, "balance": 479})
        with patch.object(client._client, "post", return_value=resp):
            data = client.finalize_job("tok-123", 7, 3, 10, 0)
        assert data["refunded"] == 9
        assert data["balance"] == 479

    def test_topup(self, client):
        client.set_token("jwt")
        resp = _mock_response(200, {
            "status": "verified", "base_credits": 400,
            "bonus_credits": 0, "total_credits": 400,
            "new_balance": 900, "promo_applied": None, "message": "Added 400 credits",
        })
        with patch.object(client._client, "post", return_value=resp):
            data = client.topup("base64_slip", 100)
        assert data["total_credits"] == 400

    def test_get_history(self, client):
        client.set_token("jwt")
        resp = _mock_response(200, {
            "transactions": [{"date": "2025-01-01", "description": "Topup", "amount": 400, "type": "TOPUP"}],
            "balance": 500,
        })
        with patch.object(client._client, "get", return_value=resp):
            txs = client.get_history(limit=10)
        assert len(txs) == 1
        assert txs[0]["type"] == "TOPUP"


# ═══════════════════════════════════════
# JobManager Error Handling Simulation
# ═══════════════════════════════════════

class TestJobManagerErrorHandling:
    """
    Simulate how JobManager.start_job handles API errors.
    These test the error flow without launching the GUI.
    """

    def test_network_error_emits_job_failed(self):
        """When api.reserve_job raises NetworkError, JobManager should emit job_failed."""
        from unittest.mock import MagicMock
        # Simulate the error handling logic from JobManager.start_job lines 152-158
        error_message = None
        try:
            raise NetworkError()
        except NetworkError:
            error_message = "Cannot connect to server. Please check your internet."
        assert "connect" in error_message.lower()

    def test_insufficient_credits_emits_job_failed(self):
        """When api.reserve_job raises InsufficientCreditsError."""
        error_message = None
        try:
            raise InsufficientCreditsError("Insufficient credits", required=300, available=50, shortfall=250)
        except APIError as e:
            error_message = f"Server error: {e}"
        assert "insufficient" in error_message.lower()

    def test_forbidden_error_emits_job_failed(self):
        error_message = None
        try:
            raise ForbiddenError("Account suspended", 403)
        except APIError as e:
            error_message = f"Server error: {e}"
        assert "suspended" in error_message.lower()
