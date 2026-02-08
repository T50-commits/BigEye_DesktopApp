"""
BigEye Pro Admin — หน้าแดชบอร์ด
สถิติวันนี้, กราฟรายได้, การเติบโตผู้ใช้, รายการรอดำเนินการ
"""
import streamlit as st
from datetime import datetime, timedelta, timezone

from utils.firestore_client import (
    users_ref, jobs_ref, slips_ref, transactions_ref, daily_reports_ref,
)
from utils.charts import revenue_chart, user_growth_chart
from utils.theme import inject_css

inject_css()
st.header("📊 แดชบอร์ด")

# ── Helper: query Firestore with caching ──

@st.cache_data(ttl=60)
def load_today_stats():
    """Load today's key metrics from Firestore."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Active users (logged in within 24h)
    active_users = 0
    try:
        docs = users_ref().where("last_login", ">=", yesterday_start).stream()
        active_users = sum(1 for _ in docs)
    except Exception:
        pass

    # New users today
    new_users = 0
    try:
        docs = users_ref().where("created_at", ">=", today_start).stream()
        new_users = sum(1 for _ in docs)
    except Exception:
        pass

    # Revenue today (from transactions with type TOPUP)
    revenue = 0
    try:
        docs = list(
            transactions_ref()
            .where("type", "==", "TOPUP")
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                revenue += d.get("amount_thb", d.get("amount", 0))
    except Exception:
        pass

    # Jobs today
    jobs_count = 0
    try:
        docs = jobs_ref().where("created_at", ">=", today_start).stream()
        jobs_count = sum(1 for _ in docs)
    except Exception:
        pass

    # Errors today (failed jobs)
    errors = 0
    try:
        docs = (
            jobs_ref()
            .where("status", "==", "FAILED")
            .where("created_at", ">=", today_start)
            .stream()
        )
        errors = sum(1 for _ in docs)
    except Exception:
        pass

    return {
        "active_users": active_users,
        "new_users": new_users,
        "revenue": revenue,
        "jobs": jobs_count,
        "errors": errors,
    }


@st.cache_data(ttl=300)
def load_daily_reports(days: int = 30):
    """Load daily reports for charts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    revenue_data = []
    user_data = []

    try:
        docs = (
            daily_reports_ref()
            .where("date", ">=", cutoff.strftime("%Y-%m-%d"))
            .order_by("date")
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
            date_str = d.get("date", "")
            revenue_data.append({"date": date_str, "revenue": d.get("revenue", 0)})
            user_data.append({"date": date_str, "new_users": d.get("new_users", 0)})
    except Exception:
        pass

    return revenue_data, user_data


@st.cache_data(ttl=60)
def load_pending_actions():
    """Load pending slips and stuck jobs."""
    pending_slips = 0
    stuck_jobs = 0

    try:
        docs = slips_ref().where("status", "==", "PENDING").stream()
        pending_slips = sum(1 for _ in docs)
    except Exception:
        pass

    expire_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    try:
        docs = (
            jobs_ref()
            .where("status", "==", "RESERVED")
            .where("created_at", "<=", expire_cutoff)
            .stream()
        )
        stuck_jobs = sum(1 for _ in docs)
    except Exception:
        pass

    return pending_slips, stuck_jobs


# ── Render ──

_top_left, _top_right = st.columns([3, 1])
with _top_right:
    if st.button("🔄 รีเฟรช", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

stats = load_today_stats()
pending_slips, stuck_jobs = load_pending_actions()

# ── Custom metric card HTML ──

def _metric_card(icon: str, label: str, value: str, color: str, sub: str = "") -> str:
    sub_html = f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:2px">{sub}</div>' if sub else ""
    return f"""
    <div style="
        background:linear-gradient(135deg,#ffffff 0%,#f8fafc 100%);
        border:1px solid #e2e8f0;
        border-left:4px solid {color};
        border-radius:12px;
        padding:20px 18px;
        height:100%;
    ">
        <div style="font-size:0.8rem;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">
            {icon} {label}
        </div>
        <div style="font-size:2rem;font-weight:800;color:#0f172a;line-height:1.1">
            {value}
        </div>
        {sub_html}
    </div>
    """

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(_metric_card("👥", "ผู้ใช้งาน", str(stats["active_users"]), "#3b82f6", "ล็อกอินใน 24 ชม."), unsafe_allow_html=True)
with c2:
    st.markdown(_metric_card("🆕", "สมัครใหม่", str(stats["new_users"]), "#8b5cf6", "วันนี้"), unsafe_allow_html=True)
with c3:
    st.markdown(_metric_card("💰", "รายได้", f"฿{stats['revenue']:,}", "#10b981", "วันนี้"), unsafe_allow_html=True)
with c4:
    st.markdown(_metric_card("⚙️", "งานทั้งหมด", str(stats["jobs"]), "#f59e0b", "วันนี้"), unsafe_allow_html=True)
with c5:
    err_color = "#ef4444" if stats["errors"] > 0 else "#22c55e"
    st.markdown(_metric_card("❌", "งานผิดพลาด", str(stats["errors"]), err_color, "วันนี้"), unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Alerts ──
if pending_slips > 0 or stuck_jobs > 0:
    alert_cols = st.columns(2)
    with alert_cols[0]:
        if pending_slips > 0:
            st.markdown(f"""
            <div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:10px">
                <span style="font-size:1.5rem">🧾</span>
                <div>
                    <div style="font-weight:700;color:#92400e">{pending_slips} สลิปรอตรวจสอบ</div>
                    <div style="font-size:0.8rem;color:#a16207">ไปที่หน้า "สลิปเติมเงิน" เพื่อดำเนินการ</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    with alert_cols[1]:
        if stuck_jobs > 0:
            st.markdown(f"""
            <div style="background:#fee2e2;border:1px solid #f87171;border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:10px">
                <span style="font-size:1.5rem">⚠️</span>
                <div>
                    <div style="font-weight:700;color:#991b1b">{stuck_jobs} งานค้าง (RESERVED)</div>
                    <div style="font-size:0.8rem;color:#b91c1c">งานหมดอายุ — ไปที่หน้า "ตรวจสอบงาน" เพื่อคืนเครดิต</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:10px">
        <span style="font-size:1.5rem">✅</span>
        <div style="font-weight:600;color:#166534">ไม่มีรายการรอดำเนินการ — ระบบทำงานปกติ</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Charts ──
revenue_data, user_data = load_daily_reports()

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 18px 8px 18px;margin-bottom:8px">
        <div style="font-weight:700;font-size:1rem;color:#1e293b;margin-bottom:4px">💰 รายได้ (30 วันล่าสุด)</div>
    </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(revenue_chart(revenue_data), use_container_width=True)

with col_right:
    st.markdown("""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 18px 8px 18px;margin-bottom:8px">
        <div style="font-weight:700;font-size:1rem;color:#1e293b;margin-bottom:4px">👥 ผู้ใช้ใหม่ (30 วันล่าสุด)</div>
    </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(user_growth_chart(user_data), use_container_width=True)
