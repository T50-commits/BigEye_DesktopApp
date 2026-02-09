"""
Server test fixtures — full in-memory Firestore mock + TestClient.

Every Firestore call in the production code goes through app.database.*_ref()
functions which call get_db().collection(name).  We replace get_db() with a
FakeFirestoreClient that stores documents in plain dicts, supporting:
  .collection().document().get/set/update
  .collection().where().limit().stream()
  .collection().add()
  firestore.Increment
  @firestore.transactional
"""
import copy
import uuid
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.security import hash_password, create_jwt_token
from app.config import settings


# ═══════════════════════════════════════════════════════════
# In-memory Firestore mock
# ═══════════════════════════════════════════════════════════

class _Increment:
    """Sentinel that mimics google.cloud.firestore.Increment."""
    def __init__(self, value):
        self.value = value


class FakeDocSnapshot:
    def __init__(self, doc_id: str, data: dict | None, ref=None):
        self.id = doc_id
        self._data = data
        self.exists = data is not None
        self.reference = ref

    def to_dict(self):
        return copy.deepcopy(self._data) if self._data else {}


class FakeDocRef:
    def __init__(self, collection: "FakeCollectionRef", doc_id: str):
        self._col = collection
        self.id = doc_id

    def get(self, transaction=None):
        data = self._col._store.get(self.id)
        return FakeDocSnapshot(self.id, data, ref=self)

    def set(self, data):
        self._col._store[self.id] = copy.deepcopy(data)

    def update(self, fields):
        existing = self._col._store.get(self.id)
        if existing is None:
            existing = {}
            self._col._store[self.id] = existing
        for key, val in fields.items():
            if isinstance(val, _Increment):
                # Support dotted paths like "stats.total_redemptions"
                parts = key.split(".")
                target = existing
                for p in parts[:-1]:
                    target = target.setdefault(p, {})
                target[parts[-1]] = target.get(parts[-1], 0) + val.value
            else:
                # Support dotted paths for non-Increment too
                parts = key.split(".")
                if len(parts) == 1:
                    existing[key] = val
                else:
                    target = existing
                    for p in parts[:-1]:
                        target = target.setdefault(p, {})
                    target[parts[-1]] = val


class FakeQuery:
    """Chainable query that filters the parent collection's _store."""
    def __init__(self, col: "FakeCollectionRef", filters: list | None = None):
        self._col = col
        self._filters = filters or []
        self._limit = None

    def where(self, *args, **kwargs):
        """Accept both old-style (field, op, val) and new-style (filter=FieldFilter(...))."""
        new_q = FakeQuery(self._col, list(self._filters))
        new_q._limit = self._limit
        if "filter" in kwargs:
            ff = kwargs["filter"]
            new_q._filters.append((ff.field_path, ff.op_string, ff.value))
        elif len(args) == 3:
            new_q._filters.append((args[0], args[1], args[2]))
        return new_q

    def limit(self, n):
        new_q = FakeQuery(self._col, list(self._filters))
        new_q._limit = n
        return new_q

    def stream(self):
        results = []
        for doc_id, data in list(self._col._store.items()):
            if self._match(data):
                results.append(FakeDocSnapshot(doc_id, data, ref=FakeDocRef(self._col, doc_id)))
        if self._limit is not None:
            results = results[:self._limit]
        return iter(results)

    def _match(self, data):
        for field, op, val in self._filters:
            doc_val = data.get(field)
            if op == "==":
                if doc_val != val:
                    return False
            elif op == "<":
                if doc_val is None or doc_val >= val:
                    return False
            elif op == ">=":
                if doc_val is None or doc_val < val:
                    return False
        return True


class FakeCollectionRef:
    def __init__(self, store: dict):
        self._store = store  # {doc_id: dict}

    def document(self, doc_id: str):
        return FakeDocRef(self, doc_id)

    def add(self, data):
        doc_id = f"auto-{uuid.uuid4().hex[:12]}"
        self._store[doc_id] = copy.deepcopy(data)
        ref = FakeDocRef(self, doc_id)
        return None, ref

    def where(self, *args, **kwargs):
        q = FakeQuery(self)
        return q.where(*args, **kwargs)

    def limit(self, n):
        q = FakeQuery(self)
        return q.limit(n)

    def stream(self):
        return FakeQuery(self).stream()


class FakeFieldFilter:
    """Mimics google.cloud.firestore_v1.FieldFilter."""
    def __init__(self, field_path, op_string, value):
        self.field_path = field_path
        self.op_string = op_string
        self.value = value


class FakeFirestoreClient:
    """Top-level Firestore client replacement."""
    def __init__(self):
        self._collections: dict[str, dict] = {}

    def collection(self, name: str) -> FakeCollectionRef:
        if name not in self._collections:
            self._collections[name] = {}
        return FakeCollectionRef(self._collections[name])

    def transaction(self):
        return FakeTransaction()


class FakeTransaction:
    """Minimal transaction that supports get() and update() on doc refs."""
    def __init__(self):
        pass

    def update(self, ref, fields):
        """Delegate to the doc ref's update method."""
        ref.update(fields)

    def get(self, ref):
        """Delegate to the doc ref's get method."""
        return ref.get()


