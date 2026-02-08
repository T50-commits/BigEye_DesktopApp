"""
BigEye Pro — Admin Promotion Router
CRUD + activate/pause/cancel/clone for promotions.
"""
import logging
from datetime import datetime, timezone
from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from app.database import users_ref
from app.dependencies import get_current_user
from app.config import settings
from app.models.promo import (
    CreatePromoRequest, UpdatePromoRequest,
    PromoResponse, PromoListResponse, PromoCreateResponse, PromoActionResponse,
    PromoStatsResponse, PromoStats, PromoConditions, PromoReward, PromoDisplay,
    RedemptionItem,
)
from app.services.promo_engine import _promotions_ref, _promo_redemptions_ref

logger = logging.getLogger("bigeye-api")
router = APIRouter(prefix="/admin/promo", tags=["Admin - Promotions"])


# ── Admin Dependency ──

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Verify that the current user is an admin."""
    user_id = user.get("user_id", "")
    if user_id not in settings.admin_uid_list:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Helpers ──

def _doc_to_promo_response(doc_id: str, data: dict) -> PromoResponse:
    """Convert Firestore document to PromoResponse."""
    cond = data.get("conditions", {})
    reward = data.get("reward", {})
    display = data.get("display", {})
    stats = data.get("stats", {})

    # Convert timestamps to ISO strings
    def ts_to_str(val):
        if val is None:
            return None
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)

    return PromoResponse(
        promo_id=doc_id,
        name=data.get("name", ""),
        code=data.get("code"),
        type=data.get("type", ""),
        status=data.get("status", "DRAFT"),
        priority=data.get("priority", 0),
        conditions=PromoConditions(
            start_date=cond.get("start_date", datetime.now(timezone.utc)),
            end_date=cond.get("end_date"),
            min_topup_baht=cond.get("min_topup_baht"),
            max_topup_baht=cond.get("max_topup_baht"),
            max_redemptions=cond.get("max_redemptions"),
            max_per_user=cond.get("max_per_user"),
            eligible_tiers=cond.get("eligible_tiers"),
            new_users_only=cond.get("new_users_only", False),
            first_topup_only=cond.get("first_topup_only", False),
            require_code=cond.get("require_code", False),
        ),
        reward=PromoReward(
            type=reward.get("type", "BONUS_CREDITS"),
            bonus_credits=reward.get("bonus_credits"),
            override_rate=reward.get("override_rate"),
            bonus_percentage=reward.get("bonus_percentage"),
            tiers=reward.get("tiers"),
        ),
        display=PromoDisplay(
            banner_text=display.get("banner_text", ""),
            banner_color=display.get("banner_color", "#FF4560"),
            show_in_client=display.get("show_in_client", True),
            show_in_topup=display.get("show_in_topup", True),
        ),
        stats=PromoStats(
            total_redemptions=stats.get("total_redemptions", 0),
            total_bonus_credits=stats.get("total_bonus_credits", 0),
            total_baht_collected=stats.get("total_baht_collected", 0),
            unique_users=stats.get("unique_users", 0),
        ),
        created_at=ts_to_str(data.get("created_at")),
        updated_at=ts_to_str(data.get("updated_at")),
        created_by=data.get("created_by"),
    )


# ── CRUD Endpoints ──

@router.post("/create", response_model=PromoCreateResponse)
async def create_promo(
    req: CreatePromoRequest,
    admin: dict = Depends(require_admin),
):
    """Create a new promotion (status: DRAFT)."""
    now = datetime.now(timezone.utc)

    promo_data = {
        "name": req.name,
        "code": req.code,
        "type": req.type,
        "status": "DRAFT",
        "priority": req.priority,
        "conditions": req.conditions.model_dump(),
        "reward": req.reward.model_dump(),
        "display": req.display.model_dump(),
        "stats": {
            "total_redemptions": 0,
            "total_bonus_credits": 0,
            "total_baht_collected": 0,
            "unique_users": 0,
        },
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("user_id", ""),
    }

    _, doc_ref = _promotions_ref().add(promo_data)
    logger.info(f"Promo created: {req.name} ({doc_ref.id}) by {admin.get('email', '')}")

    return PromoCreateResponse(promo_id=doc_ref.id, status="DRAFT")


@router.put("/{promo_id}", response_model=PromoActionResponse)
async def update_promo(
    promo_id: str,
    req: UpdatePromoRequest,
    admin: dict = Depends(require_admin),
):
    """Update an existing promotion. Only DRAFT or PAUSED promos can be edited."""
    doc_ref = _promotions_ref().document(promo_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Promotion not found")

    data = doc.to_dict()
    if data.get("status") not in ("DRAFT", "PAUSED"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit promo with status '{data.get('status')}'. Pause it first.",
        )

    update_fields = {}
    if req.name is not None:
        update_fields["name"] = req.name
    if req.code is not None:
        update_fields["code"] = req.code
    if req.type is not None:
        update_fields["type"] = req.type
    if req.priority is not None:
        update_fields["priority"] = req.priority
    if req.conditions is not None:
        update_fields["conditions"] = req.conditions.model_dump()
    if req.reward is not None:
        update_fields["reward"] = req.reward.model_dump()
    if req.display is not None:
        update_fields["display"] = req.display.model_dump()

    update_fields["updated_at"] = datetime.now(timezone.utc)
    doc_ref.update(update_fields)

    logger.info(f"Promo updated: {promo_id} by {admin.get('email', '')}")
    return PromoActionResponse(
        promo_id=promo_id,
        status=data.get("status", "DRAFT"),
        message="Promotion updated",
    )


@router.get("/list", response_model=PromoListResponse)
async def list_promos(
    status: str = Query(default=None, description="Filter by status: DRAFT, ACTIVE, PAUSED, EXPIRED, CANCELLED"),
    admin: dict = Depends(require_admin),
):
    """List all promotions, optionally filtered by status."""
    query = _promotions_ref()
    if status:
        query = query.where("status", "==", status)

    docs = list(query.stream())
    promos = [_doc_to_promo_response(doc.id, doc.to_dict()) for doc in docs]

    # Sort: ACTIVE first, then DRAFT/PAUSED, then EXPIRED/CANCELLED
    status_order = {"ACTIVE": 0, "DRAFT": 1, "PAUSED": 1, "EXPIRED": 2, "CANCELLED": 3}
    promos.sort(key=lambda p: (status_order.get(p.status, 9), -p.priority))

    return PromoListResponse(promotions=promos, total=len(promos))


@router.get("/{promo_id}", response_model=PromoResponse)
async def get_promo(
    promo_id: str,
    admin: dict = Depends(require_admin),
):
    """Get a single promotion by ID."""
    doc = _promotions_ref().document(promo_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Promotion not found")

    return _doc_to_promo_response(doc.id, doc.to_dict())


# ── Status Actions ──

@router.post("/{promo_id}/activate", response_model=PromoActionResponse)
async def activate_promo(
    promo_id: str,
    admin: dict = Depends(require_admin),
):
    """Activate a DRAFT or PAUSED promotion."""
    doc_ref = _promotions_ref().document(promo_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Promotion not found")

    data = doc.to_dict()
    if data.get("status") not in ("DRAFT", "PAUSED"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate promo with status '{data.get('status')}'",
        )

    doc_ref.update({
        "status": "ACTIVE",
        "updated_at": datetime.now(timezone.utc),
    })

    logger.info(f"Promo activated: {data.get('name', promo_id)} by {admin.get('email', '')}")
    return PromoActionResponse(
        promo_id=promo_id,
        status="ACTIVE",
        message=f"Promotion '{data.get('name', '')}' is now active",
    )


@router.post("/{promo_id}/pause", response_model=PromoActionResponse)
async def pause_promo(
    promo_id: str,
    admin: dict = Depends(require_admin),
):
    """Pause an ACTIVE promotion."""
    doc_ref = _promotions_ref().document(promo_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Promotion not found")

    data = doc.to_dict()
    if data.get("status") != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=f"Can only pause ACTIVE promos. Current: '{data.get('status')}'",
        )

    doc_ref.update({
        "status": "PAUSED",
        "updated_at": datetime.now(timezone.utc),
    })

    logger.info(f"Promo paused: {data.get('name', promo_id)} by {admin.get('email', '')}")
    return PromoActionResponse(
        promo_id=promo_id,
        status="PAUSED",
        message=f"Promotion '{data.get('name', '')}' is now paused",
    )


@router.post("/{promo_id}/cancel", response_model=PromoActionResponse)
async def cancel_promo(
    promo_id: str,
    admin: dict = Depends(require_admin),
):
    """Cancel a promotion (permanent)."""
    doc_ref = _promotions_ref().document(promo_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Promotion not found")

    data = doc.to_dict()
    if data.get("status") in ("CANCELLED",):
        raise HTTPException(status_code=400, detail="Already cancelled")

    doc_ref.update({
        "status": "CANCELLED",
        "updated_at": datetime.now(timezone.utc),
    })

    logger.info(f"Promo cancelled: {data.get('name', promo_id)} by {admin.get('email', '')}")
    return PromoActionResponse(
        promo_id=promo_id,
        status="CANCELLED",
        message=f"Promotion '{data.get('name', '')}' has been cancelled",
    )


@router.post("/{promo_id}/clone", response_model=PromoCreateResponse)
async def clone_promo(
    promo_id: str,
    admin: dict = Depends(require_admin),
):
    """Clone an existing promotion as a new DRAFT."""
    doc = _promotions_ref().document(promo_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Promotion not found")

    data = doc.to_dict()
    now = datetime.now(timezone.utc)

    # Clone with reset stats and new timestamps
    clone_data = {
        "name": f"{data.get('name', '')} (Copy)",
        "code": None,  # Clear promo code
        "type": data.get("type", ""),
        "status": "DRAFT",
        "priority": data.get("priority", 0),
        "conditions": data.get("conditions", {}),
        "reward": data.get("reward", {}),
        "display": data.get("display", {}),
        "stats": {
            "total_redemptions": 0,
            "total_bonus_credits": 0,
            "total_baht_collected": 0,
            "unique_users": 0,
        },
        "created_at": now,
        "updated_at": now,
        "created_by": admin.get("user_id", ""),
    }

    _, new_ref = _promotions_ref().add(clone_data)
    logger.info(f"Promo cloned: {data.get('name', '')} → {new_ref.id} by {admin.get('email', '')}")

    return PromoCreateResponse(promo_id=new_ref.id, status="DRAFT")


# ── Stats & Redemptions ──

@router.get("/{promo_id}/stats", response_model=PromoStatsResponse)
async def get_promo_stats(
    promo_id: str,
    limit: int = Query(default=50, le=200),
    admin: dict = Depends(require_admin),
):
    """Get promotion stats and redemption log."""
    doc = _promotions_ref().document(promo_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Promotion not found")

    data = doc.to_dict()
    stats_data = data.get("stats", {})

    # Fetch redemptions
    redemption_docs = list(
        _promo_redemptions_ref()
        .where("promo_id", "==", promo_id)
        .stream()
    )

    # Sort by created_at descending
    redemption_docs.sort(
        key=lambda d: d.to_dict().get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    redemption_docs = redemption_docs[:limit]

    # Fetch user emails for redemptions
    redemptions = []
    for rdoc in redemption_docs:
        r = rdoc.to_dict()
        user_email = None
        uid = r.get("user_id")
        if uid:
            user_doc = users_ref().document(uid).get()
            if user_doc.exists:
                user_email = user_doc.to_dict().get("email")

        created = r.get("created_at")
        created_str = created.isoformat() if hasattr(created, "isoformat") else str(created) if created else None

        redemptions.append(RedemptionItem(
            redemption_id=rdoc.id,
            user_id=r.get("user_id", ""),
            user_email=user_email,
            topup_baht=r.get("topup_baht", 0),
            base_credits=r.get("base_credits", 0),
            bonus_credits=r.get("bonus_credits", 0),
            total_credits=r.get("total_credits", 0),
            promo_name=r.get("promo_name", ""),
            created_at=created_str,
        ))

    return PromoStatsResponse(
        promo_id=promo_id,
        name=data.get("name", ""),
        stats=PromoStats(
            total_redemptions=stats_data.get("total_redemptions", 0),
            total_bonus_credits=stats_data.get("total_bonus_credits", 0),
            total_baht_collected=stats_data.get("total_baht_collected", 0),
            unique_users=stats_data.get("unique_users", 0),
        ),
        redemptions=redemptions,
    )
