"""
Tests for server/app/models/__init__.py and server/app/models/promo.py
Covers: Pydantic validation, field constraints, defaults, edge cases.
"""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from app.models import (
    RegisterRequest, LoginRequest, AuthResponse,
    BalanceResponse, TopUpRequest, TopUpResponse,
    TransactionItem, HistoryResponse,
    ReserveJobRequest, ReserveJobResponse,
    FinalizeJobRequest, FinalizeJobResponse,
    CheckUpdateRequest, CheckUpdateResponse, HealthResponse,
)
from app.models.promo import (
    PromoTier, PromoConditions, PromoReward, PromoDisplay, PromoStats,
    CreatePromoRequest, UpdatePromoRequest,
    PromoResponse, PromoListResponse, PromoCreateResponse, PromoActionResponse,
    ActivePromoInfo, CreditRatesInfo, BalanceWithPromosResponse,
    TopUpWithPromoRequest, TopUpWithPromoResponse,
    RedemptionItem, PromoStatsResponse,
)


# ═══════════════════════════════════════
# Auth Models
# ═══════════════════════════════════════

class TestRegisterRequest:

    def test_valid_register(self):
        r = RegisterRequest(
            email="user@example.com",
            password="secret123",
            full_name="John Doe",
            hardware_id="abcdef1234567890",
        )
        assert r.email == "user@example.com"
        assert r.full_name == "John Doe"

    def test_invalid_email_rejects(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                password="secret123",
                full_name="John",
                hardware_id="abcdef1234567890",
            )

    def test_password_too_short_rejects(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="12345",  # min_length=6
                full_name="John",
                hardware_id="abcdef1234567890",
            )

    def test_password_too_long_rejects(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="x" * 129,  # max_length=128
                full_name="John",
                hardware_id="abcdef1234567890",
            )

    def test_full_name_empty_rejects(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="secret123",
                full_name="",  # min_length=1
                hardware_id="abcdef1234567890",
            )

    def test_hardware_id_too_short_rejects(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="secret123",
                full_name="John",
                hardware_id="short",  # min_length=8
            )

    def test_hardware_id_too_long_rejects(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="secret123",
                full_name="John",
                hardware_id="x" * 65,  # max_length=64
            )

    def test_defaults(self):
        r = RegisterRequest(
            email="user@example.com",
            password="secret123",
            full_name="John",
            hardware_id="abcdef1234567890",
        )
        assert r.phone == ""
        assert r.os_type == ""


class TestLoginRequest:

    def test_valid_login(self):
        r = LoginRequest(
            email="user@example.com",
            password="secret123",
            hardware_id="abcdef1234567890",
        )
        assert r.email == "user@example.com"

    def test_defaults(self):
        r = LoginRequest(
            email="user@example.com",
            password="secret123",
            hardware_id="abcdef1234567890",
        )
        assert r.app_version == ""


class TestAuthResponse:

    def test_valid_response(self):
        r = AuthResponse(
            token="jwt-token",
            user_id="uid-001",
            email="user@example.com",
            full_name="John",
            credits=100,
        )
        assert r.credits == 100


# ═══════════════════════════════════════
# Credit Models
# ═══════════════════════════════════════

class TestTopUpRequest:

    def test_valid_topup(self):
        r = TopUpRequest(slip="base64data", amount=100)
        assert r.amount == 100

    def test_amount_zero_rejects(self):
        with pytest.raises(ValidationError):
            TopUpRequest(slip="base64data", amount=0)

    def test_amount_negative_rejects(self):
        with pytest.raises(ValidationError):
            TopUpRequest(slip="base64data", amount=-10)


class TestTopUpWithPromoRequest:

    def test_valid_with_code(self):
        r = TopUpWithPromoRequest(slip="data", amount=500, promo_code="SAVE50")
        assert r.promo_code == "SAVE50"

    def test_promo_code_optional(self):
        r = TopUpWithPromoRequest(slip="data", amount=100)
        assert r.promo_code is None


# ═══════════════════════════════════════
# Job Models
# ═══════════════════════════════════════