def _fake_transactional(fn):
    """Replacement for @firestore.transactional — just calls fn(transaction)."""
    def wrapper(transaction):
        return fn(transaction)
    return wrapper


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def fake_db():
    """Create a fresh FakeFirestoreClient for each test."""
    return FakeFirestoreClient()


@pytest.fixture
def patched_app(fake_db):
    """
    Patch all Firestore access points so the FastAPI app uses our in-memory DB.
    Returns the FastAPI app ready for TestClient.
    """
    import app.database as db_mod
    import app.routers.job as job_mod
    import app.routers.credit as credit_mod
    import app.routers.system as system_mod
    import app.services.promo_engine as promo_mod
    import app.routers.admin_promo as admin_promo_mod
    import google.cloud.firestore_v1 as firestore_v1_mod

    patches = [
        # Core: replace get_db singleton
        patch.object(db_mod, "get_db", return_value=fake_db),
        patch.object(db_mod, "_db", fake_db),
        # Replace FieldFilter in auth router
        patch.object(firestore_v1_mod, "FieldFilter", FakeFieldFilter),
        # Replace firestore.Client() calls in job router (line 96)
        patch("google.cloud.firestore.Client", return_value=fake_db),
        # Replace firestore.Increment with our sentinel
        patch("google.cloud.firestore.Increment", _Increment),
        # Replace @firestore.transactional decorator in job router
        patch("google.cloud.firestore.transactional", _fake_transactional),
        # Promo engine also uses get_db()
        patch.object(promo_mod, "get_db", return_value=fake_db),
    ]

    for p in patches:
        p.start()

    from app.main import app as fastapi_app
    yield fastapi_app

    for p in patches:
        p.stop()


@pytest.fixture
def client(patched_app):
    """TestClient bound to the patched FastAPI app."""
    from starlette.testclient import TestClient
    return TestClient(patched_app)


@pytest.fixture
def seed_user(fake_db):
    """
    Seed a standard active user into the fake DB.
    Returns (user_id, jwt_token, user_data_dict).
    """
    user_id = "user-test-001"
    email = "test@example.com"
    pw_hash = hash_password("Password123")
    user_data = {
        "email": email,
        "password_hash": pw_hash,
        "full_name": "Test User",
        "phone": "",
        "hardware_id": "abcdef1234567890abcdef1234567890",
        "tier": "standard",
        "credits": 500,
        "status": "active",
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "total_topup_baht": 0,
        "total_credits_used": 0,
        "app_version": "2.0.0",
        "metadata": {"os": "macOS", "registration_ip": "", "notes": ""},
    }
    fake_db.collection("users")._store[user_id] = copy.deepcopy(user_data)
    token = create_jwt_token(user_id, email)
    return user_id, token, user_data


@pytest.fixture
def auth_header(seed_user):
    """Authorization header for the seeded user."""
    _, token, _ = seed_user
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_admin(fake_db):
    """
    Seed an admin user. Also patches settings.ADMIN_UIDS.
    Returns (user_id, jwt_token).
    """
    user_id = "admin-001"
    email = "admin@example.com"
    user_data = {
        "email": email,
        "password_hash": hash_password("AdminPass123"),
        "full_name": "Admin User",
        "phone": "",
        "hardware_id": "admin_hw_id_1234567890123456",
        "tier": "admin",
        "credits": 99999,
        "status": "active",
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "last_login": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "last_active": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "total_topup_baht": 0,
        "total_credits_used": 0,
        "app_version": "2.0.0",
        "metadata": {},
    }
    fake_db.collection("users")._store[user_id] = copy.deepcopy(user_data)
    token = create_jwt_token(user_id, email)
    return user_id, token


@pytest.fixture
def admin_header(seed_admin):
    """Authorization header for the admin user (also patches ADMIN_UIDS)."""
    uid, token = seed_admin
    with patch.object(settings, "ADMIN_UIDS", uid):
        yield {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_app_settings(fake_db):
    """Seed system_config/app_settings with prompts, blacklist, rates."""
    cfg = {
        "exchange_rate": 4,
        "maintenance_mode": False,
        "app_latest_version": "2.1.0",
        "force_update_below": "1.5.0",
        "app_download_url": "https://example.com/download",
        "app_update_notes": "Bug fixes and improvements",
        "credit_rates": {
            "istock_photo": 3,
            "istock_video": 3,
            "adobe_photo": 2,
            "adobe_video": 2,
            "shutterstock_photo": 2,
            "shutterstock_video": 2,
        },
        "prompts": {
            "istock": "You are a stock photo metadata expert for iStock...",
            "hybrid": "You are a stock photo metadata expert (hybrid)...",
            "single": "You are a stock photo metadata expert (single words)...",
        },
        "dictionary": "landscape,portrait,nature,urban",
        "blacklist": ["nike", "coca cola", "disney"],
        "context_cache_threshold": 25,
    }
    fake_db.collection("system_config")._store["app_settings"] = cfg
    return cfg
