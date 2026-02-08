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


def _get_credit_rates(mode: str) -> tuple[int, int]:
    """
    Get credit rates (photo_rate, video_rate) for a platform.
    Reads from Firestore system_config/app_settings first,
    falls back to env config if Firestore unavailable.
    Returns (photo_rate, video_rate).
    """
    mode_lower = mode.lower()

    # Determine fallback rates from env config
    if "istock" in mode_lower:
        fb_photo = settings.ISTOCK_RATE
        fb_video = settings.ISTOCK_RATE
        fs_photo_key = "istock_photo"
        fs_video_key = "istock_video"
    elif "adobe" in mode_lower or "shutterstock" in mode_lower:
        fb_photo = settings.ADOBE_RATE
        fb_video = settings.ADOBE_RATE
        fs_photo_key = "adobe_photo"
        fs_video_key = "adobe_video"
    else:
        fb_photo = settings.ISTOCK_RATE
        fb_video = settings.ISTOCK_RATE
        fs_photo_key = "istock_photo"
        fs_video_key = "istock_video"

    # Try Firestore app_settings (admin-editable)
    try:
        doc = system_config_ref().document("app_settings").get()
        if doc.exists:
            rates = doc.to_dict().get("credit_rates", {})
            return (
                rates.get(fs_photo_key, fb_photo),
                rates.get(fs_video_key, fb_video),
            )
    except Exception as e:
        logger.warning(f"Failed to read credit_rates from Firestore: {e}")

    return (fb_photo, fb_video)


@router.post("/reserve", response_model=ReserveJobResponse)
async def reserve_job(req: ReserveJobRequest, user: dict = Depends(get_current_user)):
    """
    Reserve a job: deduct credits upfront, return encrypted config.
    Client must call /job/finalize when done to get refund for unused.
    """
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)

    # Check user status (§7.1 step 2)
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")

    # Calculate cost with separate photo/video rates
    photo_rate, video_rate = _get_credit_rates(req.mode)
    photos = req.photo_count
    videos = req.video_count
    # If client didn't send photo/video breakdown, treat all as photo
    if photos == 0 and videos == 0:
        photos = req.file_count
    total_cost = (photos * photo_rate) + (videos * video_rate)
    current_credits = user.get("credits", 0)

    # Generate job token
    job_token = str(uuid.uuid4())
    expires_at = now + timedelta(hours=settings.JOB_EXPIRE_HOURS)

    # Atomic credit deduction using Firestore Transaction (§7.1 step 6)
    db = firestore.Client()
    user_ref = users_ref().document(user_id)
    new_balance = 0

    @firestore.transactional
    def reserve_transaction(transaction):
        nonlocal new_balance
        snapshot = user_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="User not found")
        current = snapshot.to_dict().get("credits", 0)
        if current < total_cost:
            raise HTTPException(
                status_code=402,
                detail="Insufficient credits",
            )
        new_balance = current - total_cost
        transaction.update(user_ref, {
            "credits": new_balance,
            "last_active": now,
        })

    try:
        reserve_transaction(db.transaction())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reserve transaction failed: {e}")
        raise HTTPException(status_code=500, detail="Credit deduction failed")

    # Create job document
    jobs_ref().add({
        "job_token": job_token,
        "user_id": user_id,
        "status": "RESERVED",
        "mode": req.mode,
        "keyword_style": req.keyword_style or None,
        "file_count": req.file_count,
        "photo_count": photos,
        "video_count": videos,
        "photo_rate": photo_rate,
        "video_rate": video_rate,
        "credit_rate": photo_rate,  # backward compat
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
    cache_threshold = 20

    if config_doc.exists:
        sys_config = config_doc.to_dict()
        blacklist = sys_config.get("blacklist", [])
        cache_threshold = sys_config.get("context_cache_threshold", 20)

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

    logger.info(f"Job reserved: {job_token} ({photos}p+{videos}v, photo_rate={photo_rate}, video_rate={video_rate}, cost={total_cost})")
    return ReserveJobResponse(
        job_token=job_token,
        reserved_credits=total_cost,
        photo_rate=photo_rate,
        video_rate=video_rate,
        config=encrypted_config,
        dictionary=dictionary,
        blacklist=blacklist,
        concurrency={
            "image": settings.MAX_CONCURRENT_IMAGES,
            "video": settings.MAX_CONCURRENT_VIDEOS,
        },
        cache_threshold=cache_threshold,
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

    if job.get("status") not in ("RESERVED", "PROCESSING"):
        raise HTTPException(status_code=400, detail=f"Job cannot be finalized (status: {job.get('status')})")

    # Anti-cheat validation (§7.2 spec)
    file_count = job.get("file_count", 0)
    if req.success + req.failed > file_count:
        logger.warning(f"Anti-cheat: {user_id} claimed {req.success}+{req.failed} > {file_count} files")
        raise HTTPException(status_code=400, detail="Claimed file count exceeds reserved amount")
    if req.success > file_count:
        logger.warning(f"Anti-cheat: {user_id} claimed success={req.success} > {file_count}")
        raise HTTPException(status_code=400, detail="Success count exceeds reserved file count")

    # Calculate refund using photo/video rates stored in job
    p_rate = job.get("photo_rate", job.get("credit_rate", 3))
    v_rate = job.get("video_rate", p_rate)
    reserved = job.get("reserved_credits", 0)
    # actual_usage = successful photos × photo_rate + successful videos × video_rate
    # Client sends req.photos / req.videos as total counts (success+fail).
    # We use a weighted approach: proportional success across file types.
    total_reported = req.success + req.failed
    if total_reported > 0 and req.photos + req.videos > 0:
        # Calculate actual usage based on ratio of success files
        success_ratio = req.success / total_reported if total_reported > 0 else 0
        successful_photos = round(req.photos * success_ratio)
        successful_videos = req.success - successful_photos
        if successful_videos < 0:
            successful_videos = 0
            successful_photos = req.success
        actual_usage = (successful_photos * p_rate) + (successful_videos * v_rate)
    else:
        actual_usage = req.success * p_rate
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
