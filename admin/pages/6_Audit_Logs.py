"""
BigEye Pro Admin — Audit Logs Page
Filter by severity, view log table, expand for full detail JSON.
"""
import streamlit as st
import json
from datetime import datetime, timedelta
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import audit_logs_ref


st.header("📋 Audit Logs")


# ── Data loading ──

def load_logs(severity_filter: str = "ALL", days: int = 7, limit: int = 200) -> list[dict]:
    """Load audit logs from Firestore."""
    results = []
    cutoff = datetime.utcnow() - timedelta(days=days)

    try:
        ref = audit_logs_ref()

        if severity_filter == "WARNING+":
            # Get WARNING and ERROR
            for sev in ["WARNING", "ERROR", "CRITICAL"]:
                docs = (
                    ref.where(filter=FieldFilter("severity", "==", sev))
                    .where(filter=FieldFilter("timestamp", ">=", cutoff))
                    .order_by("timestamp", direction="DESCENDING")
                    .limit(limit)
                    .stream()
                )
                for doc in docs:
                    d = doc.to_dict()
                    d["id"] = doc.id
                    results.append(d)
            # Sort combined results
            results.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
            results = results[:limit]

        elif severity_filter != "ALL":
            docs = (
                ref.where(filter=FieldFilter("severity", "==", severity_filter))
                .where(filter=FieldFilter("timestamp", ">=", cutoff))
                .order_by("timestamp", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                results.append(d)
        else:
            docs = (
                ref.where(filter=FieldFilter("timestamp", ">=", cutoff))
                .order_by("timestamp", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                results.append(d)

    except Exception as e:
        st.error(f"Error loading logs: {e}")

    return results


def severity_color(sev: str) -> str:
    """Return emoji for severity level."""
    return {
        "INFO": "🔵",
        "WARNING": "🟡",
        "ERROR": "🔴",
        "CRITICAL": "⚫",
    }.get(sev, "⚪")


# ── Filters ──

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    severity_filter = st.selectbox(
        "Severity",
        ["ALL", "WARNING+", "INFO", "WARNING", "ERROR", "CRITICAL"],
        index=1,
    )
with col2:
    days = st.number_input("Last N days", value=7, min_value=1, max_value=90, step=1)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

logs = load_logs(severity_filter, days)

if not logs:
    st.info(f"No logs found (severity: {severity_filter}, last {days} days)")
    st.stop()

st.caption(f"Showing {len(logs)} log(s)")

# ── Log entries ──

for i, log in enumerate(logs):
    ts = log.get("timestamp", "")
    if hasattr(ts, "strftime"):
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    else:
        ts_str = str(ts)

    sev = log.get("severity", "INFO")
    event = log.get("event", log.get("action", "—"))
    user = log.get("user", log.get("email", log.get("uid", "—")))
    emoji = severity_color(sev)

    # Compact log row
    with st.expander(f"{emoji} `{ts_str}` — **{event}** — {user} — {sev}"):
        # Show all fields as formatted JSON
        display = {k: v for k, v in log.items() if k != "id"}
        # Convert datetime objects to strings for JSON display
        for k, v in display.items():
            if hasattr(v, "isoformat"):
                display[k] = v.isoformat()

        st.json(display)
