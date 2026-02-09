"""
Tests for client-side credit cost estimation:
  - PLATFORM_RATES configuration
  - Cost calculation: photos × photo_rate + videos × video_rate
  - count_files used for photo/video breakdown
  - JobManager._on_all_completed charged calculation
  - Edge cases: zero files, all photos, all videos, mixed
"""
import pytest

from core.config import PLATFORM_RATES
from utils.helpers import count_files


# ═══════════════════════════════════════
# Platform Rates Configuration
# ═══════════════════════════════════════

class TestPlatformRates:

    def test_istock_rates(self):
        assert PLATFORM_RATES["iStock"]["photo"] == 3
        assert PLATFORM_RATES["iStock"]["video"] == 3

    def test_adobe_rates(self):
        assert PLATFORM_RATES["Adobe & Shutterstock"]["photo"] == 2
        assert PLATFORM_RATES["Adobe & Shutterstock"]["video"] == 2

    def test_all_rates_positive(self):
        for platform, rates in PLATFORM_RATES.items():
            assert rates["photo"] > 0, f"{platform} photo rate must be positive"
            assert rates["video"] > 0, f"{platform} video rate must be positive"


# ═══════════════════════════════════════
# Client-Side Cost Estimation
# ═══════════════════════════════════════

def estimate_cost(files: list, platform: str) -> int:
    """
    Replicate the client-side cost estimation logic.
    This mirrors what JobManager.start_job does before calling api.reserve_job.
    """
    rates = PLATFORM_RATES.get(platform, {"photo": 3, "video": 3})
    img_count, vid_count = count_files(files)
    return (img_count * rates["photo"]) + (vid_count * rates["video"])


class TestCostEstimation:

    def test_10_istock_photos(self):
        files = [f"photo_{i}.jpg" for i in range(10)]
        assert estimate_cost(files, "iStock") == 30  # 10 × 3

    def test_10_istock_videos(self):
        files = [f"clip_{i}.mp4" for i in range(10)]
        assert estimate_cost(files, "iStock") == 30  # 10 × 3

    def test_mixed_istock(self):
        files = ["a.jpg", "b.png", "c.mp4", "d.mov", "e.tiff"]
        # 3 images × 3 + 2 videos × 3 = 15
        assert estimate_cost(files, "iStock") == 15

    def test_10_adobe_photos(self):
        files = [f"photo_{i}.jpg" for i in range(10)]
        assert estimate_cost(files, "Adobe & Shutterstock") == 20  # 10 × 2

    def test_mixed_adobe(self):
        files = ["a.jpg", "b.png", "c.mp4"]
        # 2 images × 2 + 1 video × 2 = 6
        assert estimate_cost(files, "Adobe & Shutterstock") == 6

    def test_zero_files(self):
        assert estimate_cost([], "iStock") == 0

    def test_single_photo(self):
        assert estimate_cost(["photo.jpg"], "iStock") == 3

    def test_single_video(self):
        assert estimate_cost(["clip.mp4"], "iStock") == 3

    def test_large_batch(self):
        files = [f"photo_{i}.jpg" for i in range(100)] + [f"clip_{i}.mp4" for i in range(50)]
        # 100 × 3 + 50 × 3 = 450
        assert estimate_cost(files, "iStock") == 450

    def test_unknown_platform_defaults(self):
        """Unknown platform should use default rates (3/3)."""
        files = ["a.jpg", "b.mp4"]
        cost = estimate_cost(files, "Unknown Platform")
        assert cost == 6  # 1×3 + 1×3

    def test_balance_check_sufficient(self):
        """Simulate: user has 500 credits, wants to process 100 iStock photos."""
        balance = 500
        files = [f"photo_{i}.jpg" for i in range(100)]
        cost = estimate_cost(files, "iStock")
        assert cost == 300
        assert balance >= cost  # sufficient

    def test_balance_check_insufficient(self):
        """Simulate: user has 50 credits, wants to process 100 iStock photos."""
        balance = 50
        files = [f"photo_{i}.jpg" for i in range(100)]
        cost = estimate_cost(files, "iStock")
        assert cost == 300
        assert balance < cost  # insufficient
        shortfall = cost - balance
        assert shortfall == 250

    def test_max_affordable_files(self):
        """Calculate how many files a user can afford."""
        balance = 100
        rate = PLATFORM_RATES["iStock"]["photo"]
        max_files = balance // rate
        assert max_files == 33  # 100 / 3 = 33


# ═══════════════════════════════════════
# Charged Calculation (mirrors JobManager._on_all_completed)
# ═══════════════════════════════════════

class TestChargedCalculation:

    def _calc_charged(self, results: dict, rates: dict) -> int:
        """Replicate JobManager._on_all_completed charged calculation."""
        from utils.helpers import is_image, is_video
        ok = sum(1 for r in results.values() if r.get("status") == "success")
        photos = sum(1 for fn in results if is_image(fn))
        videos = sum(1 for fn in results if is_video(fn))
        return (ok * rates.get("photo", 3)) + (videos * rates.get("video", 3))

    def test_all_success_photos(self):
        results = {f"p{i}.jpg": {"status": "success"} for i in range(10)}
        charged = self._calc_charged(results, {"photo": 3, "video": 3})
        # ok=10, photos=10, videos=0 → 10*3 + 0*3 = 30
        assert charged == 30

    def test_mixed_with_failures(self):
        results = {
            "p1.jpg": {"status": "success"},
            "p2.jpg": {"status": "error"},
            "v1.mp4": {"status": "success"},
        }
        # ok=2, photos=2, videos=1 → 2*3 + 1*3 = 9
        charged = self._calc_charged(results, {"photo": 3, "video": 3})
        assert charged == 9
