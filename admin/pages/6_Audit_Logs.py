"""
BigEye Pro Admin — หน้าบันทึกระบบ (Audit Logs)
กรองตามระดับ, ดูรายละเอียด JSON
"""
import streamlit as st
import json
from datetime import datetime, timedelta, timezone
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import audit_logs_ref, users_ref


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
            ts = r.get("timestamp") or r.get("created_at")
            if ts:
                if hasattr(ts, "tzinfo") and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    filtered.append(r)
            else:
                filtered.append(r)
        results = filtered

        # Sort by timestamp/created_at descending
        def _get_ts(x):
            return x.get("timestamp") or x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
        results.sort(key=_get_ts, reverse=True)
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


_EVENT_LABELS = {
    "USER_REGISTER": "สมัครสมาชิกใหม่",
    "LOGIN_FAILED_WRONG_PASSWORD": "ล็อกอินผิดรหัส",
    "LOGIN_FAILED_DEVICE_MISMATCH": "อุปกรณ์ไม่ตรง",
    "JOB_RESERVED": "จองงาน",
    "JOB_COMPLETED": "งานเสร็จ",
    "JOB_EXPIRED_AUTO_REFUND": "งานหมดอายุ-คืนเครดิต",
    "TOPUP_SUCCESS": "เติมเงินสำเร็จ",
}


_email_cache: dict[str, str] = {}

def _resolve_email(user_id: str) -> str:
    if not user_id:
        return "—"
    if user_id in _email_cache:
        return _email_cache[user_id]
    try:
        doc = users_ref().document(user_id).get()
        if doc.exists:
            email = doc.to_dict().get("email", user_id[:12])
            _email_cache[user_id] = email
            return email
    except Exception:
        pass
    _email_cache[user_id] = user_id[:12]
    return user_id[:12]


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
    ts = log.get("timestamp") or log.get("created_at", "")
    if hasattr(ts, "strftime"):
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    else:
        ts_str = str(ts)

    sev = log.get("severity", "INFO")
    event_type = log.get("event_type", log.get("event", log.get("action", "—")))
    event_label = _EVENT_LABELS.get(event_type, event_type)
    user_id = log.get("user_id", log.get("uid", ""))
    user_email = _resolve_email(user_id) if user_id else "—"
    emoji = severity_color(sev)

    details = log.get("details", {})
    detail_str = ""
    if isinstance(details, dict):
        # Show key info inline
        if "email" in details:
            detail_str = f" | {details['email']}"
        elif "job_token" in details:
            detail_str = f" | job: {details['job_token'][:8]}..."

    with st.expander(f"{emoji} `{ts_str}` — **{event_label}** — {user_email} — {sev}{detail_str}"):
        # Show structured info instead of raw JSON
        st.markdown(f"**เหตุการณ์:** {event_type}")
        st.markdown(f"**ผู้ใช้:** {user_email}")
        if isinstance(details, dict) and details:
            st.markdown("**รายละเอียด:**")
            detail_display = {}
            for k, v in details.items():
                if hasattr(v, "isoformat"):
                    detail_display[k] = v.isoformat()
                else:
                    detail_display[k] = v
            st.json(detail_display)
