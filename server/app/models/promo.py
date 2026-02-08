"""
BigEye Pro — Promotion Pydantic Models
Request/Response schemas for promotion endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Promotion Sub-Models ──

class PromoTier(BaseModel):
    min_baht: float
    max_baht: Optional[float] = None
    credits: int


class PromoConditions(BaseModel):
    start_date: datetime
    end_date: Optional[datetime] = None
    min_topup_baht: Optional[float] = None
    max_topup_baht: Optional[float] = None
    max_redemptions: Optional[int] = None
    max_per_user: Optional[int] = None
    eligible_tiers: Optional[list[str]] = None
    new_users_only: bool = False
    first_topup_only: bool = False
    require_code: bool = False


class PromoReward(BaseModel):
    type: str  # "BONUS_CREDITS" | "RATE_OVERRIDE" | "PERCENTAGE_BONUS" | "TIERED_BONUS"
    bonus_credits: Optional[int] = None
    override_rate: Optional[float] = None
    bonus_percentage: Optional[float] = None
    tiers: Optional[list[PromoTier]] = None


class PromoDisplay(BaseModel):
    banner_text: str = ""
    banner_color: str = "#FF4560"
    show_in_client: bool = True
    show_in_topup: bool = True


class PromoStats(BaseModel):
    total_redemptions: int = 0
    total_bonus_credits: int = 0
    total_baht_collected: float = 0
    unique_users: int = 0


# ── Admin Request Models ──

class CreatePromoRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: Optional[str] = None
    type: str  # "RATE_BOOST" | "TIERED_BONUS" | "FLAT_BONUS" | "WELCOME_BONUS" | "FIRST_TOPUP" | "USAGE_REWARD"
    priority: int = 0
    conditions: PromoConditions
    reward: PromoReward
    display: PromoDisplay = PromoDisplay()


class UpdatePromoRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[int] = None
    conditions: Optional[PromoConditions] = None
    reward: Optional[PromoReward] = None
    display: Optional[PromoDisplay] = None


# ── Admin Response Models ──

class PromoResponse(BaseModel):
    promo_id: str
    name: str
    code: Optional[str] = None
    type: str
    status: str
    priority: int = 0
    conditions: PromoConditions
    reward: PromoReward
    display: PromoDisplay
    stats: PromoStats = PromoStats()
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None


class PromoListResponse(BaseModel):
    promotions: list[PromoResponse]
    total: int


class PromoCreateResponse(BaseModel):
    promo_id: str
    status: str


class PromoActionResponse(BaseModel):
    promo_id: str
    status: str
    message: str


# ── Redemption Models ──

class RedemptionItem(BaseModel):
    redemption_id: str
    user_id: str
    user_email: Optional[str] = None
    topup_baht: float
    base_credits: int
    bonus_credits: int
    total_credits: int
    promo_name: str
    created_at: Optional[str] = None


class PromoStatsResponse(BaseModel):
    promo_id: str
    name: str
    stats: PromoStats
    redemptions: list[RedemptionItem] = []


# ── Client-Facing Models ──

class ActivePromoInfo(BaseModel):
    """Promo info sent to client in balance response."""
    promo_id: str
    name: str
    banner_text: str
    banner_color: str
    type: str
    tiers: Optional[list[PromoTier]] = None
    override_rate: Optional[float] = None
    bonus_credits: Optional[int] = None
    bonus_percentage: Optional[float] = None
    ends_at: Optional[str] = None


class BalanceWithPromosResponse(BaseModel):
    credits: int
    exchange_rate: int = 4
    active_promos: list[ActivePromoInfo] = []


class TopUpWithPromoRequest(BaseModel):
    slip: str  # base64 encoded slip image
    amount: int = Field(gt=0)
    promo_code: Optional[str] = None


class TopUpWithPromoResponse(BaseModel):
    status: str
    base_credits: int = 0
    bonus_credits: int = 0
    total_credits: int = 0
    new_balance: int = 0
    promo_applied: Optional[str] = None
    message: str = ""
