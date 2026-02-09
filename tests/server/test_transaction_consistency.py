"""
Transaction Consistency — Reserve-Refund Protocol

Verifies that credits are NEVER lost regardless of what happens between
reserve and finalize.  Each scenario follows the same pattern:

    1. Seed user with known balance
    2. POST /job/reserve  → credits locked (balance decreases)
    3. *something happens* (AI success, AI failure, timeout, partial, crash)
    4. POST /job/finalize  → unused credits refunded (balance restored)
    5. ASSERT: final balance == initial − actually_consumed

The golden rule:
    initial_balance == final_balance + actual_usage
    ⟹ credits are never created or destroyed, only moved.
"""
import copy
import pytest
from datetime import datetime, timezone

PREFIX = "/api/v1/job"


# ═══════════════════════════════════════════════════════════
# Scenario 1 — AI Failure: ALL files fail → FULL refund
#
#   User: 10 credits, cost: 5 credits (5 photos × rate 1)
#   Reserve → balance 5, locked 5
#   AI returns error for every file
#   Finalize(success=0, failed=5) → refund 5
#   Final balance: 10 (fully restored)
# ═══════════════════════════════════════════════════════════

class TestAIFailureFullRefund:

    def test_credits_never_lost_on_total_ai_failure(
        self, client, fake_db, seed_app_settings
    ):
        """
        End-to-end: 10 credits → reserve 5 → AI fails all → finalize → 10 credits.
        Credits must NEVER be lost due to AI errors.
        """
        from app.security import create_jwt_token, hash_password

        # ── Step 0: Seed user with exactly 10 credits ──
        user_id = "user-consistency-001"
        INITIAL_BALANCE = 10
        fake_db.collection("users")._store[user_id] = {
            "email": "consistency@test.com",
            "password_hash": hash_password("TestPass123"),
            "full_name": "Consistency Test",
            "hardware_id": "hw_consistency_test_1234567",
            "tier": "standard",
            "credits": INITIAL_BALANCE,
            "status": "active",
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "total_topup_baht": 0,
            "total_credits_used": 0,
            "app_version": "2.0.0",
            "metadata": {},
        }
        token = create_jwt_token(user_id, "consistency@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Override credit rates to 1 credit/file for easy math
        seed_app_settings["credit_rates"] = {
            "istock_photo": 1, "istock_video": 1,
            "adobe_photo": 1, "adobe_video": 1,
            "shutterstock_photo": 1, "shutterstock_video": 1,
        }

        # ── Step 1: Reserve 5 files → lock 5 credits ──
        reserve_resp = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 5,
            "mode": "iStock",
        })
        assert reserve_resp.status_code == 200
        reserve_data = reserve_resp.json()
        assert reserve_data["reserved_credits"] == 5
        job_token = reserve_data["job_token"]

        # Verify: balance decreased by 5
        db_user = fake_db.collection("users")._store[user_id]
        assert db_user["credits"] == 5, \
            f"After reserve: expected 5, got {db_user['credits']}"

        # ── Step 2: SIMULATE AI FAILURE ──
        # (The AI processing happens client-side. The server doesn't know
        #  about it. All the server sees is the finalize request.)
        # All 5 files failed. 0 succeeded.

        # ── Step 3: Finalize with 0 success, 5 failed → full refund ──
        finalize_resp = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 0,
            "failed": 5,
            "photos": 5,
            "videos": 0,
        })
        assert finalize_resp.status_code == 200
        finalize_data = finalize_resp.json()

        # ── Step 4: Verify credits fully restored ──
        assert finalize_data["refunded"] == 5, \
            f"Expected full refund of 5, got {finalize_data['refunded']}"
        assert finalize_data["balance"] == INITIAL_BALANCE, \
            f"Expected balance {INITIAL_BALANCE}, got {finalize_data['balance']}"

        # Double-check directly in DB
        final_credits = fake_db.collection("users")._store[user_id]["credits"]
        assert final_credits == INITIAL_BALANCE, \
            f"DB credits should be {INITIAL_BALANCE}, got {final_credits}"

        # ── Invariant: initial == final + actual_usage ──
        actual_usage = INITIAL_BALANCE - final_credits
        assert actual_usage == 0, "No credits should be consumed when all files fail"


