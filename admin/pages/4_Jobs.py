"""
BigEye Pro Admin — Jobs Monitor Page
Filter, view job details, force refund stuck jobs.
"""
import streamlit as st
from datetime import datetime, timedelta
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import jobs_ref, users_ref, transactions_ref


st.header("⚙️ Jobs Monitor")


# ── Data loading ──

def load_jobs(status_filter: str = "ALL", limit: int = 100) -> list[dict]:
    """Load jobs from Firestore with optional status filter."""
    results = []
    try:
        ref = jobs_ref()
        if status_filter != "ALL":
            query = (
                ref.where(filter=FieldFilter("status", "==", status_filter))
                .order_by("created_at", direction="DESCENDING")
                .limit(limit)
            )
        else:
            query = ref.order_by("created_at", direction="DESCENDING").limit(limit)

        for doc in query.stream():
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
    except Exception as e:
        st.error(f"Error loading jobs: {e}")
    return results


def force_refund_job(job: dict):
    """Force refund a stuck RESERVED job."""
    job_id = job.get("id", "")
    uid = job.get("uid", "")
    reserved = job.get("reserved_credits", job.get("file_count", 0) * job.get("rate", 3))

    # Update job status
    jobs_ref().document(job_id).update({
        "status": "EXPIRED",
        "expired_at": datetime.utcnow(),
        "refunded": reserved,
        "admin_force_refund": True,
    })

    # Refund credits to user
    user_doc = users_ref().document(uid)
    user_snap = user_doc.get()
    if user_snap.exists:
        user_data = user_snap.to_dict()
        current = user_data.get("credits", 0)
        new_balance = current + reserved
        user_doc.update({"credits": new_balance})

        # Create refund transaction
        transactions_ref().add({
            "uid": uid,
            "type": "refund",
            "amount": reserved,
            "balance_after": new_balance,
            "job_id": job_id,
            "description": f"Admin force refund for stuck job {job_id[:8]}",
            "created_at": datetime.utcnow(),
            "admin": True,
        })

    return reserved


def format_time_ago(dt) -> str:
    if not dt:
        return "—"
    if hasattr(dt, "timestamp"):
        now = datetime.utcnow()
        diff = now - dt
        if diff.days > 0:
            return f"{diff.days}d ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    return str(dt)


# ── Filter ──

col_filter, col_refresh = st.columns([3, 1])
with col_filter:
    status_filter = st.selectbox(
        "Filter by status",
        ["ALL", "RESERVED", "COMPLETED", "EXPIRED", "FAILED"],
        index=0,
    )
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

jobs = load_jobs(status_filter)

if not jobs:
    st.info(f"No jobs with status: {status_filter}")
    st.stop()

st.caption(f"Showing {len(jobs)} job(s)")

# ── Jobs table ──

import pandas as pd

table_data = []
for j in jobs:
    created = j.get("created_at", "")
    if hasattr(created, "strftime"):
        created_str = format_time_ago(created)
    else:
        created_str = str(created)

    table_data.append({
        "Token": j.get("id", "")[:8] + "...",
        "User": j.get("email", j.get("uid", "—")[:12]),
        "Mode": j.get("mode", "—"),
        "Files": j.get("file_count", 0),
        "Status": j.get("status", "—"),
        "Created": created_str,
    })

df = pd.DataFrame(table_data)
event = st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# ── Job Detail Panel ──

selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    idx = selected_rows[0]
    job = jobs[idx]
    job_id = job.get("id", "")

    st.divider()
    st.subheader(f"📋 Job Detail: `{job_id[:12]}...`")

    # Info grid
    col1, col2, col3 = st.columns(3)
    with col1:
        reserved = job.get("reserved_credits", 0)
        used = job.get("used_credits", 0)
        refunded = job.get("refunded", 0)
        st.markdown(f"**Reserved:** {reserved:,} cr")
        st.markdown(f"**Used:** {used:,} cr")
        st.markdown(f"**Refunded:** {refunded:,} cr")

    with col2:
        successful = job.get("successful", job.get("ok", 0))
        failed = job.get("failed", 0)
        st.markdown(f"**Successful:** {successful}")
        st.markdown(f"**Failed:** {failed}")
        st.markdown(f"**Status:** {job.get('status', '—')}")

    with col3:
        st.markdown(f"**Model:** {job.get('model', '—')}")
        st.markdown(f"**Version:** {job.get('version', '—')}")
        st.markdown(f"**Mode:** {job.get('mode', '—')}")

    # Full job ID and user
    st.markdown(f"**Job ID:** `{job_id}`")
    st.markdown(f"**User UID:** `{job.get('uid', '—')}`")

    created = job.get("created_at", "")
    if hasattr(created, "strftime"):
        st.markdown(f"**Created:** {created.strftime('%Y-%m-%d %H:%M:%S')}")

    # Force refund for stuck RESERVED jobs
    if job.get("status") == "RESERVED":
        st.divider()
        st.warning("⚠️ This job is in RESERVED status.")

        # Check if it's stuck (older than 2 hours)
        created_dt = job.get("created_at")
        is_stuck = False
        if hasattr(created_dt, "timestamp"):
            age = datetime.utcnow() - created_dt
            is_stuck = age > timedelta(hours=2)
            st.markdown(f"**Age:** {format_time_ago(created_dt)}")

        if is_stuck:
            st.error("🔴 This job appears stuck (>2 hours old)")

        if st.button("💰 Force Refund", key=f"refund_{job_id}", type="primary"):
            try:
                refunded_amount = force_refund_job(job)
                st.success(f"✅ Refunded {refunded_amount:,} credits to user")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")
