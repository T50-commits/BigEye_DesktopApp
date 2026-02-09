"""
BigEye Pro — Timezone Utility
Centralised UTC → Thailand (UTC+7) conversion for all admin pages.
"""
from datetime import datetime, timezone, timedelta

TH_TZ = timezone(timedelta(hours=7))


def to_local(dt) -> datetime:
    """Convert a Firestore UTC datetime to Thailand local time (UTC+7)."""
    if dt is None:
        return None
    if not hasattr(dt, "astimezone"):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TH_TZ)


def fmt_datetime(dt, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format a Firestore timestamp as Thailand local time string."""
    local = to_local(dt)
    if local is None:
        return "—"
    try:
        return local.strftime(fmt)
    except Exception:
        return str(dt)


def fmt_date(dt) -> str:
    """Format as date only (YYYY-MM-DD) in Thailand timezone."""
    return fmt_datetime(dt, "%Y-%m-%d")


def fmt_full(dt) -> str:
    """Format as full datetime (YYYY-MM-DD HH:MM:SS) in Thailand timezone."""
    return fmt_datetime(dt, "%Y-%m-%d %H:%M:%S")