# ═══════════════════════════════════════════════════════════
# Scenario 2 — AI Timeout / Client Crash: 0 success, 0 failed
#
#   The client crashed or timed out before processing ANY file.
#   Finalize(success=0, failed=0) → full refund of reserved credits.
# ═══════════════════════════════════════════════════════════

class TestClientCrashFullRefund:

    def test_credits_restored_on_client_crash(
        self, client, fake_db, seed_app_settings
    ):
        from app.security import create_jwt_token, hash_password

        user_id = "user-crash-001"
        INITIAL = 100
        fake_db.collection("users")._store[user_id] = {
            "email": "crash@test.com",
            "password_hash": hash_password("Pass123"),
            "full_name": "Crash Test",
            "hardware_id": "hw_crash_test_123456789012",
            "tier": "standard",
            "credits": INITIAL,
            "status": "active",
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "total_topup_baht": 0,
            "total_credits_used": 0,
            "app_version": "2.0.0",
            "metadata": {},
        }
        token = create_jwt_token(user_id, "crash@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Reserve 20 iStock files (rate=3) → cost 60
        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 20, "mode": "iStock",
        })
        assert r.status_code == 200
        job_token = r.json()["job_token"]
        reserved = r.json()["reserved_credits"]
        assert reserved == 60
        assert fake_db.collection("users")._store[user_id]["credits"] == 40

        # Client crashed — sends finalize with 0/0
        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 0,
            "failed": 0,
        })
        assert f.status_code == 200
        assert f.json()["refunded"] == 60
        assert f.json()["balance"] == INITIAL

        # DB invariant
        assert fake_db.collection("users")._store[user_id]["credits"] == INITIAL


# ═══════════════════════════════════════════════════════════
# Scenario 3 — Partial AI Failure: some succeed, some fail
#
#   User: 30 credits, reserve 10 iStock files (rate=3) → cost 30
#   AI succeeds on 6, fails on 4
#   actual_usage = 6×3 = 18, refund = 30−18 = 12
#   Final balance: 0 + 12 = 12
#   Invariant: 30 == 12 + 18 ✓
# ═══════════════════════════════════════════════════════════

class TestPartialAIFailure:

    def test_partial_failure_correct_refund(
        self, client, fake_db, seed_app_settings
    ):
        from app.security import create_jwt_token, hash_password

        user_id = "user-partial-001"
        INITIAL = 30
        fake_db.collection("users")._store[user_id] = {
            "email": "partial@test.com",
            "password_hash": hash_password("Pass123"),
            "full_name": "Partial Test",
            "hardware_id": "hw_partial_test_12345678901",
            "tier": "standard",
            "credits": INITIAL,
            "status": "active",
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "total_topup_baht": 0,
            "total_credits_used": 0,
            "app_version": "2.0.0",
            "metadata": {},
        }
        token = create_jwt_token(user_id, "partial@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Reserve 10 iStock photos (rate=3) → cost 30, balance → 0
        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        assert r.status_code == 200
        job_token = r.json()["job_token"]
        assert r.json()["reserved_credits"] == 30
        assert fake_db.collection("users")._store[user_id]["credits"] == 0

        # AI: 6 success, 4 failed
        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 6,
            "failed": 4,
            "photos": 10,
            "videos": 0,
        })
        assert f.status_code == 200

        refunded = f.json()["refunded"]
        final_balance = f.json()["balance"]
        actual_usage = INITIAL - final_balance

        # refund = reserved(30) − actual(6×3=18) = 12
        assert refunded == 12
        assert final_balance == 12

        # ── THE INVARIANT ──
        assert INITIAL == final_balance + actual_usage
        assert actual_usage == 18


# ═══════════════════════════════════════════════════════════
# Scenario 4 — All Success: zero refund
#
#   User: 500 credits, reserve 10 iStock (rate=3) → cost 30
#   All 10 succeed → actual_usage = 30, refund = 0
#   Final balance: 470
#   Invariant: 500 == 470 + 30 ✓
# ═══════════════════════════════════════════════════════════

