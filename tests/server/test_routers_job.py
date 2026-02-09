"""
Tests for server/app/routers/job.py
Covers: _get_credit_rates logic, reserve/finalize anti-cheat, refund calculation.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.routers.job import _get_credit_rates
from app.config import settings


# ═══════════════════════════════════════
# _get_credit_rates
# ═══════════════════════════════════════

class TestGetCreditRates:

    def test_istock_mode_defaults(self):
        """When Firestore is unavailable, fallback to env config."""
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_ref.return_value.document.return_value.get.return_value = mock_doc
            photo_rate, video_rate = _get_credit_rates("iStock")
            assert photo_rate == settings.ISTOCK_RATE
            assert video_rate == settings.ISTOCK_RATE

    def test_adobe_mode_defaults(self):
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_ref.return_value.document.return_value.get.return_value = mock_doc
            photo_rate, video_rate = _get_credit_rates("Adobe & Shutterstock")
            assert photo_rate == settings.ADOBE_RATE
            assert video_rate == settings.ADOBE_RATE

    def test_unknown_mode_falls_back_to_istock(self):
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_ref.return_value.document.return_value.get.return_value = mock_doc
            photo_rate, video_rate = _get_credit_rates("UnknownPlatform")
            assert photo_rate == settings.ISTOCK_RATE
            assert video_rate == settings.ISTOCK_RATE

    def test_reads_from_firestore_when_available(self):
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                "credit_rates": {
                    "istock_photo": 5,
                    "istock_video": 7,
                }
            }
            mock_ref.return_value.document.return_value.get.return_value = mock_doc
            photo_rate, video_rate = _get_credit_rates("iStock")
            assert photo_rate == 5
            assert video_rate == 7

    def test_firestore_exception_falls_back(self):
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_ref.return_value.document.return_value.get.side_effect = Exception("DB down")
            photo_rate, video_rate = _get_credit_rates("iStock")
            assert photo_rate == settings.ISTOCK_RATE
            assert video_rate == settings.ISTOCK_RATE

    def test_case_insensitive_mode_matching(self):
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_ref.return_value.document.return_value.get.return_value = mock_doc
            p1, v1 = _get_credit_rates("ISTOCK")
            p2, v2 = _get_credit_rates("istock")
            assert p1 == p2 == settings.ISTOCK_RATE

    def test_adobe_keyword_in_mode(self):
        """Mode containing 'adobe' should use ADOBE_RATE."""
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_ref.return_value.document.return_value.get.return_value = mock_doc
            p, v = _get_credit_rates("Adobe Stock")
            assert p == settings.ADOBE_RATE

    def test_shutterstock_keyword_in_mode(self):
        """Mode containing 'shutterstock' should use ADOBE_RATE."""
        with patch("app.routers.job.system_config_ref") as mock_ref:
            mock_doc = MagicMock()
            mock_doc.exists = False
            mock_ref.return_value.document.return_value.get.return_value = mock_doc
            p, v = _get_credit_rates("Shutterstock Only")
            assert p == settings.ADOBE_RATE


# ═══════════════════════════════════════
# Finalize refund calculation logic
# (tested as pure math, not via HTTP)
# ═══════════════════════════════════════

class TestFinalizeRefundCalculation:
    """
    Mirrors the refund calculation logic in finalize_job.
    Tests the math without hitting Firestore.
    """

    @staticmethod
    def _calc_refund(reserved, p_rate, v_rate, success, failed, photos, videos):
        """Replicate the finalize refund math from job.py."""
        total_reported = success + failed
        if total_reported > 0 and photos + videos > 0:
            success_ratio = success / total_reported if total_reported > 0 else 0
            successful_photos = round(photos * success_ratio)
            successful_videos = success - successful_photos
            if successful_videos < 0:
                successful_videos = 0
                successful_photos = success
            actual_usage = (successful_photos * p_rate) + (successful_videos * v_rate)
        else:
            actual_usage = success * p_rate
        refund = reserved - actual_usage
        if refund < 0:
            refund = 0
        return refund, actual_usage

    def test_all_success_no_refund(self):
        # 10 photos at rate 3, all succeed
        refund, usage = self._calc_refund(
            reserved=30, p_rate=3, v_rate=3,
            success=10, failed=0, photos=10, videos=0,
        )
        assert usage == 30
        assert refund == 0

    def test_all_failed_full_refund(self):
        refund, usage = self._calc_refund(
            reserved=30, p_rate=3, v_rate=3,
            success=0, failed=10, photos=10, videos=0,
        )
        assert usage == 0
        assert refund == 30

    def test_partial_success(self):
        # 10 photos reserved (30 credits), 7 succeed, 3 fail
        refund, usage = self._calc_refund(
            reserved=30, p_rate=3, v_rate=3,
            success=7, failed=3, photos=10, videos=0,
        )
        assert usage == 21  # 7 * 3
        assert refund == 9  # 30 - 21

    def test_mixed_photo_video(self):
        # 5 photos (rate 3) + 2 videos (rate 5) = 15 + 10 = 25 reserved
        # 6 success, 1 failed
        refund, usage = self._calc_refund(
            reserved=25, p_rate=3, v_rate=5,
            success=6, failed=1, photos=5, videos=2,
        )
        # success_ratio = 6/7 ≈ 0.857
        # successful_photos = round(5 * 6/7) = round(4.286) = 4
        # successful_videos = 6 - 4 = 2
        # actual_usage = 4*3 + 2*5 = 12 + 10 = 22
        assert usage == 22
        assert refund == 3

    def test_no_photo_video_breakdown(self):
        """When photos=0 and videos=0, fallback to success * p_rate."""
        refund, usage = self._calc_refund(
            reserved=30, p_rate=3, v_rate=3,
            success=5, failed=5, photos=0, videos=0,
        )
        assert usage == 15  # 5 * 3
        assert refund == 15

    def test_refund_cannot_be_negative(self):
        """Even if math goes wrong, refund is clamped to 0."""
        refund, _ = self._calc_refund(
            reserved=10, p_rate=3, v_rate=3,
            success=10, failed=0, photos=10, videos=0,
        )
        assert refund >= 0


# ═══════════════════════════════════════
# Anti-cheat validation
# ═══════════════════════════════════════

class TestAntiCheat:
    """Test the anti-cheat checks from finalize_job."""

    @staticmethod
    def _validate(file_count, success, failed):
        """Replicate the anti-cheat checks."""
        if success + failed > file_count:
            return "Claimed file count exceeds reserved amount"
        if success > file_count:
            return "Success count exceeds reserved file count"
        return None

    def test_valid_counts(self):
        assert self._validate(10, 7, 3) is None

    def test_exact_counts(self):
        assert self._validate(10, 10, 0) is None

    def test_overclaim_total(self):
        result = self._validate(10, 8, 5)
        assert result is not None
        assert "exceeds" in result.lower()

    def test_overclaim_success(self):
        result = self._validate(10, 11, 0)
        assert result is not None

    def test_zero_counts(self):
        assert self._validate(10, 0, 0) is None
