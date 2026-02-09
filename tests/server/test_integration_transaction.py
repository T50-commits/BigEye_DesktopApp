"""
Critical Integration Test — Reserve-Refund Credit Logic

Your app prevents credit loss with this protocol:
    1. RESERVE  — Lock credits upfront  (POST /job/reserve)
    2. GENERATE — Client-side AI processing (no server call)
    3. FINALIZE — Commit or Refund        (POST /job/finalize)
       • success=N, failed=0  → COMMIT:  credits permanently consumed
       • success=0, failed=N  → REFUND:  credits fully restored
       • partial              → partial refund for failed files

NOTE: Your API uses a single /job/finalize endpoint (not separate
/job/commit and /job/refund). The `success` and `failed` counts
determine whether credits are committed or refunded.

Each test verifies the DB state at every step, not just the HTTP response.
"""
import copy
import pytest
from datetime import datetime, timezone

from app.security import create_jwt_token, hash_password

PREFIX = "/api/v1/job"


# ── Helper: seed a user with exact balance ──

def _seed_user(fake_db, user_id: str, credits: int):
    """Insert a user with a specific credit balance into the fake DB."""
    fake_db.collection("users")._store[user_id] = {
        "email": f"{user_id}@test.com",
        "password_hash": hash_password("TestPass123"),
        "full_name": "Transaction Test",
        "hardware_id": f"hw_{user_id}_1234567890123456",
        "tier": "standard",
        "credits": credits,
        "status": "active",
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "total_topup_baht": 0,
        "total_credits_used": 0,
        "app_version": "2.0.0",
        "metadata": {},
    }
    token = create_jwt_token(user_id, f"{user_id}@test.com")
    return {"Authorization": f"Bearer {token}"}


def _db_credits(fake_db, user_id: str) -> int:
    """Read current credits directly from the fake Firestore."""
    return fake_db.collection("users")._store[user_id]["credits"]


def _db_job(fake_db, job_token: str) -> dict:
    """Find a job document by its token."""
    for doc in fake_db.collection("jobs")._store.values():
        if doc.get("job_token") == job_token:
            return doc
    return {}


# ═══════════════════════════════════════════════════════════
# Test Case 1: Failed AI Generation → Full Refund
#
#   Setup:  User has 100 credits
#   Step 1: Reserve 10 credits → Balance=90, Locked=10
#   Step 2: AI generation fails (simulated — no server call)
#   Step 3: Finalize(success=0, failed=all) → Balance=100, Locked=0
#
#   Result: Credits fully restored. Zero loss.
# ═══════════════════════════════════════════════════════════

