"""
Tests for server/app/config.py
Covers: Settings defaults, admin_uid_list property, type coercions.
"""
import pytest
from unittest.mock import patch
import os

from app.config import Settings, settings


class TestSettingsDefaults:

    def test_default_environment(self):
        s = Settings()
        assert s.ENVIRONMENT == "development"

    def test_default_jwt_algorithm(self):
        s = Settings()
        assert s.JWT_ALGORITHM == "HS256"

    def test_default_jwt_expire_hours(self):
        s = Settings()
        assert s.JWT_EXPIRE_HOURS == 168  # 7 days

    def test_default_app_version(self):
        s = Settings()
        assert s.APP_VERSION == "2.0.0"

    def test_default_exchange_rate(self):
        s = Settings()
        assert s.EXCHANGE_RATE == 4

    def test_default_credit_rates(self):
        s = Settings()
        assert s.ISTOCK_RATE == 3
        assert s.ADOBE_RATE == 2
        assert s.SHUTTERSTOCK_RATE == 2

    def test_default_concurrency(self):
        s = Settings()
        assert s.MAX_CONCURRENT_IMAGES == 5
        assert s.MAX_CONCURRENT_VIDEOS == 2

    def test_default_context_cache_threshold(self):
        s = Settings()
        assert s.CONTEXT_CACHE_THRESHOLD == 20

    def test_default_job_expire_hours(self):
        s = Settings()
        assert s.JOB_EXPIRE_HOURS == 2

    def test_aes_key_is_64_hex_chars(self):
        s = Settings()
        assert len(s.AES_KEY) == 64
        int(s.AES_KEY, 16)  # valid hex


class TestAdminUidList:

    def test_empty_admin_uids_returns_empty_list(self):
        s = Settings(ADMIN_UIDS="")
        assert s.admin_uid_list == []

    def test_single_admin_uid(self):
        s = Settings(ADMIN_UIDS="uid-001")
        assert s.admin_uid_list == ["uid-001"]

    def test_multiple_admin_uids(self):
        s = Settings(ADMIN_UIDS="uid-001, uid-002, uid-003")
        assert s.admin_uid_list == ["uid-001", "uid-002", "uid-003"]

    def test_strips_whitespace(self):
        s = Settings(ADMIN_UIDS="  uid-001 ,  uid-002  ")
        assert s.admin_uid_list == ["uid-001", "uid-002"]

    def test_ignores_empty_entries(self):
        s = Settings(ADMIN_UIDS="uid-001,,uid-002,  ,uid-003")
        assert s.admin_uid_list == ["uid-001", "uid-002", "uid-003"]

    def test_singleton_settings_exists(self):
        """The module-level `settings` singleton should be a Settings instance."""
        assert isinstance(settings, Settings)
