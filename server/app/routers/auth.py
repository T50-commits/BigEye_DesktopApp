"""
BigEye Pro — Auth Router
POST /auth/register, POST /auth/login
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from google.cloud.firestore_v1 import FieldFilter

from app.models import RegisterRequest, LoginRequest, AuthResponse
from app.database import users_ref, audit_logs_ref
from app.security import hash_password, verify_password, create_jwt_token
from app.rate_limit import limiter
from app.services.promo_engine import apply_welcome_bonus

logger = logging.getLogger("bigeye-api")
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse)
@limiter.limit("3/minute")
async def register(request: Request, req: RegisterRequest):
    """Register a new user account."""
    # Check duplicate email
    existing = list(
        users_ref()
        .where(filter=FieldFilter("email", "==", req.email.lower()))
        .limit(1)
        .stream()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Check duplicate hardware_id — prevent multi-account abuse for free credits
    existing_hw = list(
        users_ref()
        .where(filter=FieldFilter("hardware_id", "==", req.hardware_id))
        .limit(1)
        .stream()
    )
    if existing_hw:
        audit_logs_ref().add({
            "event_type": "REGISTER_BLOCKED_DUPLICATE_DEVICE",
            "details": {"hardware_id": req.hardware_id[:8] + "...", "email": req.email.lower()},
            "severity": "WARNING",
            "created_at": datetime.now(timezone.utc),
        })
        raise HTTPException(
            status_code=409,
            detail="อุปกรณ์นี้มีบัญชีอยู่แล้ว กรุณาใช้บัญชีเดิมหรือติดต่อผู้ดูแลระบบ",
        )

    now = datetime.now(timezone.utc)
    user_data = {
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "full_name": req.full_name,
        "hardware_id": req.hardware_id,
        "tier": "standard",
        "credits": 0,
        "status": "active",
        "created_at": now,
        "last_login": now,
        "last_active": now,
        "total_topup_baht": 0,
        "total_credits_used": 0,
        "app_version": "",
        "metadata": {
            "os": req.os_type,
            "registration_ip": "",
            "notes": "",
        },
    }

    # Create user document
    _, doc_ref = users_ref().add(user_data)
    user_id = doc_ref.id

    # Create JWT
    token = create_jwt_token(user_id, req.email.lower())

    # Apply welcome bonus if any ACTIVE WELCOME_BONUS promo exists
    welcome_credits = 0
    try:
        bonus_result = apply_welcome_bonus(user_id)
        if bonus_result:
            welcome_credits = bonus_result["bonus_credits"]
            logger.info(f"Welcome bonus: {user_id} +{welcome_credits} cr ({bonus_result['promo_name']})")
    except Exception as e:
        logger.warning(f"Failed to apply welcome bonus for {user_id}: {e}")

    # Audit log
    audit_logs_ref().add({
        "event_type": "USER_REGISTER",
        "user_id": user_id,
        "details": {"email": req.email.lower(), "welcome_bonus": welcome_credits},
        "severity": "INFO",
        "created_at": now,
    })

    logger.info(f"User registered: {req.email}")
    return AuthResponse(
        token=token,
        user_id=user_id,
        email=req.email.lower(),
        full_name=req.full_name,
        credits=welcome_credits,
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest):
    """Login with email + password. Validates hardware_id binding."""
    now = datetime.now(timezone.utc)

    # Find user by email
    docs = list(
        users_ref()
        .where(filter=FieldFilter("email", "==", req.email.lower()))
        .limit(1)
        .stream()
    )
    if not docs:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    doc = docs[0]
    user = doc.to_dict()
    user_id = doc.id

    # Check password
    if not verify_password(req.password, user.get("password_hash", "")):
        audit_logs_ref().add({
            "event_type": "LOGIN_FAILED_WRONG_PASSWORD",
            "user_id": user_id,
            "severity": "WARNING",
            "created_at": now,
        })
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check account status
    if user.get("status") in ("banned", "suspended"):
        raise HTTPException(status_code=403, detail="Account suspended")

    # Soft bind: allow login from new device but log the change
    stored_hw = user.get("hardware_id", "")
    update_data = {
        "last_login": now,
        "last_active": now,
        "app_version": req.app_version,
    }
    if stored_hw and stored_hw != req.hardware_id:
        # Device changed — update to new hardware_id (soft bind)
        update_data["hardware_id"] = req.hardware_id
        audit_logs_ref().add({
            "event_type": "LOGIN_DEVICE_CHANGED",
            "user_id": user_id,
            "details": {
                "old_device": stored_hw[:8] + "...",
                "new_device": req.hardware_id[:8] + "...",
            },
            "severity": "INFO",
            "created_at": now,
        })
        logger.info(f"Device changed for user {user_id} — hardware_id updated")
    elif not stored_hw:
        update_data["hardware_id"] = req.hardware_id
        logger.info(f"Hardware ID bound for user {user_id}")
    users_ref().document(user_id).update(update_data)

    # Create JWT
    token = create_jwt_token(user_id, req.email.lower())

    logger.info(f"User login: {req.email}")
    return AuthResponse(
        token=token,
        user_id=user_id,
        email=user.get("email", ""),
        full_name=user.get("full_name", ""),
        credits=user.get("credits", 0),
    )