class TestFailedAIGenerationRefund:

    def test_full_refund_on_ai_failure(self, client, fake_db, seed_app_settings):
        """
        Complete flow: reserve → AI fails → finalize(0 success) → full refund.
        Credits must return to exactly 100.
        """
        INITIAL_BALANCE = 100
        user_id = "user-refund-flow"
        headers = _seed_user(fake_db, user_id, INITIAL_BALANCE)

        # Override rates to 1 credit/file for clear math
        seed_app_settings["credit_rates"]["istock_photo"] = 1
        seed_app_settings["credit_rates"]["istock_video"] = 1

        # ── Step 1: RESERVE (lock 10 credits) ──
        reserve_resp = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10,
            "mode": "iStock",
        })
        assert reserve_resp.status_code == 200, \
            f"Reserve failed: {reserve_resp.json()}"

        reserve_data = reserve_resp.json()
        job_token = reserve_data["job_token"]
        reserved_credits = reserve_data["reserved_credits"]
        assert reserved_credits == 10, \
            f"Expected 10 credits reserved, got {reserved_credits}"

        # Verify DB state after reserve:
        #   Balance = 100 - 10 = 90 (credits deducted upfront)
        #   Job status = RESERVED
        assert _db_credits(fake_db, user_id) == 90, \
            f"After reserve: expected 90, got {_db_credits(fake_db, user_id)}"

        job = _db_job(fake_db, job_token)
        assert job["status"] == "RESERVED"
        assert job["reserved_credits"] == 10

        # Verify RESERVE transaction was recorded
        txs = fake_db.collection("transactions")._store
        reserve_txs = [t for t in txs.values() if t.get("type") == "RESERVE"]
        assert len(reserve_txs) == 1
        assert reserve_txs[0]["amount"] == -10  # negative = deduction

        # ── Step 2: SIMULATE AI FAILURE ──
        # (This happens client-side. The server has no knowledge of it.
        #  The client simply calls finalize with success=0.)

        # ── Step 3: FINALIZE / REFUND (all failed) ──
        finalize_resp = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 0,
            "failed": 10,
            "photos": 10,
            "videos": 0,
        })
        assert finalize_resp.status_code == 200, \
            f"Finalize failed: {finalize_resp.json()}"

        finalize_data = finalize_resp.json()

        # Verify refund amount
        assert finalize_data["refunded"] == 10, \
            f"Expected full refund of 10, got {finalize_data['refunded']}"

        # Verify final balance via API response
        assert finalize_data["balance"] == INITIAL_BALANCE, \
            f"Expected balance {INITIAL_BALANCE}, got {finalize_data['balance']}"

        # Verify DB state after refund:
        #   Balance = 100 (fully restored)
        #   Job status = COMPLETED
        #   Locked = 0 (no outstanding reservations)
        assert _db_credits(fake_db, user_id) == INITIAL_BALANCE, \
            f"DB credits should be {INITIAL_BALANCE}, got {_db_credits(fake_db, user_id)}"

        job = _db_job(fake_db, job_token)
        assert job["status"] == "COMPLETED"
        assert job["refund_amount"] == 10
        assert job["actual_usage"] == 0

        # Verify REFUND transaction was recorded
        refund_txs = [t for t in txs.values() if t.get("type") == "REFUND"]
        assert len(refund_txs) == 1
        assert refund_txs[0]["amount"] == 10  # positive = credit back
        assert refund_txs[0]["balance_after"] == INITIAL_BALANCE

        # ── INVARIANT: no credits created or destroyed ──
        assert INITIAL_BALANCE == _db_credits(fake_db, user_id)

    def test_refund_with_rate3_istock(self, client, fake_db, seed_app_settings):
        """
        Same flow but with default iStock rate=3.
        Reserve 10 files × 3 = 30 credits locked.
        AI fails all → refund 30 → balance restored.
        """
        INITIAL = 100
        user_id = "user-refund-rate3"
        headers = _seed_user(fake_db, user_id, INITIAL)

        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        assert r.status_code == 200
        assert r.json()["reserved_credits"] == 30  # 10 × 3
        assert _db_credits(fake_db, user_id) == 70

        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": r.json()["job_token"],
            "success": 0, "failed": 10,
            "photos": 10, "videos": 0,
        })
        assert f.status_code == 200
        assert f.json()["refunded"] == 30
        assert f.json()["balance"] == INITIAL
        assert _db_credits(fake_db, user_id) == INITIAL

    def test_refund_on_client_crash_zero_processed(self, client, fake_db, seed_app_settings):
        """
        Edge case: client crashes before processing any file.
        Finalize with success=0, failed=0 → full refund.
        """
        INITIAL = 100
        user_id = "user-crash-refund"
        headers = _seed_user(fake_db, user_id, INITIAL)

        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 5, "mode": "iStock",
        })
        assert r.status_code == 200
        reserved = r.json()["reserved_credits"]  # 5 × 3 = 15
        assert _db_credits(fake_db, user_id) == INITIAL - reserved

        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": r.json()["job_token"],
            "success": 0, "failed": 0,  # nothing processed
        })
        assert f.status_code == 200
        assert f.json()["refunded"] == reserved
        assert _db_credits(fake_db, user_id) == INITIAL


# ═══════════════════════════════════════════════════════════
# Test Case 2: Successful AI Generation → Commit (Burn)
#
#   Setup:  User has 100 credits
#   Step 1: Reserve 10 credits → Balance=90, Locked=10
#   Step 2: AI succeeds on all files
#   Step 3: Finalize(success=all, failed=0) → Balance=90, Locked=0
#
#   Result: Credits permanently consumed. Zero refund.
# ═══════════════════════════════════════════════════════════

