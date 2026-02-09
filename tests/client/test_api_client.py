"""
Tests for client/core/api_client.py
Covers: APIClient error mapping, token management, HTTP method helpers,
        custom exception hierarchy.
"""
import pytest
from unittest.mock import patch, MagicMock
import httpx

from core.api_client import (
    APIClient,
    APIError,
    NetworkError,
    AuthenticationError,
    InsufficientCreditsError,
    ForbiddenError,
    ConflictError,
    UpdateRequiredError,
    RateLimitError,
    MaintenanceError,
)


# ═══════════════════════════════════════
# Exception Hierarchy
# ═══════════════════════════════════════

class TestExceptionHierarchy:

    def test_all_errors_extend_api_error(self):
        assert issubclass(NetworkError, APIError)
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(InsufficientCreditsError, APIError)
        assert issubclass(ForbiddenError, APIError)
        assert issubclass(ConflictError, APIError)
        assert issubclass(UpdateRequiredError, APIError)
        assert issubclass(RateLimitError, APIError)
        assert issubclass(MaintenanceError, APIError)

    def test_api_error_has_status_code(self):
        e = APIError("test", 500)
        assert e.status_code == 500
        assert str(e) == "test"

    def test_network_error_defaults(self):
        e = NetworkError()
        assert e.status_code == 0
        assert "internet" in str(e).lower()

    def test_insufficient_credits_error_fields(self):
        e = InsufficientCreditsError("Not enough", required=100, available=50, shortfall=50)
        assert e.required == 100
        assert e.available == 50
        assert e.shortfall == 50
        assert e.status_code == 402

    def test_update_required_error_fields(self):
        e = UpdateRequiredError("Update needed", version="3.0.0", download_url="https://example.com", force=True)
        assert e.version == "3.0.0"
        assert e.download_url == "https://example.com"
        assert e.force is True
        assert e.status_code == 426


# ═══════════════════════════════════════
# Token Management
# ═══════════════════════════════════════

class TestTokenManagement:

    def test_initial_state_unauthenticated(self):
        client = APIClient(base_url="http://localhost:9999")
        assert client.is_authenticated is False

    def test_set_token(self):
        client = APIClient(base_url="http://localhost:9999")
        client.set_token("my-jwt-token")
        assert client.is_authenticated is True
        assert client._client.headers["Authorization"] == "Bearer my-jwt-token"

    def test_clear_token(self):
        client = APIClient(base_url="http://localhost:9999")
        client.set_token("my-jwt-token")
        client.clear_token()
        assert client.is_authenticated is False
        assert "Authorization" not in client._client.headers

    def test_clear_token_when_not_set(self):
        """Clearing when no token is set should not raise."""
        client = APIClient(base_url="http://localhost:9999")
        client.clear_token()  # Should not raise
        assert client.is_authenticated is False


# ═══════════════════════════════════════
# Error Mapping (_handle_errors)
# ═══════════════════════════════════════

