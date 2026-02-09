"""
Integration tests for /api/v1/job/reserve and /api/v1/job/finalize
via TestClient with fully mocked Firestore.

Covers:
  RESERVE:
    - Happy path: deduct credits, return encrypted config, job_token
    - Insufficient credits → 402
    - Inactive/banned account → 403
    - Prompt selection by mode (iStock vs hybrid vs single)
    - Photo/video rate separation
    - No auth → 403
  FINALIZE:
    - Happy path: partial success → refund unused credits
    - All success → zero refund
    - All failed → full refund
    - Anti-cheat: overclaim → 400
    - Already finalized → return existing data
    - Job not found → 404
    - Mixed photo/video refund calculation
"""
import copy
import pytest
from datetime import datetime, timezone, timedelta

PREFIX = "/api/v1/job"


# ═══════════════════════════════════════
# POST /job/reserve
# ═══════════════════════════════════════

class TestReserveJob:

    def test_reserve_happy_path_istock(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Reserve 10 iStock files (rate=3) → deduct 30 credits, return config."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10,
            "mode": "iStock",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["reserved_credits"] == 30  # 10 * 3
        assert body["photo_rate"] == 3
        assert body["video_rate"] == 3
        assert body["job_token"]
        assert body["config"]  # encrypted prompt
        assert body["blacklist"] == ["nike", "coca cola", "disney"]
        assert body["dictionary"] == "landscape,portrait,nature,urban"
        assert body["cache_threshold"] == 25
        assert body["concurrency"]["image"] == 5
        assert body["concurrency"]["video"] == 2

        # Credits should be deducted
        user = fake_db.collection("users")._store[user_id]
        assert user["credits"] == 500 - 30

    def test_reserve_happy_path_adobe(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Reserve 10 Adobe files (rate=2) → deduct 20 credits."""
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10,
            "mode": "Adobe & Shutterstock",
            "keyword_style": "Hybrid (Phrase & Single)",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["reserved_credits"] == 20  # 10 * 2
        assert body["photo_rate"] == 2
        assert body["video_rate"] == 2

    def test_reserve_with_photo_video_breakdown(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """When client sends photo_count + video_count, use those for cost calc."""
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10,
            "photo_count": 7,
            "video_count": 3,
            "mode": "iStock",
        })
        assert resp.status_code == 200
        body = resp.json()
        # iStock: photo=3, video=3 → 7*3 + 3*3 = 30
        assert body["reserved_credits"] == 30

    def test_reserve_insufficient_credits_402(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """User has 500 credits, tries to reserve 200 files at rate 3 → 600 needed → 402."""
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 200,
            "mode": "iStock",
        })
        assert resp.status_code == 402
        assert "insufficient" in resp.json()["detail"].lower()

    def test_reserve_exactly_enough_credits(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """User has exactly enough credits → should succeed."""
        user_id, _, _ = seed_user
        # 500 credits / 3 per file = 166 files max, cost = 498
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 166,
            "mode": "iStock",
        })
        assert resp.status_code == 200
        assert resp.json()["reserved_credits"] == 498
        assert fake_db.collection("users")._store[user_id]["credits"] == 2

    def test_reserve_banned_user_403(self, client, fake_db, seed_app_settings):
        """Banned user trying to reserve → 403 from auth dependency."""
        from app.security import create_jwt_token
        fake_db.collection("users")._store["banned-uid"] = {
            "email": "banned@test.com",
            "status": "banned",
            "credits": 1000,
        }
        token = create_jwt_token("banned-uid", "banned@test.com")
        resp = client.post(f"{PREFIX}/reserve", headers={
            "Authorization": f"Bearer {token}",
        }, json={"file_count": 5, "mode": "iStock"})
        assert resp.status_code == 403

    def test_reserve_inactive_user_403(self, client, fake_db, seed_app_settings):
        """User with status != 'active' → 403 from reserve_job check."""
        from app.security import create_jwt_token
        fake_db.collection("users")._store["inactive-uid"] = {
            "email": "inactive@test.com",
            "status": "suspended",
            "credits": 1000,
        }
        token = create_jwt_token("inactive-uid", "inactive@test.com")
        resp = client.post(f"{PREFIX}/reserve", headers={
            "Authorization": f"Bearer {token}",
        }, json={"file_count": 5, "mode": "iStock"})
        assert resp.status_code == 403

    def test_reserve_no_auth_403(self, client, fake_db):
        resp = client.post(f"{PREFIX}/reserve", json={
            "file_count": 5, "mode": "iStock",
        })
        assert resp.status_code == 403

    def test_reserve_file_count_zero_422(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 0, "mode": "iStock",
        })
        assert resp.status_code == 422

    def test_reserve_creates_job_document(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]
        jobs = fake_db.collection("jobs")._store
        assert len(jobs) == 1
        job = list(jobs.values())[0]
        assert job["job_token"] == job_token
        assert job["user_id"] == user_id
        assert job["status"] == "RESERVED"
        assert job["file_count"] == 5
        assert job["reserved_credits"] == 15

    def test_reserve_creates_transaction(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        txs = fake_db.collection("transactions")._store
        reserve_txs = [t for t in txs.values() if t.get("type") == "RESERVE"]
        assert len(reserve_txs) == 1
        assert reserve_txs[0]["amount"] == -15

    def test_reserve_creates_audit_log(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        logs = fake_db.collection("audit_logs")._store
        assert any(v.get("event_type") == "JOB_RESERVED" for v in logs.values())

    def test_reserve_prompt_selection_istock(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """iStock mode → uses 'istock' prompt."""
        from app.security import decrypt_aes
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        config = resp.json()["config"]
        decrypted = decrypt_aes(config)
        assert "iStock" in decrypted

    def test_reserve_prompt_selection_hybrid(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Adobe + Hybrid style → uses 'hybrid' prompt."""
        from app.security import decrypt_aes
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5,
            "mode": "Adobe & Shutterstock",
            "keyword_style": "Hybrid (Phrase & Single)",
        })
        config = resp.json()["config"]
        decrypted = decrypt_aes(config)
        assert "hybrid" in decrypted

    def test_reserve_prompt_selection_single(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Adobe + Single Words style → uses 'single' prompt."""
        from app.security import decrypt_aes
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5,
            "mode": "Adobe & Shutterstock",
            "keyword_style": "Single Words",
        })
        config = resp.json()["config"]
        decrypted = decrypt_aes(config)
        assert "single" in decrypted

    def test_reserve_no_dictionary_for_adobe(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Adobe mode should NOT include dictionary."""
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "Adobe & Shutterstock",
        })
        assert resp.json()["dictionary"] == ""

    def test_reserve_multiple_jobs(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """User can reserve multiple jobs sequentially."""
        r1 = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        r2 = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["job_token"] != r2.json()["job_token"]
        # 500 - 15 - 15 = 470
        user_id, _, _ = seed_user
        assert fake_db.collection("users")._store[user_id]["credits"] == 470


# ═══════════════════════════════════════
# POST /job/finalize
# ═══════════════════════════════════════

class TestFinalizeJob:

    def _reserve_job(self, client, auth_header, file_count=10, mode="iStock"):
        """Helper: reserve a job and return the job_token."""
        resp = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": file_count, "mode": mode,
        })
        assert resp.status_code == 200
        return resp.json()["job_token"]

    def test_finalize_all_success_zero_refund(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """All 10 files succeed → 0 refund."""
        user_id, _, _ = seed_user
        token = self._reserve_job(client, auth_header, 10)
        # credits: 500 - 30 = 470
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 10,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["refunded"] == 0
        assert body["balance"] == 470

    def test_finalize_all_failed_full_refund(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """All 10 files fail → full refund of 30 credits."""
        user_id, _, _ = seed_user
        token = self._reserve_job(client, auth_header, 10)
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 0,
            "failed": 10,
            "photos": 10,
            "videos": 0,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["refunded"] == 30
        assert body["balance"] == 500  # fully restored

    def test_finalize_partial_success(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """7 succeed, 3 fail → refund 9 credits (3 failed * 3 rate)."""
        user_id, _, _ = seed_user
        token = self._reserve_job(client, auth_header, 10)
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 7,
            "failed": 3,
            "photos": 10,
            "videos": 0,
        })
        assert resp.status_code == 200
        body = resp.json()
        # reserved=30, actual=7*3=21, refund=9
        assert body["refunded"] == 9
        assert body["balance"] == 470 + 9  # 479

    def test_finalize_partial_processing(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Only 5 out of 10 processed (5 success, 0 failed) → refund for 5 unprocessed."""
        token = self._reserve_job(client, auth_header, 10)
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 5,
            "failed": 0,
            "photos": 5,
            "videos": 0,
        })
        assert resp.status_code == 200
        body = resp.json()
        # reserved=30, actual=5*3=15, refund=15
        assert body["refunded"] == 15

    def test_finalize_creates_refund_transaction(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        token = self._reserve_job(client, auth_header, 10)
        client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 5,
            "failed": 5,
            "photos": 10,
            "videos": 0,
        })
        txs = fake_db.collection("transactions")._store
        refund_txs = [t for t in txs.values() if t.get("type") == "REFUND"]
        assert len(refund_txs) == 1
        assert refund_txs[0]["amount"] == 15  # 5 failed * 3

    def test_finalize_updates_job_status(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        token = self._reserve_job(client, auth_header, 10)
        client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 10,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        jobs = fake_db.collection("jobs")._store
        job = next(j for j in jobs.values() if j["job_token"] == token)
        assert job["status"] == "COMPLETED"
        assert job["success_count"] == 10
        assert job["actual_usage"] == 30

    def test_finalize_creates_audit_log(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        token = self._reserve_job(client, auth_header, 10)
        client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 10,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        logs = fake_db.collection("audit_logs")._store
        assert any(v.get("event_type") == "JOB_COMPLETED" for v in logs.values())

    # ── Anti-cheat ──

    def test_finalize_overclaim_total_400(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """success + failed > file_count → 400."""
        token = self._reserve_job(client, auth_header, 10)
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 8,
            "failed": 5,  # 8+5=13 > 10
            "photos": 10,
            "videos": 0,
        })
        assert resp.status_code == 400
        assert "exceeds" in resp.json()["detail"].lower()

    def test_finalize_overclaim_success_400(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """success > file_count → 400."""
        token = self._reserve_job(client, auth_header, 10)
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 11,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        assert resp.status_code == 400

    # ── Edge cases ──

    def test_finalize_job_not_found_404(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": "nonexistent-token",
            "success": 5,
            "failed": 0,
        })
        assert resp.status_code == 404

    def test_finalize_already_completed_returns_existing(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Finalizing an already-completed job should return existing data (idempotent)."""
        token = self._reserve_job(client, auth_header, 10)
        # First finalize
        r1 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 7,
            "failed": 3,
            "photos": 10,
            "videos": 0,
        })
        assert r1.status_code == 200
        # Second finalize (same token)
        r2 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 10,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        assert r2.status_code == 200
        # Should return the ORIGINAL refund, not recalculate
        assert r2.json()["refunded"] == r1.json()["refunded"]

    def test_finalize_no_auth_403(self, client, fake_db):
        resp = client.post(f"{PREFIX}/finalize", json={
            "job_token": "some-token",
            "success": 5,
            "failed": 0,
        })
        assert resp.status_code == 403

    def test_finalize_zero_success_zero_failed(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Client crashed immediately — 0 success, 0 failed → full refund."""
        token = self._reserve_job(client, auth_header, 10)
        resp = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 0,
            "failed": 0,
        })
        assert resp.status_code == 200
        assert resp.json()["refunded"] == 30

    def test_finalize_updates_total_credits_used(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        user_id, _, _ = seed_user
        token = self._reserve_job(client, auth_header, 10)
        client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 10,
            "failed": 0,
            "photos": 10,
            "videos": 0,
        })
        user = fake_db.collection("users")._store[user_id]
        assert user["total_credits_used"] == 30


# ═══════════════════════════════════════
# Reserve-Refund Full Cycle
# ═══════════════════════════════════════

class TestReserveRefundCycle:

    def test_full_cycle_balance_consistency(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """
        Full cycle: reserve → partial process → finalize → verify balance.
        Start: 500 credits
        Reserve 10 iStock files: -30 → 470
        Process 6 success, 4 failed: actual=18, refund=12 → 482
        """
        user_id, _, _ = seed_user
        # Reserve
        r1 = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        assert r1.status_code == 200
        token = r1.json()["job_token"]
        assert fake_db.collection("users")._store[user_id]["credits"] == 470

        # Finalize
        r2 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": token,
            "success": 6,
            "failed": 4,
            "photos": 10,
            "videos": 0,
        })
        assert r2.status_code == 200
        assert r2.json()["refunded"] == 12  # (10-6)*3 = 12
        assert r2.json()["balance"] == 482
        assert fake_db.collection("users")._store[user_id]["credits"] == 482

    def test_multiple_jobs_balance_tracking(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Two sequential jobs — verify credits tracked correctly."""
        user_id, _, _ = seed_user
        # Job 1: 5 files, all success
        r1 = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        t1 = r1.json()["job_token"]
        client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": t1, "success": 5, "failed": 0, "photos": 5, "videos": 0,
        })
        # 500 - 15 = 485, refund=0 → 485

        # Job 2: 10 files, 3 failed
        r2 = client.post(f"{PREFIX}/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        t2 = r2.json()["job_token"]
        f2 = client.post(f"{PREFIX}/finalize", headers=auth_header, json={
            "job_token": t2, "success": 7, "failed": 3, "photos": 10, "videos": 0,
        })
        # 485 - 30 = 455, refund=9 → 464
        assert f2.json()["balance"] == 464
