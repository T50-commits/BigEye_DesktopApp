"""
BigEye Pro — Auth Router
POST /auth/register, POST /auth/login
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from google.cloud.firestore_v1 import FieldFilter

from app.models import RegisterRequest, LoginRequest, AuthResponse
from app.database import users_ref, audit_logs_ref
from app.security import hash_password, verify_password, create_jwt_token

logger = logging.getLogger("bigeye-api")
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
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

    now = datetime.now(timezone.utc)
    user_data = {
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "full_name": req.full_name,
        "phone": req.phone,
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

    # Audit log
    audit_logs_ref().add({
        "event_type": "USER_REGISTER",
        "user_id": user_id,
        "details": {"email": req.email.lower()},
        "severity": "INFO",
        "created_at": now,
    })

    logger.info(f"User registered: {req.email}")
    return AuthResponse(
        token=token,
        user_id=user_id,
        email=req.email.lower(),
        full_name=req.full_name,
        credits=0,
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
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
    if user.get("status") == "banned":
        raise HTTPException(status_code=403, detail="Account suspended")

    # Check hardware_id binding
    stored_hw = user.get("hardware_id", "")
    if stored_hw and stored_hw != req.hardware_id:
        audit_logs_ref().add({
            "event_type": "LOGIN_FAILED_DEVICE_MISMATCH",
            "user_id": user_id,
            "details": {
                "stored": stored_hw[:8] + "...",
                "attempted": req.hardware_id[:8] + "...",
            },
            "severity": "WARNING",
            "created_at": now,
        })
        raise HTTPException(
            status_code=403,
            detail="This account is bound to a different device. Contact support.",
        )

    # Update last login
    users_ref().document(user_id).update({
        "last_login": now,
        "last_active": now,
        "app_version": req.app_version,
    })

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
