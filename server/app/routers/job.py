"""
BigEye Pro — Job Router
POST /job/reserve, POST /job/finalize
Reserve-Refund Protocol: deduct credits upfront, refund unused after job.
"""
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from app.models import (
    ReserveJobRequest, ReserveJobResponse,
    FinalizeJobRequest, FinalizeJobResponse,
)
from app.database import users_ref, jobs_ref, transactions_ref, system_config_ref, audit_logs_ref
from app.dependencies import get_current_user
from app.security import encrypt_aes
from app.config import settings

logger = logging.getLogger("bigeye-api")
router = APIRouter(prefix="/job", tags=["Job"])


def _get_credit_rate(mode: str) -> int:
    """Get credit rate per file for a platform."""
    mode_lower = mode.lower()
    if "istock" in mode_lower:
        return settings.ISTOCK_RATE
    elif "adobe" in mode_lower:
        return settings.ADOBE_RATE
    elif "shutterstock" in mode_lower:
        return settings.SHUTTERSTOCK_RATE
    return settings.ISTOCK_RATE


@router.post("/reserve", response_model=ReserveJobResponse)
async def reserve_job(req: ReserveJobRequest, user: dict = Depends(get_current_user)):
    """
    Reserve a job: deduct credits upfront, return encrypted config.
    Client must call /job/finalize when done to get refund for unused.
    """
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)

    # Calculate cost
    rate = _get_credit_rate(req.mode)
    total_cost = req.file_count * rate
    current_credits = user.get("credits", 0)

    # Check balance
    if current_credits < total_cost:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits",
            headers={
                "X-Required": str(total_cost),
                "X-Available": str(current_credits),
                "X-Shortfall": str(total_cost - current_credits),
            },
        )

    # Generate job token
    job_token = str(uuid.uuid4())
    expires_at = now + timedelta(hours=settings.JOB_EXPIRE_HOURS)

    # Deduct credits atomically
    user_ref = users_ref().document(user_id)
    new_balance = current_credits - total_cost
    user_ref.update({
        "credits": firestore.Increment(-total_cost),
        "last_active": now,
    })

    # Create job document
    jobs_ref().add({
        "job_token": job_token,
        "user_id": user_id,
        "status": "RESERVED",
        "mode": req.mode,
        "keyword_style": req.keyword_style or None,
        "file_count": req.file_count,
        "photo_count": 0,
        "video_count": 0,
        "credit_rate": rate,
        "reserved_credits": total_cost,
        "actual_usage": 0,
        "refund_amount": 0,
        "success_count": 0,
        "failed_count": 0,
        "created_at": now,
        "completed_at": None,
        "expires_at": expires_at,
        "client_info": {
            "app_version": req.version,
            "model_used": req.model,
            "hardware_id": user.get("hardware_id", ""),
        },
    })

    # Create transaction: RESERVE
    transactions_ref().add({
        "user_id": user_id,
        "type": "RESERVE",
        "amount": -total_cost,
        "balance_after": new_balance,
        "reference_id": job_token,
        "description": f"Reserve {req.file_count} files ({req.mode})",
        "created_at": now,
    })

    # Load system config for prompts + blacklist + dictionary
    config_doc = system_config_ref().document("app_settings").get()
    encrypted_config = ""
    dictionary = ""
    blacklist = []

    if config_doc.exists:
        sys_config = config_doc.to_dict()
        blacklist = sys_config.get("blacklist", [])

        # Select prompt based on mode + keyword_style
        prompts = sys_config.get("prompts", {})
        is_istock = "istock" in req.mode.lower()

        if is_istock:
            prompt_text = prompts.get("istock", "")
            # Include dictionary for iStock mode (dictionary-strict)
            dictionary = sys_config.get("dictionary", "")
        elif req.keyword_style and "single" in req.keyword_style.lower():
            prompt_text = prompts.get("single", "")
        else:
            # Default: hybrid (Adobe/Shutterstock)
            prompt_text = prompts.get("hybrid", "")

        # Encrypt prompt for delivery
        try:
            encrypted_config = encrypt_aes(prompt_text)
        except Exception as e:
            logger.warning(f"Config encryption failed: {e}")

    # Audit
    audit_logs_ref().add({
        "event_type": "JOB_RESERVED",
        "user_id": user_id,
        "details": {
            "job_token": job_token,
            "file_count": req.file_count,
            "mode": req.mode,
            "cost": total_cost,
        },
        "severity": "INFO",
        "created_at": now,
    })

    logger.info(f"Job reserved: {job_token} ({req.file_count} files, {total_cost} credits)")
    return ReserveJobResponse(
        job_token=job_token,
        config=encrypted_config,
        dictionary=dictionary,
        blacklist=blacklist,
        concurrency={
            "image": settings.MAX_CONCURRENT_IMAGES,
            "video": settings.MAX_CONCURRENT_VIDEOS,
        },
    )


