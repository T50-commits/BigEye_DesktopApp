"""
BigEye Pro — Credit Router
GET /credit/balance, GET /credit/history, POST /credit/topup
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from app.models import (
    BalanceResponse, TopUpRequest, TopUpResponse,
    HistoryResponse, TransactionItem,
)
from app.models.promo import (
    BalanceWithPromosResponse, TopUpWithPromoRequest, TopUpWithPromoResponse,
)
from app.database import users_ref, transactions_ref, slips_ref, audit_logs_ref, system_config_ref
from app.dependencies import get_current_user
from app.config import settings
from app.services.promo_engine import (
    get_active_promos_for_client, process_topup_with_promo,
)

logger = logging.getLogger("bigeye-api")
router = APIRouter(prefix="/credit", tags=["Credit"])


def _load_app_settings() -> dict:
    """Read app_settings from Firestore once per call."""
    try:
        doc = system_config_ref().document("app_settings").get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return {}


@router.get("/balance", response_model=BalanceWithPromosResponse)
async def get_balance(user: dict = Depends(get_current_user)):
    """Get current credit balance with active promotions and credit rates."""
    try:
        active_promos = get_active_promos_for_client()
    except Exception as e:
        logger.warning(f"Failed to fetch active promos: {e}")
        active_promos = []

    cfg = _load_app_settings()
    rates = cfg.get("credit_rates", {})

    from app.models.promo import CreditRatesInfo
    credit_rates = CreditRatesInfo(
        istock_photo=rates.get("istock_photo", settings.ISTOCK_RATE),
        istock_video=rates.get("istock_video", settings.ISTOCK_RATE),
        adobe_photo=rates.get("adobe_photo", settings.ADOBE_RATE),
        adobe_video=rates.get("adobe_video", settings.ADOBE_RATE),
        shutterstock_photo=rates.get("shutterstock_photo", settings.SHUTTERSTOCK_RATE),
        shutterstock_video=rates.get("shutterstock_video", settings.SHUTTERSTOCK_RATE),
    )

    return BalanceWithPromosResponse(
        credits=user.get("credits", 0),
        exchange_rate=cfg.get("exchange_rate", settings.EXCHANGE_RATE),
        credit_rates=credit_rates,
        active_promos=active_promos,
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(default=50, le=200),
    user: dict = Depends(get_current_user),
):
    """Get credit transaction history."""
    user_id = user["user_id"]

    docs = list(
        transactions_ref()
        .where("user_id", "==", user_id)
        .stream()
    )

    # Sort by created_at descending (avoids composite index requirement)
    docs.sort(key=lambda d: d.to_dict().get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    docs = docs[:limit]

    items = []
    for doc in docs:
        tx = doc.to_dict()
        created = tx.get("created_at")
        date_str = created.strftime("%Y-%m-%d %H:%M") if created else ""
        items.append(TransactionItem(
            date=date_str,
            description=tx.get("description", ""),
            amount=tx.get("amount", 0),
            type=tx.get("type", ""),
        ))

    return HistoryResponse(
        transactions=items,
        balance=user.get("credits", 0),
    )


@router.post("/topup", response_model=TopUpWithPromoResponse)
async def topup(req: TopUpWithPromoRequest, user: dict = Depends(get_current_user)):
    """
    Submit a payment slip for top-up.
    Automatically applies best matching promotion.
    In production: verify slip via 3rd party API.
    For now: auto-approve for testing.
    """
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)

    # Create slip record
    slip_data = {
        "user_id": user_id,
        "status": "VERIFIED",  # Auto-approve for testing
        "image_url": "",  # Would store in Cloud Storage
        "amount_detected": req.amount,
        "bank_ref": None,
        "verification_method": "AUTO_DEV",
        "created_at": now,
        "verified_at": now,
    }
    _, slip_ref = slips_ref().add(slip_data)

    # Process top-up with promo engine
    result = process_topup_with_promo(
        user_id=user_id,
        user=user,
        topup_baht=float(req.amount),
        slip_id=slip_ref.id,
        promo_code=req.promo_code,
    )

    # Update slip with credited amount
    slips_ref().document(slip_ref.id).update({
        "amount_credited": result["total_credits"],
    })

    # Audit
    audit_logs_ref().add({
        "event_type": "TOPUP_SUCCESS",
        "user_id": user_id,
        "details": {
            "amount_thb": req.amount,
            "base_credits": result["base_credits"],
            "bonus_credits": result["bonus_credits"],
            "total_credits": result["total_credits"],
            "promo_applied": result["promo_applied"],
        },
        "severity": "INFO",
        "created_at": now,
    })

    msg = f"Added {result['total_credits']} credits"
    if result["promo_applied"]:
        msg += f" (incl. {result['bonus_credits']} bonus from '{result['promo_applied']}')"

    return TopUpWithPromoResponse(
        status="verified",
        base_credits=result["base_credits"],
        bonus_credits=result["bonus_credits"],
        total_credits=result["total_credits"],
        new_balance=result["new_balance"],
        promo_applied=result["promo_applied"],
        message=msg,
    )