class TestSuccessfulGenerationCommit:

    def test_commit_on_full_success(self, client, fake_db, seed_app_settings):
        """
        Complete flow: reserve → AI succeeds all → finalize(all success) → commit.
        Credits permanently consumed, balance stays at 90.
        """
        INITIAL_BALANCE = 100
        user_id = "user-commit-flow"
        headers = _seed_user(fake_db, user_id, INITIAL_BALANCE)

        # Override rates to 1 for clear math
        seed_app_settings["credit_rates"]["istock_photo"] = 1
        seed_app_settings["credit_rates"]["istock_video"] = 1

        # ── Step 1: RESERVE (lock 10 credits) ──
        reserve_resp = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10,
            "mode": "iStock",
        })
        assert reserve_resp.status_code == 200
        job_token = reserve_resp.json()["job_token"]
        assert reserve_resp.json()["reserved_credits"] == 10
        assert _db_credits(fake_db, user_id) == 90

        # ── Step 2: AI SUCCEEDS (client-side, no server call) ──

        # ── Step 3: FINALIZE / COMMIT (all success) ──
        finalize_resp = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 10,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        assert finalize_resp.status_code == 200

        finalize_data = finalize_resp.json()

        # Zero refund — credits permanently consumed
        assert finalize_data["refunded"] == 0, \
            f"Expected 0 refund (commit), got {finalize_data['refunded']}"

        # Balance stays at 90
        assert finalize_data["balance"] == 90, \
            f"Expected balance 90 (committed), got {finalize_data['balance']}"

        # Verify DB state:
        #   Balance = 90 (permanently consumed)
        #   Job status = COMPLETED
        #   actual_usage = 10 (all credits consumed)
        #   refund_amount = 0
        assert _db_credits(fake_db, user_id) == 90

        job = _db_job(fake_db, job_token)
        assert job["status"] == "COMPLETED"
        assert job["actual_usage"] == 10
        assert job["refund_amount"] == 0
        assert job["success_count"] == 10

        # Verify total_credits_used updated
        user_data = fake_db.collection("users")._store[user_id]
        assert user_data["total_credits_used"] == 10

        # No REFUND transaction should exist
        txs = fake_db.collection("transactions")._store
        refund_txs = [t for t in txs.values() if t.get("type") == "REFUND"]
        assert len(refund_txs) == 0, "Commit flow should have no refund transactions"

        # ── INVARIANT ──
        actual_consumed = INITIAL_BALANCE - _db_credits(fake_db, user_id)
        assert actual_consumed == 10

    def test_commit_with_rate3_istock(self, client, fake_db, seed_app_settings):
        """
        Default iStock rate=3. Reserve 10 files × 3 = 30.
        All succeed → balance = 100 - 30 = 70 permanently.
        """
        INITIAL = 100
        user_id = "user-commit-rate3"
        headers = _seed_user(fake_db, user_id, INITIAL)

        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        assert r.status_code == 200
        assert r.json()["reserved_credits"] == 30
        assert _db_credits(fake_db, user_id) == 70

        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": r.json()["job_token"],
            "success": 10, "failed": 0,
            "photos": 10, "videos": 0,
        })
        assert f.status_code == 200
        assert f.json()["refunded"] == 0
        assert f.json()["balance"] == 70
        assert _db_credits(fake_db, user_id) == 70


# ═══════════════════════════════════════════════════════════
# Test Case 3: Partial Success — Commit + Refund
#
#   Setup:  100 credits, reserve 10 files × rate 1 = 10 locked
#   Result: 7 success (commit 7), 3 failed (refund 3)
#   Final:  Balance = 100 - 7 = 93
# ═══════════════════════════════════════════════════════════

class TestPartialSuccessCommitAndRefund:

    def test_partial_success_partial_refund(self, client, fake_db, seed_app_settings):
        """7 succeed, 3 fail → commit 7, refund 3."""
        INITIAL = 100
        user_id = "user-partial"
        headers = _seed_user(fake_db, user_id, INITIAL)

        seed_app_settings["credit_rates"]["istock_photo"] = 1
        seed_app_settings["credit_rates"]["istock_video"] = 1

        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        assert r.status_code == 200
        job_token = r.json()["job_token"]
        assert r.json()["reserved_credits"] == 10
        assert _db_credits(fake_db, user_id) == 90

        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 7, "failed": 3,
            "photos": 10, "videos": 0,
        })
        assert f.status_code == 200
        assert f.json()["refunded"] == 3
        assert f.json()["balance"] == 93

        # DB verification
        assert _db_credits(fake_db, user_id) == 93
        job = _db_job(fake_db, job_token)
        assert job["actual_usage"] == 7
        assert job["refund_amount"] == 3

        # INVARIANT: initial == final + consumed
        consumed = INITIAL - _db_credits(fake_db, user_id)
        assert consumed == 7


# ═══════════════════════════════════════════════════════════
# Test Case 4: Insufficient Credits — Reserve Rejected
#
#   User has 5 credits but wants to reserve 10 files × rate 3 = 30.
#   Reserve should be rejected with 402 and balance unchanged.
# ═══════════════════════════════════════════════════════════

class TestInsufficientCreditsReserve:

    def test_reserve_rejected_balance_unchanged(self, client, fake_db, seed_app_settings):
        """Cannot reserve more than available → 402, balance untouched."""
        INITIAL = 5
        user_id = "user-broke"
        headers = _seed_user(fake_db, user_id, INITIAL)

        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",  # 10 × 3 = 30 > 5
        })
        assert r.status_code == 402
        assert "insufficient" in r.json()["detail"].lower()

        # Balance must be completely unchanged
        assert _db_credits(fake_db, user_id) == INITIAL, \
            "Rejected reserve must not deduct any credits"


