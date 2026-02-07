"""
BigEye Pro — Pydantic Models
Request/Response schemas for all API endpoints.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ── Auth ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    phone: str = ""
    hardware_id: str = Field(min_length=8, max_length=64)
    os_type: str = ""  # "Windows" | "macOS" | "Linux"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    hardware_id: str = Field(min_length=8, max_length=64)
    app_version: str = ""


class AuthResponse(BaseModel):
    token: str
    user_id: str
    email: str
    full_name: str
    credits: int


# ── Credit ──

class BalanceResponse(BaseModel):
    credits: int


class TopUpRequest(BaseModel):
    slip: str  # base64 encoded slip image
    amount: int = Field(gt=0)


class TopUpResponse(BaseModel):
    status: str
    credits_added: int = 0
    new_balance: int = 0
    message: str = ""


class TransactionItem(BaseModel):
    date: str
    description: str
    amount: int
    type: str


class HistoryResponse(BaseModel):
    transactions: list[TransactionItem]
    balance: int


# ── Job ──

class ReserveJobRequest(BaseModel):
    file_count: int = Field(gt=0)
    mode: str  # "iStock" | "Adobe" | "Shutterstock"
    keyword_style: str = ""  # "Hybrid" | "Single Words"
    model: str = "gemini-2.5-pro"
    version: str = ""


class ReserveJobResponse(BaseModel):
    job_token: str
    config: str = ""  # AES encrypted prompt
    dictionary: str = ""  # keyword dictionary (iStock mode only)
    blacklist: list[str] = []
    concurrency: dict = {}


class FinalizeJobRequest(BaseModel):
    job_token: str
    success: int = 0
    failed: int = 0
    photos: int = 0
    videos: int = 0


class FinalizeJobResponse(BaseModel):
    refunded: int = 0
    balance: int = 0


# ── System ──

class CheckUpdateRequest(BaseModel):
    version: str
    hardware_id: str = ""


class CheckUpdateResponse(BaseModel):
    update_available: bool = False
    version: str = ""
    download_url: str = ""
    force: bool = False
    notes: str = ""
    maintenance: bool = False
    maintenance_message: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = ""
    environment: str = ""
