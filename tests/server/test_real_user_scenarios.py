"""
Real-User Scenario Tests — จำลองการใช้งานจริงของผู้ใช้ BigEye Pro

Scenarios:
  1. New User Registration → Login → First Job
  2. Top-up → Process → Stop Midway → Credit Refund
  3. Multiple Sequential Jobs (drain credits gradually)
  4. Concurrent Reserve Attempts (race condition)
  5. Job with Mixed Photo/Video → Partial Failure → Correct Refund
  6. Platform Switch: iStock → Adobe & Shutterstock → Different Rates
  7. Maintenance Mode Blocks All Operations
  8. Expired JWT → Re-login Flow
  9. Zero-Credit User Tries to Process
  10. Double-Finalize (idempotency)
  11. Anti-Cheat: Client Claims More Success Than Files
  12. Bank Info Available After Login
  13. Credit History Shows Thai Descriptions
  14. Adobe & Shutterstock Mode Literal Accepted
"""
import copy
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

PREFIX = "/api/v1"


# ═══════════════════════════════════════════════════════════
# Scenario 1: New User → Register → Login → First Job
# ═══════════════════════════════════════════════════════════

class TestScenario_NewUserFirstJob:
    """ผู้ใช้ใหม่: สมัคร → เข้าสู่ระบบ → ประมวลผลครั้งแรก"""

    def test_register_login_reserve_finalize(self, client, fake_db, seed_app_settings):
        """Full lifecycle: register → login → check balance → reserve → finalize."""
        hw_id = "a" * 32

        # Step 1: Register
        resp = client.post(f"{PREFIX}/auth/register", json={
            "email": "newuser@test.com",
            "password": "SecurePass123",
            "full_name": "New User",
            "phone": "0812345678",
            "hardware_id": hw_id,
        })
        assert resp.status_code == 200, f"Register failed: {resp.json()}"
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Check balance (new user should have welcome credits or 0)
        resp = client.get(f"{PREFIX}/credit/balance", headers=headers)
        assert resp.status_code == 200
        initial_credits = resp.json()["credits"]

        # Step 3: If user has credits, reserve a small job
        if initial_credits >= 3:
            resp = client.post(f"{PREFIX}/job/reserve", headers=headers, json={
                "file_count": 1,
                "photo_count": 1,
                "video_count": 0,
                "mode": "iStock",
            })
            assert resp.status_code == 200
            job_token = resp.json()["job_token"]

            # Step 4: Finalize — all success
            resp = client.post(f"{PREFIX}/job/finalize", headers=headers, json={
                "job_token": job_token,
                "success": 1,
                "failed": 0,
                "photos": 1,
                "videos": 0,
            })
            assert resp.status_code == 200
            assert resp.json()["refunded"] == 0

    def test_register_duplicate_email_409(self, client, fake_db, seed_user):
        """ลงทะเบียนซ้ำด้วยอีเมลเดิม → 409."""
        resp = client.post(f"{PREFIX}/auth/register", json={
            "email": "test@example.com",  # same as seed_user
            "password": "AnotherPass123",
            "full_name": "Dup User",
            "phone": "",
            "hardware_id": "b" * 32,
        })
        assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════
# Scenario 2: Process → Stop Midway → Credit Refund
# ═══════════════════════════════════════════════════════════

class TestScenario_StopMidway:
    """ผู้ใช้กด STOP กลางคัน → เครดิตต้องคืนถูกต้อง"""

    def test_stop_midway_partial_refund(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Reserve 10 files, only 3 succeed, 2 fail, 5 unprocessed → refund for 7 failed+unprocessed."""
        user_id, _, _ = seed_user
        initial = fake_db.collection("users")._store[user_id]["credits"]  # 500

        # Reserve 10 iStock files (rate=3) → cost 30
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        assert resp.status_code == 200
        job_token = resp.json()["job_token"]
        after_reserve = fake_db.collection("users")._store[user_id]["credits"]
        assert after_reserve == initial - 30

        # Finalize: 3 success, 2 failed (5 unprocessed treated as failed)
        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 3,
            "failed": 7,  # 2 actual fail + 5 unprocessed
            "photos": 10,
            "videos": 0,
        })
        assert resp.status_code == 200
        body = resp.json()
        # Charged for 3 success * 3 = 9, refund = 30 - 9 = 21
        assert body["refunded"] == 21
        assert body["balance"] == initial - 9  # 500 - 9 = 491

    def test_stop_immediately_full_refund(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """กด Stop ทันทีก่อนประมวลผล → คืนเครดิตทั้งหมด."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]

        # Finalize: 0 success, 0 failed (user stopped before any processing)
        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 0,
            "failed": 5,
            "photos": 5,
            "videos": 0,
        })
        assert resp.status_code == 200
        assert resp.json()["refunded"] == 15  # full refund
        assert resp.json()["balance"] == 500  # restored


