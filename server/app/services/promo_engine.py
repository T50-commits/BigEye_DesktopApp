"""
BigEye Pro — Promotion Engine
Core logic for finding applicable promotions and calculating bonuses.
"""
import logging
from datetime import datetime, timezone

from google.cloud import firestore

from app.database import get_db
from app.config import settings

logger = logging.getLogger("bigeye-api")


def _promotions_ref():
    return get_db().collection("promotions")


def _promo_redemptions_ref():
    return get_db().collection("promo_redemptions")


def get_exchange_rate() -> int:
    """Get current exchange rate (THB → credits) from Firestore, fallback to env."""
    try:
        doc = get_db().collection("system_config").document("app_settings").get()
        if doc.exists:
            rate = doc.to_dict().get("exchange_rate")
            if rate and isinstance(rate, (int, float)):
                return int(rate)
    except Exception:
        pass
    return settings.EXCHANGE_RATE


def count_user_redemptions(user_id: str, promo_id: str) -> int:
    """Count how many times a user has redeemed a specific promo."""
    docs = list(
        _promo_redemptions_ref()
        .where("user_id", "==", user_id)
        .where("promo_id", "==", promo_id)
        .stream()
    )
    return len(docs)


def is_new_user(user: dict) -> bool:
    """Check if user is considered 'new' (registered within last 7 days)."""
    created = user.get("created_at")
    if not created:
        return False
    if hasattr(created, "timestamp"):
        created_ts = created.timestamp()
    else:
        created_ts = created.replace(tzinfo=timezone.utc).timestamp()
    now_ts = datetime.now(timezone.utc).timestamp()
    return (now_ts - created_ts) < 7 * 24 * 3600  # 7 days


def has_previous_topup(user_id: str) -> bool:
    """Check if user has any previous top-up transactions."""
    from app.database import transactions_ref
    docs = list(
        transactions_ref()
        .where("user_id", "==", user_id)
        .where("type", "==", "TOPUP")
        .limit(1)
        .stream()
    )
    return len(docs) > 0


def calculate_bonus(promo: dict, topup_baht: float) -> int:
    """Calculate bonus credits for a given promo and top-up amount."""
    reward = promo.get("reward", {})
    base_rate = get_exchange_rate()
    base_credits = int(topup_baht * base_rate)
    reward_type = reward.get("type", "")

    if reward_type == "BONUS_CREDITS":
        return reward.get("bonus_credits", 0) or 0

    elif reward_type == "RATE_OVERRIDE":
        override_rate = reward.get("override_rate", base_rate)
        new_credits = int(topup_baht * override_rate)
        return new_credits - base_credits

    elif reward_type == "PERCENTAGE_BONUS":
        pct = reward.get("bonus_percentage", 0) or 0
        return int(base_credits * pct / 100)

    elif reward_type == "TIERED_BONUS":
        tiers = reward.get("tiers", []) or []
        # Sort tiers by min_baht descending to find the best matching tier
        sorted_tiers = sorted(tiers, key=lambda t: t.get("min_baht", 0), reverse=True)
        for tier in sorted_tiers:
            min_b = tier.get("min_baht", 0)
            max_b = tier.get("max_baht")
            if topup_baht >= min_b:
                if max_b is None or topup_baht <= max_b:
                    return tier.get("credits", 0) - base_credits
        return 0

    return 0


