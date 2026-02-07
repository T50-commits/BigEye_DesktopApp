"""
BigEye Pro — Firestore Database Client
"""
import os
import logging
from google.cloud import firestore

logger = logging.getLogger("bigeye-api")

_db = None


def get_db() -> firestore.Client:
    """Get Firestore client (singleton)."""
    global _db
    if _db is None:
        _db = firestore.Client()
        logger.info("Firestore client initialized")
    return _db


# Collection references
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