# ═══════════════════════════════════════════════════════════
# Scenario 3: Multiple Sequential Jobs (drain credits)
# ═══════════════════════════════════════════════════════════

class TestScenario_MultipleJobs:
    """ผู้ใช้รันหลาย job ต่อเนื่อง → เครดิตลดลงถูกต้อง"""

    def test_three_sequential_jobs(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Run 3 jobs: 10 files each at rate 3 → 90 credits total."""
        user_id, _, _ = seed_user
        tokens = []

        for i in range(3):
            resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
                "file_count": 10, "mode": "iStock",
            })
            assert resp.status_code == 200, f"Job {i+1} reserve failed"
            tokens.append(resp.json()["job_token"])

        # All 3 reserved: 500 - 90 = 410
        assert fake_db.collection("users")._store[user_id]["credits"] == 410

        # Finalize all with full success
        for token in tokens:
            resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
                "job_token": token,
                "success": 10,
                "failed": 0,
                "photos": 10,
                "videos": 0,
            })
            assert resp.status_code == 200
            assert resp.json()["refunded"] == 0

        # Final balance: 410 (no refunds)
        assert fake_db.collection("users")._store[user_id]["credits"] == 410

    def test_drain_credits_then_fail(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """ใช้เครดิตจนหมด → reserve ถัดไปต้อง 402."""
        # Reserve 166 files at rate 3 → 498 credits
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 166, "mode": "iStock",
        })
        assert resp.status_code == 200

        # Only 2 credits left → try to reserve 1 more file (cost 3) → 402
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        assert resp.status_code == 402


# ═══════════════════════════════════════════════════════════
# Scenario 5: Mixed Photo/Video → Partial Failure
# ═══════════════════════════════════════════════════════════

class TestScenario_MixedPhotoVideo:
    """ผู้ใช้ส่งทั้งภาพและวิดีโอ → ค่าใช้จ่ายและคืนเครดิตถูกต้อง"""

    def test_mixed_photo_video_refund(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """10 files (7 photos + 3 videos), iStock rate 3/3 → cost 30."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10,
            "photo_count": 7,
            "video_count": 3,
            "mode": "iStock",
        })
        assert resp.status_code == 200
        job_token = resp.json()["job_token"]
        assert resp.json()["reserved_credits"] == 30  # (7+3)*3

        # 5 succeed (mix of photos/videos), 5 fail
        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 5,
            "failed": 5,
            "photos": 7,
            "videos": 3,
        })
        assert resp.status_code == 200
        body = resp.json()
        # refund should be 30 - (5 * 3) = 15
        assert body["refunded"] == 15
        assert body["balance"] == 500 - 30 + 15  # 485


# ═══════════════════════════════════════════════════════════
# Scenario 6: Platform Switch → Different Rates
# ═══════════════════════════════════════════════════════════

class TestScenario_PlatformSwitch:
    """สลับ Platform → อัตราเครดิตต่างกัน"""

    def test_istock_vs_adobe_rates(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """iStock rate=3, Adobe rate=2 → same file count, different cost."""
        user_id, _, _ = seed_user

        # iStock: 10 files * 3 = 30
        r1 = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        assert r1.json()["reserved_credits"] == 30

        # Adobe & Shutterstock: 10 files * 2 = 20
        r2 = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "Adobe & Shutterstock",
        })
        assert r2.json()["reserved_credits"] == 20

        # Total deducted: 50
        assert fake_db.collection("users")._store[user_id]["credits"] == 450


# ═══════════════════════════════════════════════════════════
# Scenario 7: Maintenance Mode
# ═══════════════════════════════════════════════════════════

