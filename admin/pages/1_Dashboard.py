"""
BigEye Pro Admin — หน้าแดชบอร์ด
สถิติวันนี้, กราฟรายได้, การเติบโตผู้ใช้, รายการรอดำเนินการ
"""
import streamlit as st
from datetime import datetime, timedelta, timezone

from utils.firestore_client import (
    users_ref, jobs_ref, slips_ref, transactions_ref, daily_reports_ref,
    system_config_ref,
)
from utils.charts import revenue_chart, user_growth_chart
from utils.theme import inject_css
from utils.components import metric_card, alert_card, chart_card

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

    # ── รายรับ (Top-up THB) — เงินจริงที่ลูกค้าเติมเข้ามาวันนี้ ──
    topup_thb = 0
    try:
        docs = list(slips_ref().where("status", "==", "VERIFIED").stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                topup_thb += d.get("amount_detected", 0)
    except Exception:
        pass

    # ── รายได้รับรู้ (Used credits → THB) — เครดิตที่ลูกค้าใช้จริงแปลงกลับเป็นบาท ──
    # actual_usage = เครดิตที่ใช้จริง, credit_rate = อัตราเครดิต/ไฟล์
    # เราแปลงกลับเป็นบาทด้วย exchange_rate (1 บาท = N เครดิต)
    recognized_thb = 0.0
    exchange_rate = 4
    try:
        cfg = system_config_ref().document("app_settings").get()
        if cfg.exists:
            exchange_rate = cfg.to_dict().get("exchange_rate", 4)
    except Exception:
        pass

    try:
        docs = list(jobs_ref().where("status", "==", "COMPLETED").stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                usage = d.get("actual_usage", 0)
                if usage > 0 and exchange_rate > 0:
                    recognized_thb += usage / exchange_rate
    except Exception:
        pass

    # Jobs today
    jobs_count = 0
    try:
        docs = list(jobs_ref().stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                jobs_count += 1
    except Exception:
        pass

    # Errors today (failed jobs)
    errors = 0
    try:
        docs = list(jobs_ref().where("status", "==", "FAILED").stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                errors += 1
    except Exception:
        pass

    return {
        "active_users": active_users,
        "new_users": new_users,
        "topup_thb": topup_thb,
        "recognized_thb": round(recognized_thb, 2),
        "exchange_rate": exchange_rate,
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

# Row 1: Metric Cards (4 columns)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(metric_card("👥", "ผู้ใช้งาน", f"{stats['active_users']:,}", "#3b82f6", "ล็อกอินใน 24 ชม."), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("🆕", "สมัครใหม่", str(stats["new_users"]), "#8b5cf6", "วันนี้"), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("💰", "รายรับ", f"฿{stats['topup_thb']:,}", "#10b981", "เงินจริงที่ลูกค้าเติมวันนี้"), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card("📊", "รายได้รับรู้", f"฿{stats['recognized_thb']:,.2f}", "#06b6d4", f"เครดิตที่ใช้ ÷ {stats['exchange_rate']} = บาท"), unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# Row 2: Jobs (3 columns)
c5, c6, c7 = st.columns(3)
with c5:
    st.markdown(metric_card("⚙️", "งานทั้งหมด", str(stats["jobs"]), "#f59e0b", "วันนี้"), unsafe_allow_html=True)
with c6:
    err_color = "#ef4444" if stats["errors"] > 0 else "#10b981"
    st.markdown(metric_card("❌", "งานผิดพลาด", str(stats["errors"]), err_color, "วันนี้"), unsafe_allow_html=True)
with c7:
    total = stats["jobs"]
    success_rate = round(((total - stats["errors"]) / total * 100), 1) if total > 0 else 100
    rate_color = "#10b981" if success_rate >= 95 else "#f59e0b" if success_rate >= 80 else "#ef4444"
    st.markdown(metric_card("✅", "อัตราสำเร็จ", f"{success_rate}%", rate_color, f"{total - stats['errors']}/{total} งาน"), unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ── Alerts ──
if pending_slips > 0 or stuck_jobs > 0:
    alert_cols = st.columns(2)
    with alert_cols[0]:
        if pending_slips > 0:
            st.markdown(alert_card(
                "🧾", f"{pending_slips} สลิปรอตรวจสอบ",
                "ไปที่หน้า \"สลิปเติมเงิน\" เพื่อดำเนินการ",
                style="warning", action_label="ตรวจสอบ →",
            ), unsafe_allow_html=True)
        else:
            st.markdown(alert_card(
                "✅", "ไม่มีสลิปรอตรวจสอบ", "สลิปทั้งหมดได้รับการดำเนินการแล้ว",
                style="success",
            ), unsafe_allow_html=True)
    with alert_cols[1]:
        if stuck_jobs > 0:
            st.markdown(alert_card(
                "⚠️", f"{stuck_jobs} งานค้าง (RESERVED > 2 ชม.)",
                "ไปที่หน้า \"ตรวจสอบงาน\" เพื่อคืนเครดิต",
                style="danger", action_label="จัดการ →",
            ), unsafe_allow_html=True)
        else:
            st.markdown(alert_card(
                "✅", "ไม่มีงานค้าง", "งานทั้งหมดทำงานปกติ",
                style="success",
            ), unsafe_allow_html=True)
else:
    st.markdown(alert_card(
        "✅", "ระบบทำงานปกติ",
        "ไม่มีรายการรอดำเนินการ",
        style="success",
    ), unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ── Charts ──
revenue_data, user_data = load_daily_reports()

col_left, col_right = st.columns(2)
with col_left:
    st.markdown(chart_card("💰 รายได้ (30 วันล่าสุด)"), unsafe_allow_html=True)
    st.plotly_chart(revenue_chart(revenue_data), use_container_width=True)

with col_right:
    st.markdown(chart_card("👥 ผู้ใช้ใหม่ (30 วันล่าสุด)"), unsafe_allow_html=True)
    st.plotly_chart(user_growth_chart(user_data), use_container_width=True)