class TestReserveJobRequest:

    def test_valid_reserve(self):
        r = ReserveJobRequest(file_count=10, mode="iStock")
        assert r.file_count == 10
        assert r.photo_count == 0
        assert r.video_count == 0

    def test_file_count_zero_rejects(self):
        with pytest.raises(ValidationError):
            ReserveJobRequest(file_count=0, mode="iStock")

    def test_defaults(self):
        r = ReserveJobRequest(file_count=5, mode="Adobe & Shutterstock")
        assert r.keyword_style == ""
        assert r.model == "gemini-2.5-pro"
        assert r.version == ""


class TestFinalizeJobRequest:

    def test_valid_finalize(self):
        r = FinalizeJobRequest(job_token="uuid-123", success=8, failed=2)
        assert r.success == 8
        assert r.failed == 2

    def test_defaults(self):
        r = FinalizeJobRequest(job_token="uuid-123")
        assert r.success == 0
        assert r.failed == 0
        assert r.photos == 0
        assert r.videos == 0


class TestReserveJobResponse:

    def test_defaults(self):
        r = ReserveJobResponse(job_token="uuid-123")
        assert r.reserved_credits == 0
        assert r.photo_rate == 0
        assert r.video_rate == 0
        assert r.config == ""
        assert r.dictionary == ""
        assert r.blacklist == []
        assert r.concurrency == {}
        assert r.cache_threshold == 20


# ═══════════════════════════════════════
# System Models
# ═══════════════════════════════════════

class TestCheckUpdateResponse:

    def test_defaults(self):
        r = CheckUpdateResponse()
        assert r.update_available is False
        assert r.force is False
        assert r.maintenance is False

    def test_maintenance_mode(self):
        r = CheckUpdateResponse(maintenance=True, maintenance_message="Down for update")
        assert r.maintenance is True
        assert r.maintenance_message == "Down for update"


class TestHealthResponse:

    def test_defaults(self):
        r = HealthResponse()
        assert r.status == "ok"


# ═══════════════════════════════════════
# Promo Models
# ═══════════════════════════════════════

class TestPromoTier:

    def test_valid_tier(self):
        t = PromoTier(min_baht=100, max_baht=500, credits=600)
        assert t.min_baht == 100
        assert t.credits == 600

    def test_max_baht_optional(self):
        t = PromoTier(min_baht=1000, credits=5000)
        assert t.max_baht is None


class TestPromoConditions:

    def test_minimal(self):
        c = PromoConditions(start_date=datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert c.new_users_only is False
        assert c.first_topup_only is False
        assert c.require_code is False
        assert c.end_date is None

    def test_all_fields(self):
        c = PromoConditions(
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
            min_topup_baht=100,
            max_topup_baht=5000,
            max_redemptions=1000,
            max_per_user=3,
            eligible_tiers=["standard", "premium"],
            new_users_only=True,
            first_topup_only=True,
            require_code=True,
        )
        assert c.max_per_user == 3
        assert c.eligible_tiers == ["standard", "premium"]


class TestPromoReward:

    def test_bonus_credits(self):
        r = PromoReward(type="BONUS_CREDITS", bonus_credits=50)
        assert r.bonus_credits == 50

    def test_rate_override(self):
        r = PromoReward(type="RATE_OVERRIDE", override_rate=5.0)
        assert r.override_rate == 5.0

    def test_percentage_bonus(self):
        r = PromoReward(type="PERCENTAGE_BONUS", bonus_percentage=20.0)
        assert r.bonus_percentage == 20.0

    def test_tiered_bonus(self):
        tiers = [
            PromoTier(min_baht=100, max_baht=499, credits=500),
            PromoTier(min_baht=500, credits=3000),
        ]
        r = PromoReward(type="TIERED_BONUS", tiers=tiers)
        assert len(r.tiers) == 2


class TestCreditRatesInfo:

    def test_defaults(self):
        c = CreditRatesInfo()
        assert c.istock_photo == 3
        assert c.istock_video == 3
        assert c.adobe_photo == 2
        assert c.adobe_video == 2
        assert c.shutterstock_photo == 2
        assert c.shutterstock_video == 2


class TestBalanceWithPromosResponse:

    def test_defaults(self):
        r = BalanceWithPromosResponse(credits=500)
        assert r.exchange_rate == 4
        assert r.active_promos == []
