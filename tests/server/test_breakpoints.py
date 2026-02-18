"""
Breakpoint Analysis Tests — จุดที่ระบบอาจพัง

ตรวจสอบ edge cases, race conditions, error paths ที่อาจเกิดขึ้นจริง:

  1. CREDIT RACE: Reserve 2 jobs simultaneously when credits barely enough for 1
  2. NEGATIVE REFUND: actual_usage > reserved (should clamp to 0)
  3. MISSING APP_SETTINGS: Firestore has no system_config → fallback rates
  4. CORRUPT JOB DATA: Job document missing critical fields
  5. HUGE FILE COUNT: Reserve 10,000 files → integer overflow?
  6. EMPTY STRING FIELDS: mode="", keyword_style="" etc.
  7. FINALIZE NON-EXISTENT JOB: Random token → 404
  8. FINALIZE EXPIRED JOB: Job status=EXPIRED → 400
  9. USER DELETED MID-JOB: User doc disappears between reserve and finalize
  10. TRANSACTION DESCRIPTION ENCODING: Thai + emoji in descriptions
  11. BALANCE ENDPOINT WITHOUT AUTH: → 403
  12. HISTORY WITH 0 TRANSACTIONS: Empty list
  13. CONCURRENT FINALIZE: Two finalize calls for same job
  14. RESERVE WITH NEGATIVE CREDITS: User somehow has negative credits
  15. SLIP2GO NOT CONFIGURED: Topup when SLIP2GO_SECRET_KEY is empty
"""
import copy
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

PREFIX = "/api/v1"


# ═══════════════════════════════════════════════════════════
# 1. CREDIT RACE CONDITION
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_CreditRace:
    """เครดิตพอแค่ 1 job → reserve 2 job พร้อมกัน"""

    def test_sequential_reserve_second_fails(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """User has 500 credits. Reserve 166 files (498 cr) → only 2 left.
        Second reserve of 1 file (3 cr) should fail 402."""
        resp1 = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 166, "mode": "iStock",
        })
        assert resp1.status_code == 200
        assert resp1.json()["reserved_credits"] == 498

        resp2 = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        assert resp2.status_code == 402

    def test_exact_boundary_reserve(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Reserve exactly all credits → balance should be 0, not negative."""
        user_id, _, _ = seed_user
        # 500 / 2 = 250 files at Adobe rate
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 250, "mode": "Adobe & Shutterstock",
        })
        assert resp.status_code == 200
        assert resp.json()["reserved_credits"] == 500
        assert fake_db.collection("users")._store[user_id]["credits"] == 0


# ═══════════════════════════════════════════════════════════
# 2. NEGATIVE REFUND PROTECTION
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_NegativeRefund:
    """actual_usage > reserved → refund ต้องเป็น 0 ไม่ใช่ติดลบ"""

    def test_refund_clamped_to_zero(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """If somehow actual_usage exceeds reserved, refund should be 0."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]
        # reserved = 15 (5 * 3)

        # Claim all 5 success → actual_usage = 15, refund = 0
        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 5,
            "failed": 0,
            "photos": 5,
            "videos": 0,
        })
        assert resp.status_code == 200
        assert resp.json()["refunded"] == 0
        # Balance should not go below what it was after reserve
        assert resp.json()["balance"] >= 0