@router.post("/finalize", response_model=FinalizeJobResponse)
async def finalize_job(req: FinalizeJobRequest, user: dict = Depends(get_current_user)):
    """
    Finalize a job: calculate actual usage and refund unused credits.
    """
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)

    # Find job by token
    job_docs = list(
        jobs_ref()
        .where("job_token", "==", req.job_token)
        .where("user_id", "==", user_id)
        .limit(1)
        .stream()
    )

    if not job_docs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_doc = job_docs[0]
    job = job_doc.to_dict()
    job_id = job_doc.id

    if job.get("status") in ("COMPLETED", "REFUNDED"):
        # Already finalized — return existing data
        user_doc = users_ref().document(user_id).get()
        current_balance = user_doc.to_dict().get("credits", 0) if user_doc.exists else 0
        return FinalizeJobResponse(
            refunded=job.get("refund_amount", 0),
            balance=current_balance,
        )

    # Calculate refund
    rate = job.get("credit_rate", 3)
    reserved = job.get("reserved_credits", 0)
    actual_usage = req.success * rate  # Only successful files cost credits
    refund = reserved - actual_usage
    if refund < 0:
        refund = 0

    # Update job
    jobs_ref().document(job_id).update({
        "status": "COMPLETED",
        "success_count": req.success,
        "failed_count": req.failed,
        "photo_count": req.photos,
        "video_count": req.videos,
        "actual_usage": actual_usage,
        "refund_amount": refund,
        "completed_at": now,
    })

    # Refund credits
    new_balance = 0
    if refund > 0:
        users_ref().document(user_id).update({
            "credits": firestore.Increment(refund),
        })

        # Refund transaction
        user_doc = users_ref().document(user_id).get()
        new_balance = user_doc.to_dict().get("credits", 0) if user_doc.exists else 0

        transactions_ref().add({
            "user_id": user_id,
            "type": "REFUND",
            "amount": refund,
            "balance_after": new_balance,
            "reference_id": req.job_token,
            "description": f"Refund {refund} credits ({req.failed} failed files)",
            "created_at": now,
        })
    else:
        user_doc = users_ref().document(user_id).get()
        new_balance = user_doc.to_dict().get("credits", 0) if user_doc.exists else 0

    # Update user stats
    users_ref().document(user_id).update({
        "total_credits_used": firestore.Increment(actual_usage),
        "last_active": now,
    })

    # Audit
    audit_logs_ref().add({
        "event_type": "JOB_COMPLETED",
        "user_id": user_id,
        "details": {
            "job_token": req.job_token,
            "success": req.success,
            "failed": req.failed,
            "actual_usage": actual_usage,
            "refund": refund,
        },
        "severity": "INFO",
        "created_at": now,
    })

    logger.info(f"Job finalized: {req.job_token} (ok={req.success}, fail={req.failed}, refund={refund})")
    return FinalizeJobResponse(
        refunded=refund,
        balance=new_balance,
    )
