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
from app.database import users_ref, transactions_ref, slips_ref, audit_logs_ref
from app.dependencies import get_current_user
from app.config import settings

logger = logging.getLogger("bigeye-api")
router = APIRouter(prefix="/credit", tags=["Credit"])


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: dict = Depends(get_current_user)):
    """Get current credit balance."""
    return BalanceResponse(credits=user.get("credits", 0))


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


@router.post("/topup", response_model=TopUpResponse)
async def topup(req: TopUpRequest, user: dict = Depends(get_current_user)):
    """
    Submit a payment slip for top-up.
    In production: verify slip via 3rd party API.
    For now: auto-approve for testing.
    """
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)

    # Calculate credits
    credits_to_add = req.amount * settings.EXCHANGE_RATE

    # Create slip record
    slip_data = {
        "user_id": user_id,
        "status": "VERIFIED",  # Auto-approve for testing
        "image_url": "",  # Would store in Cloud Storage
        "amount_detected": req.amount,
        "amount_credited": credits_to_add,
        "bank_ref": None,
        "verification_method": "AUTO_DEV",
        "created_at": now,
        "verified_at": now,
    }
    _, slip_ref = slips_ref().add(slip_data)

    # Atomic credit update
    db = users_ref().document(user_id)
    new_balance = user.get("credits", 0) + credits_to_add
    db.update({
        "credits": firestore.Increment(credits_to_add),
        "total_topup_baht": firestore.Increment(req.amount),
        "last_active": now,
    })

    # Create transaction record
    transactions_ref().add({
        "user_id": user_id,
        "type": "TOPUP",
        "amount": credits_to_add,
        "balance_after": new_balance,
        "reference_id": slip_ref.id,
        "description": f"Top-up {req.amount} THB ({credits_to_add} credits)",
        "created_at": now,
        "metadata": {
            "baht_amount": req.amount,
            "slip_ref": slip_ref.id,
        },
    })

    # Audit
    audit_logs_ref().add({
        "event_type": "TOPUP_SUCCESS",
        "user_id": user_id,
        "details": {"amount_thb": req.amount, "credits": credits_to_add},
        "severity": "INFO",
        "created_at": now,
    })

    logger.info(f"Top-up: {user_id} +{credits_to_add} credits ({req.amount} THB)")
    return TopUpResponse(
        status="verified",
        credits_added=credits_to_add,
        new_balance=new_balance,
        message=f"Added {credits_to_add} credits",
    )