# ═══════════════════════════════════════════════════════════
# Test Case 5: Double Finalize — Idempotency Guard
#
#   Calling finalize twice on the same job_token must NOT
#   double-refund or double-commit credits.
# ═══════════════════════════════════════════════════════════

class TestDoubleFinalizeIdempotency:

    def test_double_finalize_safe(self, client, fake_db, seed_app_settings):
        """Second finalize returns same result, no extra credits."""
        INITIAL = 100
        user_id = "user-double"
        headers = _seed_user(fake_db, user_id, INITIAL)

        seed_app_settings["credit_rates"]["istock_photo"] = 1
        seed_app_settings["credit_rates"]["istock_video"] = 1

        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = r.json()["job_token"]

        # First finalize: 5 success, 5 failed → refund 5
        f1 = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 5, "failed": 5,
            "photos": 10, "videos": 0,
        })
        assert f1.status_code == 200
        assert f1.json()["refunded"] == 5
        balance_after_first = f1.json()["balance"]
        assert balance_after_first == 95

        # Second finalize (duplicate/retry) — same token, different numbers
        f2 = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 10, "failed": 0,  # attacker tries to claim all success
            "photos": 10, "videos": 0,
        })
        assert f2.status_code == 200
        # Must return the SAME refund as first call (idempotent)
        assert f2.json()["refunded"] == 5
        assert f2.json()["balance"] == balance_after_first

        # DB: no extra credits created
        assert _db_credits(fake_db, user_id) == balance_after_first


# ═══════════════════════════════════════════════════════════
# Test Case 6: Sequential Reserve-Refund-Reserve-Commit
#
#   Full lifecycle across two jobs to verify balance tracking:
#   Job 1: reserve → all fail → refund (balance restored)
#   Job 2: reserve → all succeed → commit (balance reduced)
# ═══════════════════════════════════════════════════════════

class TestSequentialReserveRefundCommit:

    def test_sequential_jobs_balance_correct(self, client, fake_db, seed_app_settings):
        INITIAL = 100
        user_id = "user-sequential"
        headers = _seed_user(fake_db, user_id, INITIAL)

        seed_app_settings["credit_rates"]["istock_photo"] = 1
        seed_app_settings["credit_rates"]["istock_video"] = 1

        # ── Job 1: Reserve 10, all FAIL → full refund ──
        r1 = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        assert _db_credits(fake_db, user_id) == 90
        f1 = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": r1.json()["job_token"],
            "success": 0, "failed": 10,
            "photos": 10, "videos": 0,
        })
        assert f1.json()["refunded"] == 10
        assert _db_credits(fake_db, user_id) == 100  # fully restored

        # ── Job 2: Reserve 10, all SUCCESS → commit ──
        r2 = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        assert _db_credits(fake_db, user_id) == 90
        f2 = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": r2.json()["job_token"],
            "success": 10, "failed": 0,
            "photos": 10, "videos": 0,
        })
        assert f2.json()["refunded"] == 0
        assert _db_credits(fake_db, user_id) == 90  # permanently consumed

        # ── INVARIANT: only job 2's credits were consumed ──
        total_consumed = INITIAL - _db_credits(fake_db, user_id)
        assert total_consumed == 10


# ═══════════════════════════════════════════════════════════
# Test Case 7: Anti-Cheat — Overclaim Rejected
#
#   Client claims more successes than files reserved.
#   Server must reject with 400 and not modify balance.
# ═══════════════════════════════════════════════════════════

class TestAntiCheatOverclaim:

    def test_overclaim_rejected_balance_safe(self, client, fake_db, seed_app_settings):
        INITIAL = 100
        user_id = "user-cheat"
        headers = _seed_user(fake_db, user_id, INITIAL)

        seed_app_settings["credit_rates"]["istock_photo"] = 1
        seed_app_settings["credit_rates"]["istock_video"] = 1

        r = client.post(f"{PREFIX}/reserve", headers=headers, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = r.json()["job_token"]
        assert _db_credits(fake_db, user_id) == 90

        # Overclaim: 15 success for 10-file job
        f = client.post(f"{PREFIX}/finalize", headers=headers, json={
            "job_token": job_token,
            "success": 15, "failed": 0,
            "photos": 10, "videos": 0,
        })
        assert f.status_code == 400
        assert "exceeds" in f.json()["detail"].lower()

        # Balance unchanged (no commit, no refund)
        assert _db_credits(fake_db, user_id) == 90

        # Job still in RESERVED state (not finalized)
        job = _db_job(fake_db, job_token)
        assert job["status"] == "RESERVED"
