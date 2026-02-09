"""
BigEye Pro — System Router
POST /system/check-update, GET /system/health,
POST /system/cleanup-expired-jobs, POST /system/generate-daily-report
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException
from google.cloud import firestore

from app.models import CheckUpdateRequest, CheckUpdateResponse, HealthResponse
from app.database import (
    system_config_ref, jobs_ref, users_ref, transactions_ref,
    audit_logs_ref, daily_reports_ref,
)
from app.config import settings

logger = logging.getLogger("bigeye-api")
router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.post("/check-update", response_model=CheckUpdateResponse)
async def check_update(req: CheckUpdateRequest):
    """Check for app updates and maintenance mode."""
    config_doc = system_config_ref().document("app_settings").get()

    if not config_doc.exists:
        return CheckUpdateResponse()

    cfg = config_doc.to_dict()

    # Check maintenance mode
    if cfg.get("maintenance_mode", False):
        return CheckUpdateResponse(
            maintenance=True,
            maintenance_message=cfg.get("maintenance_message", "Server maintenance in progress"),
        )

    # Check version
    latest = cfg.get("app_latest_version", "")
    force_below = cfg.get("force_update_below", "")
    download_url = cfg.get("app_download_url", "")
    notes = cfg.get("app_update_notes", "")

    update_available = False
    force = False

    if latest and req.version:
        update_available = _version_lt(req.version, latest)
        if force_below:
            force = _version_lt(req.version, force_below)

    return CheckUpdateResponse(
        update_available=update_available,
        version=latest,
        download_url=download_url,
        force=force,
        notes=notes,
    )


@router.post("/cleanup-expired-jobs")
async def cleanup_expired_jobs():
    """
    Cleanup expired RESERVED jobs — auto-refund unused credits.
    Called by Cloud Scheduler every hour.
    """
    now = datetime.now(timezone.utc)
    count = 0

    expired_docs = (
        jobs_ref()
        .where("status", "==", "RESERVED")
        .where("expires_at", "<", now)
        .stream()
    )

    for doc in expired_docs:
        job = doc.to_dict()
        job_id = doc.id
        user_id = job.get("user_id", "")
        reserved = job.get("reserved_credits", 0)

        # Refund all reserved credits
        if user_id and reserved > 0:
            users_ref().document(user_id).update({
                "credits": firestore.Increment(reserved),
            })

            # Get updated balance
            user_doc = users_ref().document(user_id).get()
            balance = user_doc.to_dict().get("credits", 0) if user_doc.exists else 0

            transactions_ref().add({
                "user_id": user_id,
                "type": "REFUND",
                "amount": reserved,
                "balance_after": balance,
                "reference_id": job.get("job_token", ""),
                "description": f"Auto-refund expired job ({reserved} credits)",
                "created_at": now,
            })

        # Update job status
        jobs_ref().document(job_id).update({
            "status": "EXPIRED",
            "refund_amount": reserved,
            "completed_at": now,
        })

        audit_logs_ref().add({
            "event_type": "JOB_EXPIRED_AUTO_REFUND",
            "user_id": user_id,
            "details": {"job_token": job.get("job_token"), "refunded": reserved},
            "severity": "INFO",
            "created_at": now,
        })

        count += 1

    logger.info(f"Cleanup: {count} expired jobs refunded")
    return {"cleaned": count}


@router.post("/generate-daily-report")
async def generate_daily_report():
    """
    Generate daily report. Called by Cloud Scheduler at midnight.
    """
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    # Count new users
    new_users = len(list(
        users_ref()
        .where("created_at", ">=", start)
        .where("created_at", "<", end)
        .stream()
    ))

    # Count jobs
    jobs_today = list(
        jobs_ref()
        .where("created_at", ">=", start)
        .where("created_at", "<", end)
        .stream()
    )
    total_jobs = len(jobs_today)
    total_files = sum(j.to_dict().get("success_count", 0) + j.to_dict().get("failed_count", 0) for j in jobs_today)

    # Sum topups
    topups = list(
        transactions_ref()
        .where("type", "==", "TOPUP")
        .where("created_at", ">=", start)
        .where("created_at", "<", end)
        .stream()
    )
    total_topup_baht = sum(t.to_dict().get("metadata", {}).get("baht_amount", 0) for t in topups)
    total_credits_sold = sum(t.to_dict().get("amount", 0) for t in topups)

    report = {
        "date": today,
        "new_users": new_users,
        "active_users": 0,  # Would need distinct user_id from jobs
        "total_topup_baht": total_topup_baht,
        "total_credits_sold": total_credits_sold,
        "total_jobs": total_jobs,
        "total_files_processed": total_files,
        "generated_at": now,
    }

    daily_reports_ref().document(today).set(report)
    logger.info(f"Daily report generated: {today}")
    return report


@router.post("/expire-promotions")
async def expire_promotions_endpoint():
    """
    Auto-expire promotions past end_date.
    Called by Cloud Scheduler every hour.
    """
    from app.services.promo_engine import expire_promotions
    count = expire_promotions()
    logger.info(f"Expire promos: {count} expired")
    return {"expired": count}


def _version_lt(v1: str, v2: str) -> bool:
    """Compare version strings. Returns True if v1 < v2."""
    try:
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        return parts1 < parts2
    except (ValueError, AttributeError):
        return False
