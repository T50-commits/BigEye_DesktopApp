"""
BigEye Pro — Credit Router
GET /credit/balance, GET /credit/history, POST /credit/topup
"""
import logging
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

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
from app.rate_limit import limiter
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


@router.get("/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    """Get current credit balance with active promotions and credit rates."""
    try:
        active_promos = get_active_promos_for_client()
    except Exception as e:
        logger.warning(f"Failed to fetch active promos: {e}")
        active_promos = []

    cfg = _load_app_settings()
    rates = cfg.get("credit_rates", {})

    credit_rates = {
        "istock_photo": rates.get("istock_photo", settings.ISTOCK_RATE),
        "istock_video": rates.get("istock_video", settings.ISTOCK_RATE),
        "adobe_photo": rates.get("adobe_photo", settings.ADOBE_RATE),
        "adobe_video": rates.get("adobe_video", settings.ADOBE_RATE),
        "shutterstock_photo": rates.get("shutterstock_photo", settings.SHUTTERSTOCK_RATE),
        "shutterstock_video": rates.get("shutterstock_video", settings.SHUTTERSTOCK_RATE),
    }

    # Bank info for top-up display (managed via Admin Dashboard)
    raw_bank = cfg.get("bank_info", {})
    # Only return structured bank_info if it's actually configured
    if raw_bank and any(raw_bank.get(k) for k in ("bank_name", "account_number", "account_name")):
        bank_info = {
            "bank_name": raw_bank.get("bank_name", ""),
            "account_number": raw_bank.get("account_number", ""),
            "account_name": raw_bank.get("account_name", ""),
        }
    else:
        bank_info = {}

    return {
        "credits": user.get("credits", 0),
        "exchange_rate": cfg.get("exchange_rate", settings.EXCHANGE_RATE),
        "credit_rates": credit_rates,
        "active_promos": active_promos,
        "bank_info": bank_info,
    }


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
        if created:
            # Convert UTC → UTC+7 (Thailand)
            local_dt = created.astimezone(timezone(timedelta(hours=7)))
            date_str = local_dt.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = ""
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


async def _verify_slip_with_slip2go(qr_data: str) -> dict:
    """Call Slip2Go API to verify a payment slip QR code.
    Sends checkCondition for duplicate + receiver validation.
    Returns the parsed response dict on success, raises HTTPException on failure.

    Slip2Go response codes:
      200000 = Slip Found
      200001 = Get Info Success
      200200 = Slip is Valid (all conditions passed)
      200401 = Recipient Account Not Match
      200402 = Transfer Amount Not Match
      200403 = Transfer Date Not Match
      200404 = Slip Not Found
      200500 = Slip is Fraud
      200501 = Slip is Duplicated
    """
    if not settings.SLIP2GO_SECRET_KEY:
        logger.error("SLIP2GO_SECRET_KEY is not set — top-up via QR is disabled")
        raise HTTPException(
            status_code=503,
            detail="ระบบตรวจสอบสลิปยังไม่ได้ตั้งค่า กรุณาแจ้งผู้ดูแลระบบ",
        )

    url = f"{settings.SLIP2GO_API_URL}/api/verify-slip/qr-code/info"
    headers = {
        "Authorization": f"Bearer {settings.SLIP2GO_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "payload": {
            "qrCode": qr_data,
            "checkCondition": {
                "checkDuplicate": True,
            },
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Slip verification timed out")
    except httpx.RequestError as e:
        logger.error(f"Slip2Go request error: {e}")
        raise HTTPException(status_code=502, detail="Cannot connect to slip verification service")

    if resp.status_code != 200:
        logger.warning(f"Slip2Go HTTP error: {resp.status_code} {resp.text[:500]}")
        raise HTTPException(status_code=502, detail="Slip verification service error")

    body = resp.json()
    response_code = int(body.get("code", 0))

    # Handle Slip2Go response codes
    if response_code == 200501:
        raise HTTPException(status_code=409, detail="สลิปนี้เคยใช้แล้ว (duplicate)")
    if response_code == 200500:
        raise HTTPException(status_code=400, detail="สลิปปลอม (fraud detected)")
    if response_code == 200404:
        raise HTTPException(status_code=400, detail="ไม่พบข้อมูลสลิปในระบบธนาคาร")
    if response_code == 200401:
        raise HTTPException(status_code=400, detail="บัญชีผู้รับไม่ตรงกับบัญชีร้าน")
    if response_code == 200402:
        raise HTTPException(status_code=400, detail="จำนวนเงินไม่ตรงกับเงื่อนไข")
    if response_code == 200403:
        raise HTTPException(status_code=400, detail="วันที่โอนไม่ตรงกับเงื่อนไข")

    # Success codes: 200000 (Slip Found), 200001 (Info Success), 200200 (Valid)
    if response_code not in (200000, 200001, 200200):
        msg = body.get("message", "Unknown error")
        logger.warning(f"Slip2Go unexpected code: {response_code} msg={msg}")
        raise HTTPException(status_code=400, detail=f"Slip verification failed: {msg}")

    return body


def _check_duplicate_bank_ref(bank_ref: str) -> bool:
    """Check if a bank_ref already exists in the slips collection (our own duplicate check)."""
    if not bank_ref:
        return False
    existing = list(
        slips_ref()
        .where(filter=FieldFilter("bank_ref", "==", bank_ref))
        .where(filter=FieldFilter("status", "==", "VERIFIED"))
        .limit(1)
        .stream()
    )
    return len(existing) > 0


def _check_duplicate_qr(qr_data: str) -> bool:
    """Check if this exact QR string was already VERIFIED — blocks before calling Slip2Go API."""
    if not qr_data:
        return False
    existing = list(
        slips_ref()
        .where(filter=FieldFilter("qr_data", "==", qr_data))
        .where(filter=FieldFilter("status", "==", "VERIFIED"))
        .limit(1)
        .stream()
    )
    return len(existing) > 0


def _check_recent_rejection(user_id: str, cooldown_minutes: int = 5) -> bool:
    """Check if user had a REJECTED slip within cooldown window — prevents spam."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
    recent = list(
        slips_ref()
        .where(filter=FieldFilter("user_id", "==", user_id))
        .where(filter=FieldFilter("status", "==", "REJECTED"))
        .where(filter=FieldFilter("created_at", ">=", cutoff))
        .limit(1)
        .stream()
    )
    return len(recent) > 0


@router.post("/topup", response_model=TopUpWithPromoResponse)
@limiter.limit("3/minute;10/hour")
async def topup(request: Request, req: TopUpWithPromoRequest, user: dict = Depends(get_current_user)):
    """
    Submit a payment slip for top-up.
    0. Pre-checks (rate limit, QR dup, cooldown) — before calling Slip2Go
    1. Create PENDING slip record
    2. Verify QR code via Slip2Go API (with checkDuplicate)
    3. Our own duplicate check via bank_ref in Firestore
    4. Validate receiver name
    5. Use verified amount from Slip2Go (NOT from client)
    6. Apply promotions and credit the user
    """
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)

    # ── Step 0: Pre-checks before calling Slip2Go (saves API cost) ──

    # 0a. Check if this exact QR was already verified (free check via Firestore)
    if _check_duplicate_qr(req.slip):
        raise HTTPException(status_code=409, detail="สลิปนี้เคยใช้แล้ว (duplicate)")

    # 0b. Cooldown: if user had a rejected slip in last 5 minutes, block
    if _check_recent_rejection(user_id, cooldown_minutes=5):
        raise HTTPException(
            status_code=429,
            detail="กรุณารอ 5 นาทีก่อนส่งสลิปใหม่",
        )

    # ── Step 1: Create PENDING slip record ──
    slip_data = {
        "user_id": user_id,
        "status": "PENDING",
        "image_url": "",
        "amount_detected": None,
        "bank_ref": None,
        "qr_data": req.slip,
        "verification_method": "AUTO_API",
        "created_at": now,
    }
    _, slip_doc_ref = slips_ref().add(slip_data)
    slip_id = slip_doc_ref.id

    try:
        # ── Step 2: Verify with Slip2Go ──
        slip2go_resp = await _verify_slip_with_slip2go(req.slip)

        # Extract data from Slip2Go response
        data = slip2go_resp.get("data", {})
        bank_ref = data.get("transRef", "")
        verified_amount = float(data.get("amount", 0))
        receiver_obj = data.get("receiver", {})
        receiver_name = receiver_obj.get("account", {}).get("name", "") or receiver_obj.get("name", "") or receiver_obj.get("displayName", "")
        sender_obj = data.get("sender", {})
        sender_name = sender_obj.get("account", {}).get("name", "") or sender_obj.get("name", "") or sender_obj.get("displayName", "")
        logger.info(f"Slip2Go verified: amount={verified_amount}, receiver={receiver_name}, sender={sender_name}, ref={bank_ref}")

        # ── Step 3: Our own duplicate check (backup) ──
        if bank_ref and _check_duplicate_bank_ref(bank_ref):
            slips_ref().document(slip_id).update({
                "status": "DUPLICATE",
                "bank_ref": bank_ref,
                "amount_detected": verified_amount,
            })
            raise HTTPException(status_code=409, detail="สลิปนี้เคยใช้แล้ว (duplicate)")

        # ── Step 4: Validate receiver ──
        expected_receiver = settings.SLIP2GO_RECEIVER_NAME
        receiver_names = [n.strip().lower() for n in expected_receiver.split(",") if n.strip()]
        receiver_match = not receiver_names or any(n in receiver_name.lower() for n in receiver_names)
        if expected_receiver and not receiver_match:
            slips_ref().document(slip_id).update({
                "status": "REJECTED",
                "bank_ref": bank_ref,
                "amount_detected": verified_amount,
                "reject_reason": f"ผู้รับไม่ถูกต้อง: {receiver_name}",
            })
            raise HTTPException(
                status_code=400,
                detail=f"สลิปนี้ไม่ได้โอนเข้าบัญชี {expected_receiver}",
            )

        # ── Step 5: Validate amount ──
        if verified_amount <= 0:
            slips_ref().document(slip_id).update({
                "status": "REJECTED",
                "bank_ref": bank_ref,
                "amount_detected": verified_amount,
                "reject_reason": "จำนวนเงินไม่ถูกต้อง",
            })
            raise HTTPException(status_code=400, detail="จำนวนเงินในสลิปไม่ถูกต้อง")

        # ── Step 6: Mark slip as VERIFIED ──
        slips_ref().document(slip_id).update({
            "status": "VERIFIED",
            "bank_ref": bank_ref,
            "amount_detected": verified_amount,
            "verified_at": datetime.now(timezone.utc),
            "verification_result": {
                "provider": "Slip2Go",
                "raw_response": data,
                "confidence": 1.0,
            },
            "metadata": {
                "sender_name": sender_name,
                "receiver_account": data.get("receiver", {}).get("account", {}).get("value", ""),
            },
        })

        # ── Step 7: Process top-up with promo engine (use Slip2Go amount!) ──
        result = process_topup_with_promo(
            user_id=user_id,
            user=user,
            topup_baht=verified_amount,
            slip_id=slip_id,
            promo_code=req.promo_code,
        )

        # Update slip with credited amount
        slips_ref().document(slip_id).update({
            "amount_credited": result["total_credits"],
        })

        # Audit
        audit_logs_ref().add({
            "event_type": "TOPUP_SUCCESS",
            "user_id": user_id,
            "details": {
                "amount_thb": verified_amount,
                "bank_ref": bank_ref,
                "base_credits": result["base_credits"],
                "bonus_credits": result["bonus_credits"],
                "total_credits": result["total_credits"],
                "promo_applied": result["promo_applied"],
            },
            "severity": "INFO",
            "created_at": datetime.now(timezone.utc),
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

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        # Unexpected error — mark slip as failed
        logger.error(f"TopUp failed for {user_id}: {e}")
        slips_ref().document(slip_id).update({
            "status": "REJECTED",
            "reject_reason": f"System error: {str(e)[:200]}",
        })
        raise HTTPException(status_code=500, detail="เกิดข้อผิดพลาดในการเติมเงิน กรุณาลองใหม่")
