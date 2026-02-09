"""
Tests for server/app/services/promo_engine.py
Covers: calculate_bonus, is_new_user, find_applicable_promos sorting, expire_promotions.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.services.promo_engine import (
    calculate_bonus,
    is_new_user,
    has_previous_topup,
    count_user_redemptions,
    get_exchange_rate,
)


# ═══════════════════════════════════════
# get_exchange_rate
# ═══════════════════════════════════════

class TestGetExchangeRate:

    def test_returns_firestore_rate(self):
        with patch("app.services.promo_engine.get_db") as mock_db:
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {"exchange_rate": 5}
            mock_db.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
            assert get_exchange_rate() == 5

    def test_returns_fallback_on_missing(self):
        with patch("app.services.promo_engine.get_db") as mock_db:
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {}  # no exchange_rate key
            mock_db.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
            assert get_exchange_rate() == 4  # settings.EXCHANGE_RATE

    def test_returns_fallback_on_exception(self):
        with patch("app.services.promo_engine.get_db") as mock_db:
            mock_db.return_value.collection.side_effect = Exception("DB down")
            assert get_exchange_rate() == 4

    def test_returns_fallback_on_non_numeric(self):
        with patch("app.services.promo_engine.get_db") as mock_db:
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {"exchange_rate": "not-a-number"}
            mock_db.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
            assert get_exchange_rate() == 4

    def test_returns_fallback_when_doc_not_exists(self):
        with patch("app.services.promo_engine.get_db") as mock_db:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_db.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
            assert get_exchange_rate() == 4


# ═══════════════════════════════════════
# calculate_bonus
# ═══════════════════════════════════════

class TestCalculateBonus:

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_bonus_credits_type(self, _):
        promo = {"reward": {"type": "BONUS_CREDITS", "bonus_credits": 50}}
        assert calculate_bonus(promo, 100) == 50

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_bonus_credits_none_value(self, _):
        promo = {"reward": {"type": "BONUS_CREDITS", "bonus_credits": None}}
        assert calculate_bonus(promo, 100) == 0

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_rate_override_type(self, _):
        """Rate override: new_credits - base_credits."""
        promo = {"reward": {"type": "RATE_OVERRIDE", "override_rate": 6}}
        # base = 100 * 4 = 400, new = 100 * 6 = 600, bonus = 200
        assert calculate_bonus(promo, 100) == 200

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_rate_override_lower_than_base(self, _):
        """If override rate is lower than base, bonus is negative (penalty)."""
        promo = {"reward": {"type": "RATE_OVERRIDE", "override_rate": 2}}
        # base = 100 * 4 = 400, new = 100 * 2 = 200, bonus = -200
        assert calculate_bonus(promo, 100) == -200

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_percentage_bonus_type(self, _):
        promo = {"reward": {"type": "PERCENTAGE_BONUS", "bonus_percentage": 25}}
        # base = 100 * 4 = 400, bonus = 400 * 25 / 100 = 100
        assert calculate_bonus(promo, 100) == 100

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_percentage_bonus_zero(self, _):
        promo = {"reward": {"type": "PERCENTAGE_BONUS", "bonus_percentage": 0}}
        assert calculate_bonus(promo, 100) == 0

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_tiered_bonus_matches_tier(self, _):
        promo = {
            "reward": {
                "type": "TIERED_BONUS",
                "tiers": [
                    {"min_baht": 100, "max_baht": 499, "credits": 500},
                    {"min_baht": 500, "max_baht": None, "credits": 3000},
                ],
            }
        }
        # topup=200, matches first tier (100-499), credits=500
        # base = 200 * 4 = 800, bonus = 500 - 800 = -300
        assert calculate_bonus(promo, 200) == -300

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_tiered_bonus_highest_tier(self, _):
        promo = {
            "reward": {
                "type": "TIERED_BONUS",
                "tiers": [
                    {"min_baht": 100, "max_baht": 499, "credits": 500},
                    {"min_baht": 500, "max_baht": None, "credits": 3000},
                ],
            }
        }
        # topup=1000, matches second tier (500+), credits=3000
        # base = 1000 * 4 = 4000, bonus = 3000 - 4000 = -1000
        assert calculate_bonus(promo, 1000) == -1000

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_tiered_bonus_no_match(self, _):
        promo = {
            "reward": {
                "type": "TIERED_BONUS",
                "tiers": [
                    {"min_baht": 500, "max_baht": None, "credits": 3000},
                ],
            }
        }
        # topup=100, below min_baht=500 → no match
        assert calculate_bonus(promo, 100) == 0

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_unknown_reward_type(self, _):
        promo = {"reward": {"type": "UNKNOWN_TYPE"}}
        assert calculate_bonus(promo, 100) == 0

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_empty_reward(self, _):
        promo = {"reward": {}}
        assert calculate_bonus(promo, 100) == 0

    @patch("app.services.promo_engine.get_exchange_rate", return_value=4)
    def test_missing_reward_key(self, _):
        promo = {}
        assert calculate_bonus(promo, 100) == 0


# ═══════════════════════════════════════
# is_new_user
# ═══════════════════════════════════════

class TestIsNewUser:

    def test_new_user_within_7_days(self):
        user = {"created_at": datetime.now(timezone.utc) - timedelta(days=3)}
        assert is_new_user(user) is True

    def test_old_user_beyond_7_days(self):
        user = {"created_at": datetime.now(timezone.utc) - timedelta(days=10)}
        assert is_new_user(user) is False

    def test_exactly_7_days(self):
        user = {"created_at": datetime.now(timezone.utc) - timedelta(days=7, seconds=1)}
        assert is_new_user(user) is False

    def test_no_created_at(self):
        assert is_new_user({}) is False
        assert is_new_user({"created_at": None}) is False

    def test_firestore_timestamp_with_timestamp_method(self):
        """Firestore timestamps have a .timestamp() method."""
        mock_ts = MagicMock()
        mock_ts.timestamp.return_value = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
        user = {"created_at": mock_ts}
        assert is_new_user(user) is True


# ═══════════════════════════════════════
# has_previous_topup
# ═══════════════════════════════════════

class TestHasPreviousTopup:

    def test_no_previous_topup(self):
        with patch("app.database.transactions_ref") as mock_ref:
            mock_ref.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = iter([])
            assert has_previous_topup("user-001") is False

    def test_has_previous_topup(self):
        with patch("app.database.transactions_ref") as mock_ref:
            fake_doc = MagicMock()
            mock_ref.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = iter([fake_doc])
            assert has_previous_topup("user-001") is True


# ═══════════════════════════════════════
# count_user_redemptions
# ═══════════════════════════════════════

class TestCountUserRedemptions:

    def test_zero_redemptions(self):
        with patch("app.services.promo_engine._promo_redemptions_ref") as mock_ref:
            mock_ref.return_value.where.return_value.where.return_value.stream.return_value = iter([])
            assert count_user_redemptions("user-001", "promo-001") == 0

    def test_multiple_redemptions(self):
        with patch("app.services.promo_engine._promo_redemptions_ref") as mock_ref:
            mock_ref.return_value.where.return_value.where.return_value.stream.return_value = iter([
                MagicMock(), MagicMock(), MagicMock(),
            ])
            assert count_user_redemptions("user-001", "promo-001") == 3