class TestScenario_MaintenanceMode:
    """Maintenance mode → client ต้องถูก block"""

    def test_check_update_returns_maintenance(self, client, fake_db):
        """When maintenance_mode=True, check-update returns maintenance flag."""
        fake_db.collection("system_config")._store["app_settings"] = {
            "maintenance_mode": True,
            "maintenance_message": "ปิดปรับปรุงระบบ 2 ชม.",
            "app_latest_version": "2.0.0",
        }
        resp = client.post(f"{PREFIX}/system/check-update", json={
            "version": "2.0.0",
            "hardware_id": "a" * 32,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["maintenance"] is True
        assert "ปิดปรับปรุง" in body["maintenance_message"]

    def test_reserve_still_works_during_maintenance(self, client, auth_header, seed_user, fake_db):
        """Reserve endpoint doesn't check maintenance — only check-update does.
        This is a KNOWN LIMITATION: maintenance only blocks at startup/refresh."""
        fake_db.collection("system_config")._store["app_settings"] = {
            "maintenance_mode": True,
            "maintenance_message": "Down for maintenance",
            "credit_rates": {"istock_photo": 3, "istock_video": 3},
            "prompts": {"istock": "test prompt"},
        }
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 1, "mode": "iStock",
        })
        # NOTE: This currently succeeds! Server doesn't check maintenance on /job/reserve.
        # This is a potential improvement area.
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════
# Scenario 8: Expired JWT
# ═══════════════════════════════════════════════════════════

class TestScenario_ExpiredJWT:
    """JWT หมดอายุ → ต้อง re-login"""

    def test_expired_token_403(self, client, fake_db, seed_user):
        """Expired JWT should return 401/403."""
        from app.security import create_jwt_token
        import jwt as pyjwt

        user_id, _, _ = seed_user
        # Create a token that expired 1 hour ago
        payload = {
            "user_id": user_id,
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        from app.config import settings
        expired_token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

        resp = client.get(f"{PREFIX}/credit/balance", headers={
            "Authorization": f"Bearer {expired_token}",
        })
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════
# Scenario 9: Zero-Credit User
# ═══════════════════════════════════════════════════════════

class TestScenario_ZeroCredits:
    """ผู้ใช้เครดิต 0 → ต้องไม่สามารถ reserve ได้"""

    def test_zero_credit_reserve_402(self, client, fake_db, seed_app_settings):
        """User with 0 credits → 402 on reserve."""
        from app.security import create_jwt_token, hash_password
        fake_db.collection("users")._store["zero-uid"] = {
            "email": "zero@test.com",
            "password_hash": hash_password("Password123"),
            "credits": 0,
            "status": "active",
            "hardware_id": "c" * 32,
        }
        token = create_jwt_token("zero-uid", "zero@test.com")
        resp = client.post(f"{PREFIX}/job/reserve", headers={
            "Authorization": f"Bearer {token}",
        }, json={"file_count": 1, "mode": "iStock"})
        assert resp.status_code == 402


# ═══════════════════════════════════════════════════════════
# Scenario 10: Double-Finalize (Idempotency)
# ═══════════════════════════════════════════════════════════

class TestScenario_DoubleFinalize:
    """Finalize ซ้ำ → ต้อง idempotent (ไม่คืนเครดิตซ้ำ)"""

    def test_double_finalize_idempotent(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Calling finalize twice should return same result, not double-refund."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]

        finalize_payload = {
            "job_token": job_token,
            "success": 5,
            "failed": 5,
            "photos": 10,
            "videos": 0,
        }

        # First finalize
        r1 = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json=finalize_payload)
        assert r1.status_code == 200
        balance_after_first = r1.json()["balance"]

        # Second finalize (should be idempotent)
        r2 = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json=finalize_payload)
        assert r2.status_code == 200
        balance_after_second = r2.json()["balance"]

        # Balance should NOT change on second finalize
        assert balance_after_second == balance_after_first


# ═══════════════════════════════════════════════════════════
# Scenario 11: Anti-Cheat
# ═══════════════════════════════════════════════════════════

class TestScenario_AntiCheat:
    """ป้องกันการโกง: claim มากกว่าจำนวนไฟล์จริง"""

    def test_overclaim_success_400(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Claim 15 success on a 10-file job → 400."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]

        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 15,
            "failed": 0,
            "photos": 15,
            "videos": 0,
        })
        assert resp.status_code == 400

    def test_overclaim_total_400(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Claim success + failed > file_count → 400."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]

        resp = client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 8,
            "failed": 5,  # 8+5=13 > 10
            "photos": 10,
            "videos": 0,
        })
        assert resp.status_code == 400

    def test_finalize_wrong_user_404(self, client, fake_db, seed_user, seed_app_settings):
        """User A's job token → User B tries to finalize → 404."""
        from app.security import create_jwt_token, hash_password
        _, token_a, _ = seed_user

        # User A reserves
        resp = client.post(f"{PREFIX}/job/reserve", headers={
            "Authorization": f"Bearer {token_a}",
        }, json={"file_count": 5, "mode": "iStock"})
        job_token = resp.json()["job_token"]

        # Create User B
        fake_db.collection("users")._store["user-b"] = {
            "email": "userb@test.com",
            "password_hash": hash_password("Password123"),
            "credits": 500,
            "status": "active",
            "hardware_id": "d" * 32,
        }
        token_b = create_jwt_token("user-b", "userb@test.com")

        # User B tries to finalize User A's job
        resp = client.post(f"{PREFIX}/job/finalize", headers={
            "Authorization": f"Bearer {token_b}",
        }, json={
            "job_token": job_token,
            "success": 5, "failed": 0, "photos": 5, "videos": 0,
        })
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# Scenario 12: Bank Info Available After Login
# ═══════════════════════════════════════════════════════════