class TestAllSuccessZeroRefund:

    def test_all_success_no_credits_lost(
        self, client, auth_header, seed_user, fake_db, seed_app_settings
    ):
        user_id, _, _ = seed_user
        INITIAL = 500

        r = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        assert r.status_code == 200
        job_token = r.json()["job_token"]
        assert r.json()["reserved_credits"] == 30
        assert fake_db.collection("users")._store[user_id]["credits"] == 470

        f = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 10,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        assert f.status_code == 200
        assert f.json()["refunded"] == 0
        assert f.json()["balance"] == 470

        # Invariant
        final = fake_db.collection("users")._store[user_id]["credits"]
        assert INITIAL == final + 30


# ═══════════════════════════════════════════════════════════
# Scenario 5 — Mixed Photo/Video with AI failure
#
#   User: 100 credits
#   Reserve 10 files (7 photos + 3 videos), iStock rate=3
#   Cost = (7+3)×3 = 30, balance → 70
#   AI: 5 success, 5 failed (proportional: ~3.5 photo success, ~1.5 video)
#   Refund = reserved − actual_usage
#   Invariant: 100 == final_balance + actual_usage
# ═══════════════════════════════════════════════════════════

class TestMixedPhotoVideoFailure:

    def test_mixed_media_refund_consistency(
        self, client, fake_db, seed_app_settings
    ):
        from app.security import create_jwt_token, hash_password

        user_id = "user-mixed-001"
        INITIAL = 100
        fake_db.collection("users")._store[user_id] = {
            "email": "mixed@test.com",
            "password_hash": hash_password("Pass123"),
            "full_name": "Mixed Test",
            "hardware_id": "hw_mixed_test_1234567890123",
            "tier": "standard",
            "credits": INITIAL,
            "status": "active",
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "total_topup_baht": 0,
            "total_credits_used": 0,
            "app_version": "2.0.0",
            "metadata": {},
        }
        token = create_jwt_token(user_id, "mixed@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Reserve 10 files (7p + 3v) at iStock rate=3 → cost 30
        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10,
            "photo_count": 7,
            "video_count": 3,
            "mode": "iStock",
        })
        assert r.status_code == 200
        job_token = r.json()["job_token"]
        reserved = r.json()["reserved_credits"]
        assert reserved == 30
        assert fake_db.collection("users")._store[user_id]["credits"] == 70

        # AI: 5 success, 5 failed
        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 5,
            "failed": 5,
            "photos": 7,
            "videos": 3,
        })
        assert f.status_code == 200

        refunded = f.json()["refunded"]
        final_balance = f.json()["balance"]
        actual_usage = reserved - refunded

        # ── THE INVARIANT: no credits created or destroyed ──
        assert final_balance == INITIAL - actual_usage, \
            f"Invariant violated: {INITIAL} != {final_balance} + {actual_usage}"
        assert refunded >= 0, "Refund must never be negative"
        assert actual_usage >= 0, "Usage must never be negative"
        assert actual_usage <= reserved, "Usage cannot exceed reserved amount"


# ═══════════════════════════════════════════════════════════
# Scenario 6 — Double Finalize (Idempotency)
#
#   Client sends finalize twice (e.g. network retry).
#   Second call must NOT double-refund.
# ═══════════════════════════════════════════════════════════

class TestDoubleFinalize:

    def test_double_finalize_no_double_refund(
        self, client, auth_header, seed_user, fake_db, seed_app_settings
    ):
        user_id, _, _ = seed_user
        INITIAL = 500

        r = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = r.json()["job_token"]

        # First finalize: 5 success, 5 failed → refund 15
        f1 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 5, "failed": 5,
            "photos": 10, "videos": 0,
        })
        assert f1.status_code == 200
        first_refund = f1.json()["refunded"]
        first_balance = f1.json()["balance"]
        assert first_refund == 15

        # Second finalize (duplicate/retry)
        f2 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 10, "failed": 0,  # different numbers — should be ignored
            "photos": 10, "videos": 0,
        })
        assert f2.status_code == 200
        # Must return the SAME refund as first call
        assert f2.json()["refunded"] == first_refund
        # Balance must not have changed
        assert f2.json()["balance"] == first_balance

        # DB must match
        final_credits = fake_db.collection("users")._store[user_id]["credits"]
        assert final_credits == first_balance, \
            "Double finalize must not create extra credits"


