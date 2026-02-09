"""
Tests for server/app/dependencies.py
Covers: get_current_user — JWT validation, user lookup, banned check.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError

from app.dependencies import get_current_user
from app.security import create_jwt_token


@pytest.fixture
def valid_credentials():
    token = create_jwt_token("user-001", "test@example.com")
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def active_user_doc():
    doc = MagicMock()
    doc.exists = True
    doc.id = "user-001"
    doc.to_dict.return_value = {
        "email": "test@example.com",
        "full_name": "Test User",
        "credits": 100,
        "status": "active",
    }
    return doc


@pytest.fixture
def banned_user_doc():
    doc = MagicMock()
    doc.exists = True
    doc.id = "user-001"
    doc.to_dict.return_value = {
        "email": "test@example.com",
        "full_name": "Banned User",
        "credits": 0,
        "status": "banned",
    }
    return doc


class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, valid_credentials, active_user_doc):
        with patch("app.dependencies.users_ref") as mock_ref:
            mock_ref.return_value.document.return_value.get.return_value = active_user_doc
            user = await get_current_user(valid_credentials)
            assert user["user_id"] == "user-001"
            assert user["email"] == "test@example.com"
            assert user["status"] == "active"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_without_sub_raises_401(self):
        """Token with no 'sub' claim should raise 401."""
        from jose import jwt as jose_jwt
        from datetime import datetime, timedelta, timezone
        from app.config import settings
        payload = {
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self, valid_credentials):
        not_found_doc = MagicMock()
        not_found_doc.exists = False
        with patch("app.dependencies.users_ref") as mock_ref:
            mock_ref.return_value.document.return_value.get.return_value = not_found_doc
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(valid_credentials)
            assert exc_info.value.status_code == 401
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_banned_user_raises_403(self, valid_credentials, banned_user_doc):
        with patch("app.dependencies.users_ref") as mock_ref:
            mock_ref.return_value.document.return_value.get.return_value = banned_user_doc
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(valid_credentials)
            assert exc_info.value.status_code == 403
            assert "suspended" in exc_info.value.detail.lower()