def find_applicable_promos(
    user_id: str,
    topup_baht: float,
    user: dict,
    promo_code: str | None = None,
) -> list[dict]:
    """
    Find all promotions that apply to this top-up.
    Returns list sorted by priority (highest first).
    Only the BEST single promo should be applied (no stacking).
    """
    now = datetime.now(timezone.utc)

    # Query active promos
    promos = list(
        _promotions_ref()
        .where("status", "==", "ACTIVE")
        .stream()
    )

    applicable = []

    for doc in promos:
        p = doc.to_dict()
        cond = p.get("conditions", {})

        # Check start_date
        start_date = cond.get("start_date")
        if start_date:
            if hasattr(start_date, "timestamp"):
                if now.timestamp() < start_date.timestamp():
                    continue
            elif now < start_date.replace(tzinfo=timezone.utc):
                continue

        # Check end_date
        end_date = cond.get("end_date")
        if end_date:
            if hasattr(end_date, "timestamp"):
                if now.timestamp() > end_date.timestamp():
                    continue
            elif now > end_date.replace(tzinfo=timezone.utc):
                continue

        # Check promo code requirement
        if cond.get("require_code") and p.get("code") != promo_code:
            continue

        # Check min/max top-up amount
        min_topup = cond.get("min_topup_baht")
        if min_topup and topup_baht < min_topup:
            continue
        max_topup = cond.get("max_topup_baht")
        if max_topup and topup_baht > max_topup:
            continue

        # Check max total redemptions
        max_redemptions = cond.get("max_redemptions")
        if max_redemptions:
            stats = p.get("stats", {})
            if stats.get("total_redemptions", 0) >= max_redemptions:
                continue

        # Check max per user
        max_per_user = cond.get("max_per_user")
        if max_per_user:
            user_count = count_user_redemptions(user_id, doc.id)
            if user_count >= max_per_user:
                continue

        # Check user eligibility
        if cond.get("new_users_only") and not is_new_user(user):
            continue
        if cond.get("first_topup_only") and has_previous_topup(user_id):
            continue
        eligible_tiers = cond.get("eligible_tiers")
        if eligible_tiers and user.get("tier") not in eligible_tiers:
            continue

        # Calculate bonus
        bonus = calculate_bonus(p, topup_baht)

        applicable.append({
            "promo_id": doc.id,
            "name": p.get("name", ""),
            "bonus_credits": bonus,
            "display": p.get("display", {}),
            "priority": p.get("priority", 0),
            "type": p.get("type", ""),
            "reward": p.get("reward", {}),
            "conditions": cond,
        })

    # Sort by priority (DESC), then by bonus (DESC)
    applicable.sort(key=lambda x: (-x["priority"], -x["bonus_credits"]))
    return applicable


def get_active_promos_for_client() -> list[dict]:
    """
    Get active promotions to display in client (balance response).
    Returns simplified promo info for the client UI.
    """
    now = datetime.now(timezone.utc)

    promos = list(
        _promotions_ref()
        .where("status", "==", "ACTIVE")
        .stream()
    )

    result = []
    for doc in promos:
        p = doc.to_dict()
        display = p.get("display", {})
        cond = p.get("conditions", {})
        reward = p.get("reward", {})

        # Check date range
        start_date = cond.get("start_date")
        if start_date:
            if hasattr(start_date, "timestamp"):
                if now.timestamp() < start_date.timestamp():
                    continue
            elif now < start_date.replace(tzinfo=timezone.utc):
                continue

        end_date = cond.get("end_date")
        if end_date:
            if hasattr(end_date, "timestamp"):
                if now.timestamp() > end_date.timestamp():
                    continue
            elif now > end_date.replace(tzinfo=timezone.utc):
                continue

        # Only include promos visible to client
        if not display.get("show_in_client", True):
            continue

        # Don't include code-only promos in public list
        if cond.get("require_code"):
            continue

        ends_at = None
        if end_date:
            if hasattr(end_date, "isoformat"):
                ends_at = end_date.isoformat()
            else:
                ends_at = str(end_date)

        info = {
            "promo_id": doc.id,
            "name": p.get("name", ""),
            "banner_text": display.get("banner_text", ""),
            "banner_color": display.get("banner_color", "#FF4560"),
            "type": p.get("type", ""),
            "ends_at": ends_at,
        }

        # Add reward details based on type
        tiers = reward.get("tiers")
        if tiers:
            info["tiers"] = [
                {"min_baht": t.get("min_baht", 0), "credits": t.get("credits", 0)}
                for t in tiers
            ]
        if reward.get("override_rate"):
            info["override_rate"] = reward["override_rate"]
        if reward.get("bonus_credits"):
            info["bonus_credits"] = reward["bonus_credits"]
        if reward.get("bonus_percentage"):
            info["bonus_percentage"] = reward["bonus_percentage"]

        result.append(info)

    return result


