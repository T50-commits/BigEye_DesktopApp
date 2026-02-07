"""
BigEye Pro — Backend Configuration
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"

    # JWT
    JWT_SECRET: str = "dev-secret-key-change-in-production-32chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 168  # 7 days

    # AES-256 key (hex, 64 chars = 32 bytes)
    AES_KEY: str = "0000000000000000000000000000000000000000000000000000000000000000"

    # Slip verification
    SLIP_VERIFY_URL: str = ""
    SLIP_API_KEY: str = ""

    # LINE Notify
    LINE_NOTIFY_TOKEN: str = ""

    # Admin
    ADMIN_UIDS: str = ""

    # App
    APP_VERSION: str = "2.0.0"
    EXCHANGE_RATE: int = 4  # 1 THB = 4 credits

    # Credit rates
    ISTOCK_RATE: int = 3
    ADOBE_RATE: int = 2
    SHUTTERSTOCK_RATE: int = 2

    # Concurrency
    MAX_CONCURRENT_IMAGES: int = 5
    MAX_CONCURRENT_VIDEOS: int = 2
    CONTEXT_CACHE_THRESHOLD: int = 20

    # Job expiry
    JOB_EXPIRE_HOURS: int = 2

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def admin_uid_list(self) -> list:
        if not self.ADMIN_UIDS:
            return []
        return [uid.strip() for uid in self.ADMIN_UIDS.split(",") if uid.strip()]


settings = Settings()
