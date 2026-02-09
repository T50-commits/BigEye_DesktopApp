"""
Integration tests for /api/v1/credit/* endpoints
via TestClient with fully mocked Firestore.

Covers:
  - GET /credit/balance — happy path, with promos, with custom rates
  - GET /credit/history — happy path, empty history, limit param
  - POST /credit/topup — happy path (auto-approve), amount validation,
    promo code application, slip record creation
"""
import copy
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

PREFIX = "/api/v1/credit"


# ═══════════════════════════════════════
# GET /credit/balance
# ═══════════════════════════════════════

class TestGetBalance:

    def test_balance_happy_path(self, client, auth_header, seed_user, seed_app_settings):
        """Authenticated user gets their credit balance."""
        resp = client.get(f"{PREFIX}/balance", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["credits"] == 500
        assert body["exchange_rate"] == 4
        assert "credit_rates" in body
        assert body["credit_rates"]["istock_photo"] == 3
        assert body["credit_rates"]["adobe_photo"] == 2

    def test_balance_without_app_settings(self, client, auth_header, seed_user):
        """When no app_settings doc exists, fallback to env defaults."""
        resp = client.get(f"{PREFIX}/balance", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["credits"] == 500
        assert body["exchange_rate"] == 4  # settings.EXCHANGE_RATE default
        assert body["credit_rates"]["istock_photo"] == 3

    def test_balance_includes_active_promos(self, client, auth_header, seed_user, fake_db):
        """Active promos visible to client should appear in balance response."""
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-1"] = {
            "name": "Summer Sale",
            "status": "ACTIVE",
            "conditions": {
                "start_date": now - timedelta(days=1),
                "end_date": now + timedelta(days=30),
                "require_code": False,
            },
            "reward": {"type": "BONUS_CREDITS", "bonus_credits": 50},
            "display": {
                "banner_text": "Summer Sale!",
                "banner_color": "#FF0000",
                "show_in_client": True,
                "show_in_topup": True,
            },
        }
        resp = client.get(f"{PREFIX}/balance", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["active_promos"]) >= 1
        assert body["active_promos"][0]["name"] == "Summer Sale"

    def test_balance_excludes_code_only_promos(self, client, auth_header, seed_user, fake_db):
        """Promos with require_code=True should NOT appear in public balance."""
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-secret"] = {
            "name": "Secret Code",
            "status": "ACTIVE",
            "conditions": {
                "start_date": now - timedelta(days=1),
                "require_code": True,
            },
            "reward": {"type": "BONUS_CREDITS", "bonus_credits": 100},
            "display": {"show_in_client": True, "show_in_topup": True,
                        "banner_text": "Secret", "banner_color": "#000"},
            "code": "SECRET50",
        }
        resp = client.get(f"{PREFIX}/balance", headers=auth_header)
        body = resp.json()
        promo_names = [p["name"] for p in body["active_promos"]]
        assert "Secret Code" not in promo_names

    def test_balance_no_auth_403(self, client, fake_db):
        resp = client.get(f"{PREFIX}/balance")
        assert resp.status_code == 403

    def test_balance_zero_credits(self, client, fake_db):
        """User with 0 credits should still get 200."""
        from app.security import create_jwt_token
        fake_db.collection("users")._store["zero-user"] = {
            "email": "zero@test.com",
            "credits": 0,
            "status": "active",
        }
        token = create_jwt_token("zero-user", "zero@test.com")
        resp = client.get(f"{PREFIX}/balance", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        assert resp.json()["credits"] == 0


# ═══════════════════════════════════════
# GET /credit/history
# ═══════════════════════════════════════

class TestGetHistory:

    def test_history_empty(self, client, auth_header, seed_user):
        """User with no transactions → empty list."""
        resp = client.get(f"{PREFIX}/history", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert body["transactions"] == []
        assert body["balance"] == 500

    def test_history_with_transactions(self, client, auth_header, seed_user, fake_db):
        user_id, _, _ = seed_user
        now = datetime.now(timezone.utc)
        fake_db.collection("transactions")._store["tx-1"] = {
            "user_id": user_id,
            "type": "TOPUP",
            "amount": 400,
            "description": "Top-up 100 THB",
            "created_at": now - timedelta(hours=2),
        }
        fake_db.collection("transactions")._store["tx-2"] = {
            "user_id": user_id,
            "type": "RESERVE",
            "amount": -30,
            "description": "Reserve 10 files (iStock)",
            "created_at": now - timedelta(hours=1),
        }
        resp = client.get(f"{PREFIX}/history", headers=auth_header)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["transactions"]) == 2
        # Should be sorted descending by date (most recent first)
        assert body["transactions"][0]["type"] == "RESERVE"

    def test_history_limit_param(self, client, auth_header, seed_user, fake_db):
        user_id, _, _ = seed_user
        now = datetime.now(timezone.utc)
        for i in range(10):
            fake_db.collection("transactions")._store[f"tx-{i}"] = {
                "user_id": user_id,
                "type": "TOPUP",
                "amount": 100,
                "description": f"Tx {i}",
                "created_at": now - timedelta(hours=i),
            }
        resp = client.get(f"{PREFIX}/history?limit=3", headers=auth_header)
        assert resp.status_code == 200
        assert len(resp.json()["transactions"]) == 3

    def test_history_does_not_leak_other_users(self, client, auth_header, seed_user, fake_db):
        """Should only return transactions for the authenticated user."""
        fake_db.collection("transactions")._store["tx-other"] = {
            "user_id": "other-user-999",
            "type": "TOPUP",
            "amount": 9999,
            "description": "Other user topup",
            "created_at": datetime.now(timezone.utc),
        }
        resp = client.get(f"{PREFIX}/history", headers=auth_header)
        assert resp.status_code == 200
        assert len(resp.json()["transactions"]) == 0


# ═══════════════════════════════════════
# POST /credit/topup
# ═══════════════════════════════════════

class TestTopUp:

    def test_topup_happy_path(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Top-up 100 THB → 400 base credits (rate=4), balance increases."""
        user_id, _, _ = seed_user
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_image_data",
            "amount": 100,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "verified"
        assert body["base_credits"] == 400  # 100 * 4
        assert body["total_credits"] >= 400
        assert body["new_balance"] == 500 + body["total_credits"]

    def test_topup_creates_slip_record(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 200,
        })
        slips = fake_db.collection("slips")._store
        assert len(slips) >= 1
        slip = list(slips.values())[0]
        assert slip["status"] == "VERIFIED"
        assert slip["amount_detected"] == 200

    def test_topup_creates_transaction(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        user_id, _, _ = seed_user
        client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 100,
        })
        txs = fake_db.collection("transactions")._store
        topup_txs = [t for t in txs.values() if t.get("type") == "TOPUP"]
        assert len(topup_txs) >= 1
        assert topup_txs[0]["user_id"] == user_id
        assert topup_txs[0]["amount"] == 400  # 100 * 4

    def test_topup_creates_audit_log(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 100,
        })
        logs = fake_db.collection("audit_logs")._store
        topup_logs = [l for l in logs.values() if l.get("event_type") == "TOPUP_SUCCESS"]
        assert len(topup_logs) >= 1

    def test_topup_amount_zero_422(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 0,
        })
        assert resp.status_code == 422

    def test_topup_amount_negative_422(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": -100,
        })
        assert resp.status_code == 422

    def test_topup_missing_slip_422(self, client, auth_header, seed_user):
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "amount": 100,
        })
        assert resp.status_code == 422

    def test_topup_no_auth_403(self, client, fake_db):
        resp = client.post(f"{PREFIX}/topup", json={
            "slip": "base64_slip_data",
            "amount": 100,
        })
        assert resp.status_code == 403

    def test_topup_with_promo_code(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Top-up with a valid promo code should apply bonus."""
        user_id, _, _ = seed_user
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-code-1"] = {
            "name": "CODE50",
            "code": "SAVE50",
            "type": "FLAT_BONUS",
            "status": "ACTIVE",
            "priority": 10,
            "conditions": {
                "start_date": now - timedelta(days=1),
                "require_code": True,
            },
            "reward": {"type": "BONUS_CREDITS", "bonus_credits": 50},
            "display": {"show_in_client": False, "show_in_topup": True,
                        "banner_text": "", "banner_color": "#000"},
            "stats": {"total_redemptions": 0, "total_bonus_credits": 0,
                      "total_baht_collected": 0, "unique_users": 0},
        }
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 100,
            "promo_code": "SAVE50",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["bonus_credits"] == 50
        assert body["total_credits"] == 450  # 400 base + 50 bonus
        assert body["promo_applied"] == "CODE50"

    def test_topup_with_wrong_promo_code_no_bonus(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Wrong promo code → no bonus applied, but topup still succeeds."""
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-code-2"] = {
            "name": "CODE100",
            "code": "REAL100",
            "type": "FLAT_BONUS",
            "status": "ACTIVE",
            "priority": 10,
            "conditions": {
                "start_date": now - timedelta(days=1),
                "require_code": True,
            },
            "reward": {"type": "BONUS_CREDITS", "bonus_credits": 100},
            "display": {"show_in_client": False, "show_in_topup": True,
                        "banner_text": "", "banner_color": "#000"},
            "stats": {"total_redemptions": 0, "total_bonus_credits": 0,
                      "total_baht_collected": 0, "unique_users": 0},
        }
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 100,
            "promo_code": "WRONG_CODE",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["bonus_credits"] == 0
        assert body["promo_applied"] is None

    def test_topup_auto_promo_no_code_needed(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """Auto-apply promo that doesn't require a code."""
        now = datetime.now(timezone.utc)
        fake_db.collection("promotions")._store["promo-auto"] = {
            "name": "Auto Bonus",
            "code": None,
            "type": "RATE_BOOST",
            "status": "ACTIVE",
            "priority": 5,
            "conditions": {
                "start_date": now - timedelta(days=1),
                "require_code": False,
            },
            "reward": {"type": "PERCENTAGE_BONUS", "bonus_percentage": 25},
            "display": {"show_in_client": True, "show_in_topup": True,
                        "banner_text": "25% Bonus!", "banner_color": "#00FF00"},
            "stats": {"total_redemptions": 0, "total_bonus_credits": 0,
                      "total_baht_collected": 0, "unique_users": 0},
        }
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 100,
        })
        assert resp.status_code == 200
        body = resp.json()
        # base=400, 25% bonus=100
        assert body["base_credits"] == 400
        assert body["bonus_credits"] == 100
        assert body["total_credits"] == 500
        assert body["promo_applied"] == "Auto Bonus"

    def test_topup_updates_user_credits(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        """After topup, user's credits in DB should be incremented."""
        user_id, _, _ = seed_user
        old_credits = fake_db.collection("users")._store[user_id]["credits"]
        resp = client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 100,
        })
        body = resp.json()
        new_credits = fake_db.collection("users")._store[user_id]["credits"]
        assert new_credits == old_credits + body["total_credits"]

    def test_topup_updates_total_topup_baht(self, client, auth_header, seed_user, fake_db, seed_app_settings):
        user_id, _, _ = seed_user
        client.post(f"{PREFIX}/topup", headers=auth_header, json={
            "slip": "base64_slip_data",
            "amount": 250,
        })
        assert fake_db.collection("users")._store[user_id]["total_topup_baht"] == 250