class TestHandleErrors:

    def _make_response(self, status_code: int, json_body: dict = None):
        """Create a mock httpx.Response."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        if json_body is not None:
            resp.json.return_value = json_body
        else:
            resp.json.side_effect = Exception("no body")
        return resp

    def test_200_returns_json(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(200, {"credits": 100})
        result = client._handle_errors(resp)
        assert result == {"credits": 100}

    def test_401_raises_authentication_error(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(401, {"detail": "Invalid credentials"})
        with pytest.raises(AuthenticationError) as exc_info:
            client._handle_errors(resp)
        assert exc_info.value.status_code == 401

    def test_402_raises_insufficient_credits(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(402, {"detail": "Not enough credits", "required": 100, "available": 50})
        with pytest.raises(InsufficientCreditsError) as exc_info:
            client._handle_errors(resp)
        assert exc_info.value.required == 100

    def test_403_raises_forbidden(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(403, {"detail": "Device mismatch"})
        with pytest.raises(ForbiddenError):
            client._handle_errors(resp)

    def test_409_raises_conflict(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(409, {"detail": "Email already registered"})
        with pytest.raises(ConflictError):
            client._handle_errors(resp)

    def test_426_raises_update_required(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(426, {
            "detail": "Update required",
            "version": "3.0.0",
            "download_url": "https://example.com",
            "force": True,
        })
        with pytest.raises(UpdateRequiredError) as exc_info:
            client._handle_errors(resp)
        assert exc_info.value.force is True

    def test_429_raises_rate_limit(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(429, {"detail": "Too many requests"})
        with pytest.raises(RateLimitError):
            client._handle_errors(resp)

    def test_503_raises_maintenance(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(503, {"detail": "Maintenance"})
        with pytest.raises(MaintenanceError):
            client._handle_errors(resp)

    def test_500_raises_generic_api_error(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(500, {"detail": "Internal error"})
        with pytest.raises(APIError) as exc_info:
            client._handle_errors(resp)
        assert exc_info.value.status_code == 500

    def test_no_json_body_uses_status_code_message(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = self._make_response(500)
        with pytest.raises(APIError) as exc_info:
            client._handle_errors(resp)
        assert "500" in str(exc_info.value)


# ═══════════════════════════════════════
# Network Error Handling
# ═══════════════════════════════════════

class TestNetworkErrors:

    def test_get_connect_error_raises_network_error(self):
        client = APIClient(base_url="http://localhost:9999")
        with patch.object(client._client, "get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(NetworkError):
                client._get("/test")

    def test_get_timeout_raises_network_error(self):
        client = APIClient(base_url="http://localhost:9999")
        with patch.object(client._client, "get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(NetworkError):
                client._get("/test")

    def test_post_connect_error_raises_network_error(self):
        client = APIClient(base_url="http://localhost:9999")
        with patch.object(client._client, "post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(NetworkError):
                client._post("/test", {})

    def test_post_timeout_raises_network_error(self):
        client = APIClient(base_url="http://localhost:9999")
        with patch.object(client._client, "post", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(NetworkError):
                client._post("/test", {})


# ═══════════════════════════════════════
# API Methods (login/register auto-set token)
# ═══════════════════════════════════════

class TestAPIMethods:

    def test_login_sets_token_on_success(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"token": "jwt-abc", "user_id": "u1", "email": "a@b.com", "full_name": "A", "credits": 10}
        with patch.object(client._client, "post", return_value=resp):
            result = client.login("a@b.com", "pass", "hw-id-12345678")
            assert client.is_authenticated
            assert result["token"] == "jwt-abc"

    def test_register_sets_token_on_success(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"token": "jwt-xyz", "user_id": "u2", "email": "b@c.com", "full_name": "B", "credits": 0}
        with patch.object(client._client, "post", return_value=resp):
            result = client.register("b@c.com", "pass", "Name", "0812345678", "hw-id-12345678")
            assert client.is_authenticated
            assert result["token"] == "jwt-xyz"

    def test_get_balance_returns_int(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"credits": 500, "exchange_rate": 4}
        with patch.object(client._client, "get", return_value=resp):
            balance = client.get_balance()
            assert balance == 500

    def test_get_balance_with_promos(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {
            "credits": 500,
            "exchange_rate": 4,
            "credit_rates": {"istock_photo": 3},
            "active_promos": [{"name": "Summer Sale"}],
        }
        with patch.object(client._client, "get", return_value=resp):
            result = client.get_balance_with_promos()
            assert result["credits"] == 500
            assert len(result["active_promos"]) == 1

    def test_get_history_returns_list(self):
        client = APIClient(base_url="http://localhost:9999")
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {"transactions": [{"date": "2025-01-01", "amount": 100}], "balance": 500}
        with patch.object(client._client, "get", return_value=resp):
            history = client.get_history(limit=10)
            assert len(history) == 1