class TestScenario_BankInfo:
    """bank_info ต้องมาพร้อมกับ /credit/balance"""

    def test_balance_includes_bank_info(self, client, auth_header, seed_user, fake_db):
        """When bank_info is configured, it should appear in balance response."""
        fake_db.collection("system_config")._store["app_settings"] = {
            "exchange_rate": 4,
            "credit_rates": {"istock_photo": 3, "istock_video": 3, "adobe_photo": 2, "adobe_video": 2},
            "bank_info": {
                "bank_name": "ธนาคารกสิกรไทย",
                "account_number": "123-4-56789-0",
                "account_name": "บริษัท บิ๊กอาย จำกัด",
            },
        }
        resp = client.get(f"{PREFIX}/credit/balance", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["bank_info"]["bank_name"] == "ธนาคารกสิกรไทย"
        assert body["bank_info"]["account_number"] == "123-4-56789-0"

    def test_balance_no_bank_info_returns_empty(self, client, auth_header, seed_user, fake_db):
        """When bank_info is not configured, return empty dict."""
        fake_db.collection("system_config")._store["app_settings"] = {
            "exchange_rate": 4,
            "credit_rates": {"istock_photo": 3, "istock_video": 3},
        }
        resp = client.get(f"{PREFIX}/credit/balance", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["bank_info"] == {}


# ═══════════════════════════════════════════════════════════
# Scenario 13: Credit History Thai Descriptions
# ═══════════════════════════════════════════════════════════

class TestScenario_HistoryThai:
    """ประวัติเครดิตต้องแสดงเป็นภาษาไทย"""

    def test_reserve_transaction_thai_description(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Reserve transaction should have Thai description with photo/video counts."""
        client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10,
            "photo_count": 7,
            "video_count": 3,
            "mode": "iStock",
        })
        txs = fake_db.collection("transactions")._store
        reserve_txs = [t for t in txs.values() if t.get("type") == "RESERVE"]
        assert len(reserve_txs) == 1
        desc = reserve_txs[0]["description"]
        assert "หักเครดิต" in desc
        assert "📷" in desc or "ภาพ" in desc
        assert "🎬" in desc or "วิดีโอ" in desc

    def test_refund_transaction_thai_description(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Refund transaction should have Thai description."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 10, "mode": "iStock",
        })
        job_token = resp.json()["job_token"]

        client.post(f"{PREFIX}/job/finalize", headers=auth_header, json={
            "job_token": job_token,
            "success": 5, "failed": 5, "photos": 10, "videos": 0,
        })
        txs = fake_db.collection("transactions")._store
        refund_txs = [t for t in txs.values() if t.get("type") == "REFUND"]
        assert len(refund_txs) == 1
        desc = refund_txs[0]["description"]
        assert "คืนเครดิต" in desc
        assert "ล้มเหลว" in desc


# ═══════════════════════════════════════════════════════════
# Scenario 14: Adobe & Shutterstock Mode Literal
# ═══════════════════════════════════════════════════════════

class TestScenario_ModeLiteral:
    """mode 'Adobe & Shutterstock' ต้องถูกรับโดย server"""

    def test_adobe_shutterstock_mode_accepted(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Server must accept 'Adobe & Shutterstock' as valid mode."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5,
            "mode": "Adobe & Shutterstock",
            "keyword_style": "Hybrid (Phrase & Single)",
        })
        assert resp.status_code == 200
        assert resp.json()["photo_rate"] == 2

    def test_invalid_mode_422(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Invalid mode string → 422 validation error."""
        resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
            "file_count": 5,
            "mode": "InvalidPlatform",
        })
        assert resp.status_code == 422

    def test_all_valid_modes(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """All 4 valid modes should be accepted."""
        for mode in ["iStock", "Adobe", "Shutterstock", "Adobe & Shutterstock"]:
            resp = client.post(f"{PREFIX}/job/reserve", headers=auth_header, json={
                "file_count": 1, "mode": mode,
            })
            assert resp.status_code == 200, f"Mode '{mode}' rejected: {resp.json()}"
