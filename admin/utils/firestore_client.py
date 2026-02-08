"""
BigEye Pro Admin — Firestore Client
Firebase Admin SDK wrapper for the admin dashboard.
"""
import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger("admin")

_db = None
_app = None


def get_db() -> firestore.firestore.Client:
    """Get Firestore client (singleton). Initializes Firebase app if needed."""
    global _db, _app
    if _db is None:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        if not _app:
            if cred_path and os.path.isfile(cred_path):
                cred = credentials.Certificate(cred_path)
                _app = firebase_admin.initialize_app(cred)
            else:
                _app = firebase_admin.initialize_app()
        _db = firestore.client()
        logger.info("Firestore client initialized for admin dashboard")
    return _db


# ── Collection helpers ──

def users_ref():
    return get_db().collection("users")

def jobs_ref():
    return get_db().collection("jobs")

def transactions_ref():
    return get_db().collection("transactions")

def slips_ref():
    return get_db().collection("slips")

def system_config_ref():
    return get_db().collection("system_config")

def audit_logs_ref():
    return get_db().collection("audit_logs")

def daily_reports_ref():
    return get_db().collection("daily_reports")

def promotions_ref():
    return get_db().collection("promotions")

def promo_redemptions_ref():
    return get_db().collection("promo_redemptions")
