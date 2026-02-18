"""
BigEye Pro — Backend API Server
FastAPI + Firestore — Cloud Run deployment
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.rate_limit import limiter
from app.routers import auth, credit, job, system, admin_promo, admin

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bigeye-api")

# ── Production safety checks ──
if settings.ENVIRONMENT == "production":
    if "dev-secret" in settings.JWT_SECRET:
        raise RuntimeError(
            "CRITICAL: JWT_SECRET is still the default dev value! "
            "Set a strong JWT_SECRET in environment variables before deploying."
        )
    if settings.AES_KEY == "0" * 64:
        raise RuntimeError(
            "CRITICAL: AES_KEY is still the default all-zeros value! "
            "Set a strong AES_KEY (64 hex chars) in environment variables before deploying."
        )

_is_dev = settings.ENVIRONMENT == "development"

# FastAPI app
app = FastAPI(
    title="BigEye Pro API",
    version=settings.APP_VERSION,
    docs_url="/docs" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
    redoc_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow desktop client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api/v1
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(credit.router, prefix=PREFIX)
app.include_router(job.router, prefix=PREFIX)
app.include_router(system.router, prefix=PREFIX)
app.include_router(admin_promo.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)


@app.get("/")
async def root():
    return {"service": "BigEye Pro API", "version": settings.APP_VERSION}


logger.info(f"BigEye Pro API started ({settings.ENVIRONMENT})")
