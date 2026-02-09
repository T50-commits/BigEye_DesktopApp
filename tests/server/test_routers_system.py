"""
Tests for server/app/routers/system.py
Covers: _version_lt helper, health endpoint, check-update logic.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.routers.system import _version_lt


# ═══════════════════════════════════════
# Version Comparison (_version_lt)
# ═══════════════════════════════════════

class TestVersionLt:

    def test_equal_versions(self):
        assert _version_lt("2.0.0", "2.0.0") is False

    def test_older_major(self):
        assert _version_lt("1.0.0", "2.0.0") is True

    def test_newer_major(self):
        assert _version_lt("3.0.0", "2.0.0") is False

    def test_older_minor(self):
        assert _version_lt("2.0.0", "2.1.0") is True

    def test_newer_minor(self):
        assert _version_lt("2.2.0", "2.1.0") is False

    def test_older_patch(self):
        assert _version_lt("2.0.0", "2.0.1") is True

    def test_newer_patch(self):
        assert _version_lt("2.0.2", "2.0.1") is False

    def test_complex_version(self):
        assert _version_lt("1.9.9", "2.0.0") is True
        assert _version_lt("2.0.0", "1.9.9") is False

    def test_invalid_version_returns_false(self):
        assert _version_lt("abc", "2.0.0") is False
        assert _version_lt("2.0.0", "xyz") is False
        assert _version_lt("", "") is False

    def test_different_length_versions(self):
        # Python list comparison handles different lengths
        assert _version_lt("2.0", "2.0.1") is True
        assert _version_lt("2.0.1", "2.0") is False


# ═══════════════════════════════════════
# Health Endpoint (unit test, no HTTP)
# ═══════════════════════════════════════

class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        from app.routers.system import health
        result = await health()
        assert result.status == "ok"
        assert result.version == "2.0.0"
        assert result.environment == "development"
