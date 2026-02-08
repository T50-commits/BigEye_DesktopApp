"""
BigEye Pro Admin — Dashboard Page
Today's stats, revenue chart, user growth, pending actions.
"""
import streamlit as st
from datetime import datetime, timedelta

from utils.firestore_client import (
    users_ref, jobs_ref, slips_ref, transactions_ref, daily_reports_ref,
)
from utils.charts import revenue_chart, user_growth_chart

st.header("📊 Dashboard")

# ── Helper: query Firestore with caching ──

@st.cache_data(ttl=60)
def load_today_stats():
    """Load today's key metrics from Firestore."""
    now = datetime.utcnow()
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

    # Revenue today (from transactions with type topup)
    revenue = 0
    try:
        docs = (
            transactions_ref()
            .where("type", "==", "topup")
            .where("created_at", ">=", today_start)
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
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
    cutoff = datetime.utcnow() - timedelta(days=days)
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

    expire_cutoff = datetime.utcnow() - timedelta(hours=2)
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

if st.button("🔄 Refresh"):
    st.cache_data.clear()

stats = load_today_stats()

# Stats cards
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("👥 Active Users", stats["active_users"])
c2.metric("🆕 New Users", stats["new_users"])
c3.metric("💰 Revenue", f"฿{stats['revenue']:,}")
c4.metric("⚙️ Jobs", stats["jobs"])
c5.metric("❌ Errors", stats["errors"])

st.divider()

# Charts
revenue_data, user_data = load_daily_reports()

col_left, col_right = st.columns(2)
with col_left:
    st.subheader("Revenue (Last 30 Days)")
    st.plotly_chart(revenue_chart(revenue_data), use_container_width=True)

with col_right:
    st.subheader("User Growth (Last 30 Days)")
    st.plotly_chart(user_growth_chart(user_data), use_container_width=True)

st.divider()

# Pending actions
st.subheader("⚠️ Pending Actions")
pending_slips, stuck_jobs = load_pending_actions()

if pending_slips == 0 and stuck_jobs == 0:
    st.success("✅ No pending actions")
else:
    if pending_slips > 0:
        st.warning(f"🧾 **{pending_slips}** slip(s) awaiting manual review")
    if stuck_jobs > 0:
        st.error(f"⚙️ **{stuck_jobs}** job(s) stuck in RESERVED (expired)")