def process_topup_with_promo(
    user_id: str,
    user: dict,
    topup_baht: float,
    slip_id: str,
    promo_code: str | None = None,
) -> dict:
    """
    Process top-up with automatic or code-based promotion.
    Returns dict with base_credits, bonus_credits, total_credits, promo_applied.
    """
    from app.database import users_ref, transactions_ref

    base_rate = get_exchange_rate()
    base_credits = int(topup_baht * base_rate)
    bonus_credits = 0
    applied_promo = None

    # Find best promo
    promos = find_applicable_promos(user_id, topup_baht, user, promo_code)
    if promos:
        best = promos[0]
        bonus_credits = best["bonus_credits"]
        applied_promo = best

    total_credits = base_credits + bonus_credits
    now = datetime.now(timezone.utc)
    db = get_db()

    # Atomic update: credits + transaction + redemption + promo stats
    user_ref = users_ref().document(user_id)
    new_balance = user.get("credits", 0) + total_credits

    user_ref.update({
        "credits": firestore.Increment(total_credits),
        "total_topup_baht": firestore.Increment(topup_baht),
        "last_active": now,
    })

    # Transaction description
    desc = f"เติมเงิน {int(topup_baht)} บาท → {total_credits} เครดิต"
    if applied_promo:
        desc += f" (รวมโบนัส {bonus_credits} จาก '{applied_promo['name']}')"

    # Create transaction record
    tx_ref = transactions_ref().add({
        "user_id": user_id,
        "type": "TOPUP",
        "amount": total_credits,
        "balance_after": new_balance,
        "reference_id": slip_id,
        "description": desc,
        "created_at": now,
        "metadata": {
            "baht_amount": topup_baht,
            "base_credits": base_credits,
            "bonus_credits": bonus_credits,
            "promo_id": applied_promo["promo_id"] if applied_promo else None,
            "slip_ref": slip_id,
        },
    })

    # Record redemption if promo applied
    if applied_promo:
        _promo_redemptions_ref().add({
            "promo_id": applied_promo["promo_id"],
            "user_id": user_id,
            "topup_baht": topup_baht,
            "base_credits": base_credits,
            "bonus_credits": bonus_credits,
            "total_credits": total_credits,
            "promo_name": applied_promo["name"],
            "slip_id": slip_id,
            "created_at": now,
        })

        # Update promo stats
        promo_ref = _promotions_ref().document(applied_promo["promo_id"])
        promo_ref.update({
            "stats.total_redemptions": firestore.Increment(1),
            "stats.total_bonus_credits": firestore.Increment(bonus_credits),
            "stats.total_baht_collected": firestore.Increment(topup_baht),
        })

        # Update unique_users (check if first time)
        if count_user_redemptions(user_id, applied_promo["promo_id"]) <= 1:
            promo_ref.update({
                "stats.unique_users": firestore.Increment(1),
            })

    logger.info(
        f"Top-up: {user_id} +{total_credits} cr ({topup_baht} THB)"
        + (f" [promo: {applied_promo['name']}]" if applied_promo else "")
    )

    return {
        "base_credits": base_credits,
        "bonus_credits": bonus_credits,
        "total_credits": total_credits,
        "new_balance": new_balance,
        "promo_applied": applied_promo["name"] if applied_promo else None,
    }


def expire_promotions() -> int:
    """Auto-expire promotions past end_date. Returns count of expired."""
    now = datetime.now(timezone.utc)
    expired_count = 0

    promos = list(
        _promotions_ref()
        .where("status", "==", "ACTIVE")
        .stream()
    )

    for doc in promos:
        p = doc.to_dict()
        end_date = p.get("conditions", {}).get("end_date")
        if not end_date:
            continue

        if hasattr(end_date, "timestamp"):
            is_expired = now.timestamp() > end_date.timestamp()
        else:
            is_expired = now > end_date.replace(tzinfo=timezone.utc)

        if is_expired:
            doc.reference.update({
                "status": "EXPIRED",
                "updated_at": now,
            })
            logger.info(f"Promo expired: {p.get('name', doc.id)}")
            expired_count += 1

    return expired_count
