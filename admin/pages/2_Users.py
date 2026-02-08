"""
BigEye Pro Admin — Users Page
Search, view, adjust credits, suspend/unsuspend, reset hardware ID.
"""
import streamlit as st
from datetime import datetime
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import users_ref, transactions_ref, jobs_ref


st.header("👥 Users")


# ── Data loading ──

def search_users(query: str = "") -> list[dict]:
    """Search users by email or name. Returns list of user dicts."""
    ref = users_ref()
    results = []

    try:
        if query:
            # Search by email prefix
            docs = (
                ref.where(filter=FieldFilter("email", ">=", query))
                .where(filter=FieldFilter("email", "<=", query + "\uf8ff"))
                .limit(50)
                .stream()
            )
            for doc in docs:
                d = doc.to_dict()
                d["uid"] = doc.id
                results.append(d)

            # Also search by name if few results
            if len(results) < 5:
                name_docs = (
                    ref.where(filter=FieldFilter("name", ">=", query))
                    .where(filter=FieldFilter("name", "<=", query + "\uf8ff"))
                    .limit(20)
                    .stream()
                )
                existing_uids = {r["uid"] for r in results}
                for doc in name_docs:
                    if doc.id not in existing_uids:
                        d = doc.to_dict()
                        d["uid"] = doc.id
                        results.append(d)
        else:
            docs = ref.order_by("created_at", direction="DESCENDING").limit(50).stream()
            for doc in docs:
                d = doc.to_dict()
                d["uid"] = doc.id
                results.append(d)
    except Exception as e:
        st.error(f"Error loading users: {e}")

    return results


def get_user_jobs(uid: str, limit: int = 20) -> list[dict]:
    """Get recent jobs for a user."""
    results = []
    try:
        docs = (
            jobs_ref()
            .where(filter=FieldFilter("uid", "==", uid))
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
    except Exception:
        pass
    return results


def format_time_ago(dt) -> str:
    """Format a datetime as relative time ago."""
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


# ── Search bar ──

search_query = st.text_input("🔍 Search by email or name", placeholder="john@example.com")

users = search_users(search_query)

if not users:
    st.info("No users found.")
    st.stop()

# ── Users table ──

st.caption(f"Showing {len(users)} user(s)")

# Build table data
table_data = []
for u in users:
    table_data.append({
        "Email": u.get("email", "—"),
        "Name": u.get("name", "—"),
        "Credits": u.get("credits", 0),
        "Status": u.get("status", "active"),
        "Last Active": format_time_ago(u.get("last_login")),
    })

# Display as selectable dataframe
import pandas as pd
df = pd.DataFrame(table_data)

event = st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# ── User Detail Panel ──

selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    idx = selected_rows[0]
    user = users[idx]
    uid = user.get("uid", "")

    st.divider()
    st.subheader(f"👤 {user.get('email', '—')}")

    # Info grid
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Name:** {user.get('name', '—')}")
        st.markdown(f"**Phone:** {user.get('phone', '—')}")
        st.markdown(f"**Hardware ID:** `{user.get('hardware_id', '—')}`")
    with col2:
        st.markdown(f"**Credits:** {user.get('credits', 0):,}")
        st.markdown(f"**Total Top-up:** ฿{user.get('total_topup', 0):,}")
        st.markdown(f"**Status:** {user.get('status', 'active')}")
    with col3:
        created = user.get("created_at", "—")
        if hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d")
        st.markdown(f"**Registered:** {created}")
        st.markdown(f"**Last Login:** {format_time_ago(user.get('last_login'))}")
        st.markdown(f"**App Version:** {user.get('app_version', '—')}")

    st.divider()

    # ── Actions ──
    st.subheader("Actions")

    act_col1, act_col2, act_col3 = st.columns(3)

    # Adjust Credits
    with act_col1:
        st.markdown("**Adjust Credits**")
        with st.form(f"adjust_{uid}", clear_on_submit=True):
            adj_amount = st.number_input("Amount (+/-)", value=0, step=100, key=f"adj_amt_{uid}")
            adj_reason = st.text_input("Reason", key=f"adj_reason_{uid}")
            adj_submit = st.form_submit_button("Apply")

        if adj_submit and adj_amount != 0:
            try:
                user_doc = users_ref().document(uid)
                current = user.get("credits", 0)
                new_balance = max(0, current + adj_amount)
                user_doc.update({"credits": new_balance})

                # Create transaction record
                transactions_ref().add({
                    "uid": uid,
                    "type": "adjustment",
                    "amount": adj_amount,
                    "balance_after": new_balance,
                    "description": f"Admin adjustment: {adj_reason or 'No reason'}",
                    "created_at": datetime.utcnow(),
                    "admin": True,
                })

                st.success(f"✅ Credits adjusted: {current:,} → {new_balance:,}")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

    # Suspend / Unsuspend
    with act_col2:
        st.markdown("**Account Status**")
        current_status = user.get("status", "active")

        if current_status == "active":
            if st.button("🔴 Suspend User", key=f"suspend_{uid}"):
                try:
                    users_ref().document(uid).update({"status": "suspended"})
                    st.success("User suspended")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
        else:
            if st.button("🟢 Unsuspend User", key=f"unsuspend_{uid}"):
                try:
                    users_ref().document(uid).update({"status": "active"})
                    st.success("User unsuspended")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

    # Reset Hardware ID
    with act_col3:
        st.markdown("**Hardware ID**")
        st.code(user.get("hardware_id", "—"), language=None)
        if st.button("🔄 Reset Hardware ID", key=f"reset_hw_{uid}"):
            try:
                users_ref().document(uid).update({"hardware_id": ""})
                st.success("Hardware ID reset")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

    # ── User's Job History ──
    st.divider()
    with st.expander("📋 View Job History"):
        user_jobs = get_user_jobs(uid)
        if not user_jobs:
            st.info("No jobs found for this user.")
        else:
            job_table = []
            for j in user_jobs:
                created = j.get("created_at", "")
                if hasattr(created, "strftime"):
                    created = created.strftime("%Y-%m-%d %H:%M")
                job_table.append({
                    "Token": j.get("id", "")[:8] + "...",
                    "Mode": j.get("mode", "—"),
                    "Files": j.get("file_count", 0),
                    "Status": j.get("status", "—"),
                    "Created": created,
                })
            st.dataframe(pd.DataFrame(job_table), use_container_width=True, hide_index=True)