# ═══════════════════════════════════════════════════════════
# Scenario 7 — Sequential Jobs: balance tracks correctly
#
#   Job 1: reserve → all fail → full refund
#   Job 2: reserve → all success → zero refund
#   Final balance must equal initial − job2_cost
# ═══════════════════════════════════════════════════════════

class TestSequentialJobs:

    def test_sequential_jobs_balance_integrity(
        self, client, auth_header, seed_user, fake_db, seed_app_settings
    ):
        user_id, _, _ = seed_user
        INITIAL = 500

        # ── Job 1: 10 files, ALL FAIL → full refund ──
        r1 = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        t1 = r1.json()["job_token"]
        assert fake_db.collection("users")._store[user_id]["credits"] == 470

        f1 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": t1, "success": 0, "failed": 10,
            "photos": 10, "videos": 0,
        })
        assert f1.json()["refunded"] == 30
        assert f1.json()["balance"] == 500  # fully restored

        # ── Job 2: 5 files, ALL SUCCESS → zero refund ──
        r2 = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        t2 = r2.json()["job_token"]
        assert fake_db.collection("users")._store[user_id]["credits"] == 485

        f2 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": t2, "success": 5, "failed": 0,
            "photos": 5, "videos": 0,
        })
        assert f2.json()["refunded"] == 0
        assert f2.json()["balance"] == 485

        # ── Final invariant ──
        final = fake_db.collection("users")._store[user_id]["credits"]
        total_consumed = 15  # only job 2 consumed credits (5×3)
        assert final == INITIAL - total_consumed


# ═══════════════════════════════════════════════════════════
# Scenario 8 — Expired Job: server auto-refunds
#
#   Client never calls finalize (network died completely).
#   Server cleanup cron refunds the full reserved amount.
# ═══════════════════════════════════════════════════════════

class TestExpiredJobAutoRefund:

    def test_expired_job_credits_restored(self, client, fake_db):
        from app.security import create_jwt_token, hash_password
        from datetime import timedelta

        user_id = "user-expire-001"
        INITIAL = 50
        fake_db.collection("users")._store[user_id] = {
            "email": "expire@test.com",
            "password_hash": hash_password("Pass123"),
            "full_name": "Expire Test",
            "hardware_id": "hw_expire_test_12345678901",
            "tier": "standard",
            "credits": INITIAL,
            "status": "active",
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "total_topup_baht": 0,
            "total_credits_used": 0,
            "app_version": "2.0.0",
            "metadata": {},
        }

        # Simulate: job was reserved but client never finalized
        # Manually insert an expired RESERVED job
        now = datetime.now(timezone.utc)
        fake_db.collection("jobs")._store["job-expired-test"] = {
            "job_token": "expired-token-consistency",
            "user_id": user_id,
            "status": "RESERVED",
            "reserved_credits": 15,
            "expires_at": now - timedelta(hours=1),  # already expired
        }
        # Simulate that credits were already deducted during reserve
        fake_db.collection("users")._store[user_id]["credits"] = INITIAL - 15  # 35

        # Server cleanup cron runs
        resp = client.post("/api/v1/system/cleanup-expired-jobs")
        assert resp.status_code == 200
        assert resp.json()["cleaned"] == 1

        # Credits must be fully restored
        final = fake_db.collection("users")._store[user_id]["credits"]
        assert final == INITIAL, \
            f"After expiry cleanup: expected {INITIAL}, got {final}"

        # Job status must be EXPIRED
        job = fake_db.collection("jobs")._store["job-expired-test"]
        assert job["status"] == "EXPIRED"
