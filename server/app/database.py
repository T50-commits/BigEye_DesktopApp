"""
BigEye Pro — Firestore Database Client
"""
import os
import logging
from google.cloud import firestore
from google.oauth2 import service_account

logger = logging.getLogger("bigeye-api")

_db = None


def get_db() -> firestore.Client:
    """Get Firestore client (singleton)."""
    global _db
    if _db is None:
        # Look for service account next to this file's parent (server/) directory
        server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_sa = os.path.join(server_dir, "firebase-service-account.json")

        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if cred_path and not os.path.isabs(cred_path):
            cred_path = os.path.join(server_dir, os.path.basename(cred_path))

        # Prefer explicit env var, fall back to default location
        resolved = cred_path if (cred_path and os.path.exists(cred_path)) else default_sa

        if os.path.exists(resolved):
            credentials = service_account.Credentials.from_service_account_file(
                resolved,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            _db = firestore.Client(credentials=credentials, project=credentials.project_id)
            logger.info(f"Firestore client initialized with service account: {resolved}")
        else:
            _db = firestore.Client()
            logger.info("Firestore client initialized with default credentials")
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
