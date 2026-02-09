"""
Integration tests for /api/v1/system/* endpoints
via TestClient with fully mocked Firestore.

Covers:
  - GET /system/health
  - POST /system/check-update (version comparison, maintenance mode, force update)
  - POST /system/cleanup-expired-jobs (auto-refund)
  - POST /system/expire-promotions
  - Prompt management (verified via /job/reserve config delivery)
"""
import pytest
from datetime import datetime, timezone, timedelta

PREFIX = "/api/v1/system"


# ═══════════════════════════════════════
# GET /system/health
# ═══════════════════════════════════════

class TestHealth:

    def test_health_returns_ok(self, client, fake_db):
        resp = client.get(f"{PREFIX}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "2.0.0"
        assert body["environment"] == "development"

    def test_health_no_auth_required(self, client, fake_db):
        """Health endpoint should be public."""
        resp = client.get(f"{PREFIX}/health")
        assert resp.status_code == 200


# ═══════════════════════════════════════
# POST /system/check-update
# ═══════════════════════════════════════

class TestCheckUpdate:

    def test_no_config_returns_defaults(self, client, fake_db):
        """When no app_settings doc exists → all defaults (no update)."""
        resp = client.post(f"{PREFIX}/check-update", json={"version": "2.0.0"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["update_available"] is False
        assert body["force"] is False
        assert body["maintenance"] is False

    def test_update_available(self, client, fake_db, seed_app_settings):
        """Client on 2.0.0, latest is 2.1.0 → update_available=True."""
        resp = client.post(f"{PREFIX}/check-update", json={"version": "2.0.0"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["update_available"] is True
        assert body["version"] == "2.1.0"
        assert body["download_url"] == "https://example.com/download"
        assert body["notes"] == "Bug fixes and improvements"

    def test_no_update_when_current(self, client, fake_db, seed_app_settings):
        """Client already on latest → update_available=False."""
        resp = client.post(f"{PREFIX}/check-update", json={"version": "2.1.0"})
        assert resp.status_code == 200
        assert resp.json()["update_available"] is False

    def test_force_update_below_threshold(self, client, fake_db, seed_app_settings):
        """Client on 1.0.0, force_update_below=1.5.0 → force=True."""
        resp = client.post(f"{PREFIX}/check-update", json={"version": "1.0.0"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["update_available"] is True
        assert body["force"] is True

    def test_force_update_above_threshold(self, client, fake_db, seed_app_settings):
        """Client on 1.9.0 (above force_update_below=1.5.0) → force=False."""
        resp = client.post(f"{PREFIX}/check-update", json={"version": "1.9.0"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["update_available"] is True
        assert body["force"] is False

    def test_maintenance_mode(self, client, fake_db, seed_app_settings):
        """When maintenance_mode=True → maintenance=True, skip version check."""
        fake_db.collection("system_config")._store["app_settings"]["maintenance_mode"] = True
        fake_db.collection("system_config")._store["app_settings"]["maintenance_message"] = "Down for update"
        resp = client.post(f"{PREFIX}/check-update", json={"version": "2.0.0"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["maintenance"] is True
        assert body["maintenance_message"] == "Down for update"
        # When in maintenance, update_available should be default (False)
        assert body["update_available"] is False


# ═══════════════════════════════════════
# POST /system/cleanup-expired-jobs
# ═══════════════════════════════════════

class TestCleanupExpiredJobs:

    def test_cleanup_no_expired_jobs(self, client, fake_db):
        resp = client.post(f"{PREFIX}/cleanup-expired-jobs")
        assert resp.status_code == 200
        assert resp.json()["cleaned"] == 0

    def test_cleanup_refunds_expired_job(self, client, fake_db):
        """Expired RESERVED job → auto-refund credits to user."""
        user_id = "user-expired"
        fake_db.collection("users")._store[user_id] = {
            "email": "expired@test.com",
            "credits": 100,
            "status": "active",
        }
        now = datetime.now(timezone.utc)
        fake_db.collection("jobs")._store["job-expired"] = {
            "job_token": "expired-token-123",
            "user_id": user_id,
            "status": "RESERVED",
            "reserved_credits": 30,
            "expires_at": now - timedelta(hours=1),  # already expired
        }
        resp = client.post(f"{PREFIX}/cleanup-expired-jobs")
        assert resp.status_code == 200
        assert resp.json()["cleaned"] == 1

        # User should have credits refunded
        user = fake_db.collection("users")._store[user_id]
        assert user["credits"] == 130  # 100 + 30

        # Job should be marked EXPIRED
        job = fake_db.collection("jobs")._store["job-expired"]
        assert job["status"] == "EXPIRED"

        # Refund transaction should exist
        txs = fake_db.collection("transactions")._store
        refund_txs = [t for t in txs.values() if t.get("type") == "REFUND"]
        assert len(refund_txs) == 1
        assert refund_txs[0]["amount"] == 30

    def test_cleanup_ignores_non_expired(self, client, fake_db):
        """RESERVED job that hasn't expired yet → not cleaned."""
        now = datetime.now(timezone.utc)
        fake_db.collection("jobs")._store["job-active"] = {
            "job_token": "active-token",
            "user_id": "user-1",
            "status": "RESERVED",
            "reserved_credits": 30,
            "expires_at": now + timedelta(hours=1),  # still valid
        }
        resp = client.post(f"{PREFIX}/cleanup-expired-jobs")
        assert resp.json()["cleaned"] == 0

    def test_cleanup_ignores_completed_jobs(self, client, fake_db):
        """COMPLETED jobs should not be cleaned up."""
        now = datetime.now(timezone.utc)
        fake_db.collection("jobs")._store["job-done"] = {
            "job_token": "done-token",
            "user_id": "user-1",
            "status": "COMPLETED",
            "reserved_credits": 30,
            "expires_at": now - timedelta(hours=1),
        }
        resp = client.post(f"{PREFIX}/cleanup-expired-jobs")
        assert resp.json()["cleaned"] == 0

    def test_cleanup_multiple_expired(self, client, fake_db):
        """Multiple expired jobs → all cleaned."""
        now = datetime.now(timezone.utc)
        for i in range(3):
            uid = f"user-{i}"
            fake_db.collection("users")._store[uid] = {
                "email": f"u{i}@test.com", "credits": 50, "status": "active",
            }
            fake_db.collection("jobs")._store[f"job-{i}"] = {
                "job_token": f"token-{i}",
                "user_id": uid,
                "status": "RESERVED",
                "reserved_credits": 15,
                "expires_at": now - timedelta(hours=1),
            }
        resp = client.post(f"{PREFIX}/cleanup-expired-jobs")
        assert resp.json()["cleaned"] == 3


# ═══════════════════════════════════════
# POST /system/expire-promotions
# ═══════════════════════════════════════

class TestExpirePromotions:

    def test_expire_past_end_date(self, client, fake_db):
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-old"] = {
            "name": "Old Promo",
            "status": "ACTIVE",
            "conditions": {
                "start_date": now - timedelta(days=30),
                "end_date": now - timedelta(days=1),
            },
        }
        resp = client.post(f"{PREFIX}/expire-promotions")
        assert resp.status_code == 200
        assert resp.json()["expired"] == 1
        assert fake_db.collection("promotions")._store["promo-old"]["status"] == "EXPIRED"

    def test_no_expire_future_end_date(self, client, fake_db):
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-future"] = {
            "name": "Future Promo",
            "status": "ACTIVE",
            "conditions": {
                "start_date": now - timedelta(days=1),
                "end_date": now + timedelta(days=30),
            },
        }
        resp = client.post(f"{PREFIX}/expire-promotions")
        assert resp.json()["expired"] == 0
        assert fake_db.collection("promotions")._store["promo-future"]["status"] == "ACTIVE"

    def test_no_expire_without_end_date(self, client, fake_db):
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-forever"] = {
            "name": "Forever Promo",
            "status": "ACTIVE",
            "conditions": {
                "start_date": now - timedelta(days=1),
            },
        }
        resp = client.post(f"{PREFIX}/expire-promotions")
        assert resp.json()["expired"] == 0


# ═══════════════════════════════════════
# Prompt Management (via /job/reserve)
# ═══════════════════════════════════════

class TestPromptManagement:
    """
    Prompt management is tested through /job/reserve which reads prompts
    from system_config/app_settings and delivers them encrypted.
    """

    def test_prompt_delivered_encrypted(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Reserve should deliver an AES-encrypted prompt in 'config' field."""
        from app.security import decrypt_aes
        resp = client.post("/api/v1/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        assert resp.status_code == 200
        config = resp.json()["config"]
        assert config  # non-empty
        # Should be valid hex (AES output)
        int(config, 16)
        # Should decrypt to the iStock prompt
        decrypted = decrypt_aes(config)
        assert decrypted == "You are a stock photo metadata expert for iStock..."

    def test_prompt_changes_by_mode(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Different modes should deliver different prompts."""
        from app.security import decrypt_aes

        r1 = client.post("/api/v1/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        r2 = client.post("/api/v1/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "Adobe & Shutterstock",
        })
        p1 = decrypt_aes(r1.json()["config"])
        p2 = decrypt_aes(r2.json()["config"])
        assert p1 != p2
        assert "iStock" in p1
        assert "hybrid" in p2

    def test_blacklist_delivered(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        resp = client.post("/api/v1/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        assert resp.json()["blacklist"] == ["nike", "coca cola", "disney"]

    def test_no_app_settings_empty_config(self, client, auth_header, seed_user, fake_db):
        """When no app_settings → config is empty, blacklist is empty."""
        resp = client.post("/api/v1/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        assert resp.status_code == 200
        assert resp.json()["config"] == ""
        assert resp.json()["blacklist"] == []
        assert resp.json()["dictionary"] == ""
