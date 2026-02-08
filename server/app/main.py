"""
BigEye Pro — Backend API Server
FastAPI + Firestore — Cloud Run deployment
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, credit, job, system, admin_promo

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bigeye-api")

# FastAPI app
app = FastAPI(
    title="BigEye Pro API",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

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


@app.get("/")
async def root():
    return {"service": "BigEye Pro API", "version": settings.APP_VERSION}


logger.info(f"BigEye Pro API started ({settings.ENVIRONMENT})")
