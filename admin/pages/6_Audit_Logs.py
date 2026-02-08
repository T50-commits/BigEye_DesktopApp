"""
BigEye Pro Admin — หน้าบันทึกระบบ (Audit Logs)
กรองตามระดับ, ดูรายละเอียด JSON
"""
import streamlit as st
import json
from datetime import datetime, timedelta, timezone
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import audit_logs_ref


st.header("📋 บันทึกระบบ")


# ── Data loading ──

def load_logs(severity_filter: str = "ALL", days: int = 7, limit: int = 200) -> list[dict]:
    results = []
    try:
        ref = audit_logs_ref()

        if severity_filter == "WARNING+":
            for sev in ["WARNING", "ERROR", "CRITICAL"]:
                docs = list(
                    ref.where(filter=FieldFilter("severity", "==", sev))
                    .limit(limit)
                    .stream()
                )
                for doc in docs:
                    d = doc.to_dict()
                    d["id"] = doc.id
                    results.append(d)
        elif severity_filter != "ALL":
            docs = list(
                ref.where(filter=FieldFilter("severity", "==", severity_filter))
                .limit(limit)
                .stream()
            )
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                results.append(d)
        else:
            docs = list(ref.limit(limit).stream())
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                results.append(d)

        # Filter by date cutoff in Python (avoid composite index)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = []
        for r in results:
            ts = r.get("timestamp")
            if ts:
                if hasattr(ts, "tzinfo") and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    filtered.append(r)
            else:
                filtered.append(r)
        results = filtered

        # Sort by timestamp descending
        results.sort(
            key=lambda x: x.get("timestamp") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        results = results[:limit]

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดบันทึก: {e}")

    return results


def severity_color(sev: str) -> str:
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
        "ระดับความรุนแรง",
        ["ALL", "WARNING+", "INFO", "WARNING", "ERROR", "CRITICAL"],
        index=1,
    )
with col2:
    days = st.number_input("ย้อนหลัง (วัน)", value=7, min_value=1, max_value=90, step=1)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 รีเฟรช"):
        st.cache_data.clear()
        st.rerun()

logs = load_logs(severity_filter, days)

if not logs:
    st.info(f"ไม่พบบันทึก (ระดับ: {severity_filter}, ย้อนหลัง {days} วัน)")
    st.stop()

st.caption(f"แสดง {len(logs)} รายการ")

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

    with st.expander(f"{emoji} `{ts_str}` — **{event}** — {user} — {sev}"):
        display = {k: v for k, v in log.items() if k != "id"}
        for k, v in display.items():
            if hasattr(v, "isoformat"):
                display[k] = v.isoformat()
        st.json(display)