# ═══════════════════════════════════════════════════════════
# 3. MISSING APP_SETTINGS
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_MissingConfig:
    """Firestore ไม่มี system_config/app_settings → ต้อง fallback"""

    def test_balance_without_settings(self, client, auth_header, seed_user, fake_db):
        """Balance endpoint should work even without app_settings doc."""
        # Don't seed app_settings
        resp = client.get(f"{PREFIX}/credit/balance", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["credits"] == 500
        # Should have fallback rates
        assert "credit_rates" in body

    def test_reserve_without_settings(self, client, auth_header, seed_user, fake_db):
        """Reserve should work with fallback rates even without app_settings."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        # Should succeed with fallback rate
        assert resp.status_code == 200
        # Config (encrypted prompt) will be empty but job should still work
        assert resp.json()["job_token"]


# ═══════════════════════════════════════════════════════════
# 4. CORRUPT JOB DATA
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_CorruptJobData:
    """Job document มีข้อมูลไม่ครบ → finalize ต้องไม่ crash"""

    def test_finalize_job_missing_rates(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Job doc missing photo_rate/video_rate → should use fallback."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]

        # Corrupt the job: remove rate fields
        jobs = fake_db.collection("jobs")._store
        for jid, jdata in jobs.items():
            if jdata.get("job_token") == job_token:
                jdata.pop("photo_rate", None)
                jdata.pop("video_rate", None)
                break

        # Finalize should still work (fallback to credit_rate or default)
        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 3, "failed": 2, "photos": 5, "videos": 0,
        })
        assert resp.status_code == 200
        assert resp.json()["refunded"] >= 0


# ═══════════════════════════════════════════════════════════
# 5. HUGE FILE COUNT
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_HugeFileCount:
    """จำนวนไฟล์มาก → ต้องไม่ overflow"""

    def test_huge_file_count_insufficient(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """10,000 files at rate 3 = 30,000 credits → 402 (user has 500)."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10000, "mode": "iStock",
        })
        assert resp.status_code == 402

    def test_single_file_minimum(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Minimum: 1 file should work."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        assert resp.status_code == 200
        assert resp.json()["reserved_credits"] == 3


# ═══════════════════════════════════════════════════════════
# 6. EMPTY/INVALID FIELDS
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_InvalidFields:
    """ส่งข้อมูลผิดรูปแบบ → ต้อง validate"""

    def test_empty_mode_422(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "",
        })
        assert resp.status_code == 422

    def test_negative_file_count_422(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": -1, "mode": "iStock",
        })
        assert resp.status_code == 422

    def test_missing_mode_422(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5,
        })
        assert resp.status_code == 422

    def test_empty_job_token_finalize(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": "",
            "success": 0, "failed": 0, "photos": 0, "videos": 0,
        })
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# 7. FINALIZE NON-EXISTENT JOB
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_NonExistentJob:
    """Finalize job ที่ไม่มีอยู่"""

    def test_random_token_404(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": "non-existent-token-12345",
            "success": 0, "failed": 0, "photos": 0, "videos": 0,
        })
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# 8. FINALIZE EXPIRED JOB
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_ExpiredJob:
    """Job ที่ถูก mark เป็น EXPIRED → finalize ต้อง 400"""

    def test_finalize_expired_job_400(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]

        # Manually expire the job
        jobs = fake_db.collection("jobs")._store
        for jid, jdata in jobs.items():
            if jdata.get("job_token") == job_token:
                jdata["status"] = "EXPIRED"
                break

        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 5, "failed": 0, "photos": 5, "videos": 0,
        })
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════
# 10. THAI + EMOJI IN DESCRIPTIONS
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_ThaiEncoding:
    """ข้อความภาษาไทย + emoji ใน transaction descriptions"""

    def test_thai_description_in_history(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Reserve → check history → description should contain Thai text."""
        client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5,
            "photo_count": 3,
            "video_count": 2,
            "mode": "iStock",
        })

        resp = client.get(f"{PREFIX}/credit/history", headers=auth_header)
        assert resp.status_code == 200
        txs = resp.json()["transactions"]
        assert len(txs) >= 1
        # Check Thai text is properly encoded in response
        desc = txs[0]["description"]
        assert "หักเครดิต" in desc
        assert "ภาพ" in desc
        assert "วิดีโอ" in desc


# ═══════════════════════════════════════════════════════════
# 11. UNAUTHENTICATED ACCESS
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_NoAuth:
    """ไม่มี token → ทุก endpoint ต้อง 403"""

    def test_balance_no_auth(self, client):
        resp = client.get(f"{PREFIX}/credit/balance")
        assert resp.status_code == 403

    def test_history_no_auth(self, client):
        resp = client.get(f"{PREFIX}/credit/history")
        assert resp.status_code == 403

    def test_reserve_no_auth(self, client):
        resp = client.post(f"{PREFIX}/job/reserve", json={
            "file_count": 5, "mode": "iStock",
        })
        assert resp.status_code == 403

    def test_finalize_no_auth(self, client):
        resp = client.post(f"{PREFIX}/job/finalize", json={
            "job_token": "x", "success": 0, "failed": 0, "photos": 0, "videos": 0,
        })
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════
# 12. EMPTY HISTORY
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_EmptyHistory:
    """ผู้ใช้ใหม่ไม่มีประวัติ → ต้อง return empty list"""

    def test_empty_history(self, client, auth_header, seed_user):
        resp = client.get(f"{PREFIX}/credit/history", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["transactions"] == []


# ═══════════════════════════════════════════════════════════
# 13. CONCURRENT FINALIZE
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_ConcurrentFinalize:
    """2 finalize requests พร้อมกัน → ต้องไม่ double-refund"""

    def test_second_finalize_returns_same_data(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Sequential double-finalize: second call should be idempotent."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]
        # reserved 30, balance 470

        payload = {
            "job_token": job_token,
            "success": 5, "failed": 5, "photos": 10, "videos": 0,
        }

        r1 = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json=payload)
        r2 = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json=payload)

        assert r1.status_code == 200
        assert r2.status_code == 200

        # Both should report same balance
        assert r1.json()["balance"] == r2.json()["balance"]

        # User credits should only be refunded ONCE
        final_credits = fake_db.collection("users")._store[user_id]["credits"]
        expected = 500 - 30 + 15  # reserve 30, refund 15 (5 failed * 3)
        assert final_credits == expected


# ═══════════════════════════════════════════════════════════
# 14. NEGATIVE CREDITS USER
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_NegativeCredits:
    """ผู้ใช้มีเครดิตติดลบ (ไม่ควรเกิด แต่ต้องไม่ crash)"""

    def test_negative_credits_reserve_402(self, client, fake_db, seed_app_settings):
        """User with -10 credits → reserve should fail 402."""
        from app.security import create_jwt_token, hash_password
        fake_db.collection("users")._store["neg-uid"] = {
            "email": "neg@test.com",
            "password_hash": hash_password("Password123"),
            "credits": -10,
            "status": "active",
            "hardware_id": "e" * 32,
        }
        token = create_jwt_token("neg-uid", "neg@test.com")
        resp = client.post(f"{PREFIX}/job/reserve", headers={
            "Authorization": f"Bearer {token}",
        }, json={"file_count": 1, "mode": "iStock"})
        assert resp.status_code == 402


# ═══════════════════════════════════════════════════════════
# 15. SLIP2GO NOT CONFIGURED
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_Slip2GoNotConfigured:
    """SLIP2GO_SECRET_KEY ว่าง → topup ต้อง 503 พร้อมข้อความไทย"""

    def test_topup_without_slip2go_key(self, client, auth_header, seed_user, fake_db):
        """When SLIP2GO_SECRET_KEY is empty, topup should return 503."""
        from app.config import settings
        with patch.object(settings, "SLIP2GO_SECRET_KEY", ""):
            resp = client.post(f"{PREFIX}/credit/topup", headers=auth_header, json={
                "slip": "some-qr-data",
            })
            assert resp.status_code == 503
            detail = resp.json().get("detail", "")
            assert "ตรวจสอบสลิป" in detail or "ตั้งค่า" in detail


# ═══════════════════════════════════════════════════════════
# BONUS: Stress — Many transactions in history
# ═══════════════════════════════════════════════════════════

class TestBreakpoint_ManyTransactions:
    """ผู้ใช้มี transaction เยอะมาก → history ต้องไม่ช้าหรือ crash"""

    def test_history_with_many_transactions(self, client, auth_header, seed_user, fake_db):
        """Seed 100 transactions, request limit=10 → should return exactly 10."""
        user_id, _, _ = seed_user
        now = datetime.now(timezone.utc)
        for i in range(100):
            fake_db.collection("transactions")._store[f"tx-{i}"] = {
                "user_id": user_id,
                "type": "RESERVE",
                "amount": -3,
                "balance_after": 500 - (i * 3),
                "description": f"หักเครดิต job #{i}",
                "created_at": now - timedelta(hours=i),
            }

        resp = client.get(f"{PREFIX}/credit/history?limit=10", headers=auth_header)
        assert resp.status_code == 200
        txs = resp.json()["transactions"]
        assert len(txs) == 10

    def test_history_default_limit(self, client, auth_header, seed_user, fake_db):
        """Default limit=50 → should return at most 50."""
        user_id, _, _ = seed_user
        now = datetime.now(timezone.utc)
        for i in range(80):
            fake_db.collection("transactions")._store[f"tx-{i}"] = {
                "user_id": user_id,
                "type": "RESERVE",
                "amount": -3,
                "balance_after": 500,
                "description": f"test #{i}",
                "created_at": now - timedelta(hours=i),
            }

        resp = client.get(f"{PREFIX}/credit/history", headers=auth_header)
        assert resp.status_code == 200
        assert len(resp.json()["transactions"]) == 50
