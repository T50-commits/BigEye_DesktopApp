"""
BigEye Pro Admin — หน้าจัดการผู้ใช้
ค้นหา, ดูข้อมูล, ปรับเครดิต, ระงับ/เปิดบัญชี, รีเซ็ต Hardware ID
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import users_ref, transactions_ref, jobs_ref


st.header("👥 ผู้ใช้งาน")


# ── Data loading ──

def search_users(query: str = "") -> list[dict]:
    ref = users_ref()
    results = []
    try:
        if query:
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
        st.error(f"เกิดข้อผิดพลาดในการโหลดผู้ใช้: {e}")
    return results


def get_user_jobs(uid: str, limit: int = 20) -> list[dict]:
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
    if not dt:
        return "—"
    try:
        if hasattr(dt, "timestamp"):
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            diff = now - dt
            if diff.days > 0:
                return f"{diff.days} วันก่อน"
            hours = diff.seconds // 3600
            if hours > 0:
                return f"{hours} ชม.ก่อน"
            minutes = diff.seconds // 60
            return f"{minutes} นาทีก่อน"
    except Exception:
        pass
    return str(dt)


# ── Search bar ──

search_query = st.text_input("🔍 ค้นหาด้วยอีเมลหรือชื่อ", placeholder="john@example.com")

users = search_users(search_query)

if not users:
    st.info("ไม่พบผู้ใช้")
    st.stop()

# ── Users table ──

st.caption(f"แสดง {len(users)} ผู้ใช้")

table_data = []
for u in users:
    table_data.append({
        "อีเมล": u.get("email", "—"),
        "ชื่อ": u.get("name", "—"),
        "เครดิต": u.get("credits", 0),
        "สถานะ": u.get("status", "active"),
        "ใช้งานล่าสุด": format_time_ago(u.get("last_login")),
    })

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

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**ชื่อ:** {user.get('name', '—')}")
        st.markdown(f"**โทรศัพท์:** {user.get('phone', '—')}")
        st.markdown(f"**Hardware ID:** `{user.get('hardware_id', '—')}`")
    with col2:
        st.markdown(f"**เครดิต:** {user.get('credits', 0):,}")
        st.markdown(f"**เติมเงินรวม:** ฿{user.get('total_topup', 0):,}")
        st.markdown(f"**สถานะ:** {user.get('status', 'active')}")
    with col3:
        created = user.get("created_at", "—")
        if hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d")
        st.markdown(f"**สมัครเมื่อ:** {created}")
        st.markdown(f"**เข้าสู่ระบบล่าสุด:** {format_time_ago(user.get('last_login'))}")
        st.markdown(f"**เวอร์ชันแอป:** {user.get('app_version', '—')}")

    st.divider()

    # ── Actions ──
    st.subheader("จัดการ")

    act_col1, act_col2, act_col3 = st.columns(3)

    # Adjust Credits
    with act_col1:
        st.markdown("**ปรับเครดิต**")
        with st.form(f"adjust_{uid}", clear_on_submit=True):
            adj_amount = st.number_input("จำนวน (+/-)", value=0, step=100, key=f"adj_amt_{uid}")
            adj_reason = st.text_input("เหตุผล", key=f"adj_reason_{uid}")
            adj_submit = st.form_submit_button("ยืนยัน")

        if adj_submit and adj_amount != 0:
            try:
                user_doc = users_ref().document(uid)
                current = user.get("credits", 0)
                new_balance = max(0, current + adj_amount)
                user_doc.update({"credits": new_balance})

                transactions_ref().add({
                    "uid": uid,
                    "type": "adjustment",
                    "amount": adj_amount,
                    "balance_after": new_balance,
                    "description": f"แอดมินปรับ: {adj_reason or 'ไม่ระบุเหตุผล'}",
                    "created_at": datetime.now(timezone.utc),
                    "admin": True,
                })

                st.success(f"✅ ปรับเครดิตแล้ว: {current:,} → {new_balance:,}")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"ล้มเหลว: {e}")

    # Suspend / Unsuspend
    with act_col2:
        st.markdown("**สถานะบัญชี**")
        current_status = user.get("status", "active")

        if current_status == "active":
            if st.button("🔴 ระงับบัญชี", key=f"suspend_{uid}"):
                try:
                    users_ref().document(uid).update({"status": "suspended"})
                    st.success("ระงับบัญชีแล้ว")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"ล้มเหลว: {e}")
        else:
            if st.button("🟢 เปิดบัญชี", key=f"unsuspend_{uid}"):
                try:
                    users_ref().document(uid).update({"status": "active"})
                    st.success("เปิดบัญชีแล้ว")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"ล้มเหลว: {e}")

    # Reset Hardware ID
    with act_col3:
        st.markdown("**Hardware ID**")
        st.code(user.get("hardware_id", "—"), language=None)
        if st.button("🔄 รีเซ็ต Hardware ID", key=f"reset_hw_{uid}"):
            try:
                users_ref().document(uid).update({"hardware_id": ""})
                st.success("รีเซ็ต Hardware ID แล้ว")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"ล้มเหลว: {e}")

    # ── User's Job History ──
    st.divider()
    with st.expander("📋 ดูประวัติงาน"):
        user_jobs = get_user_jobs(uid)
        if not user_jobs:
            st.info("ไม่พบประวัติงานของผู้ใช้นี้")
        else:
            job_table = []
            for j in user_jobs:
                created = j.get("created_at", "")
                if hasattr(created, "strftime"):
                    created = created.strftime("%Y-%m-%d %H:%M")
                job_table.append({
                    "Token": j.get("id", "")[:8] + "...",
                    "โหมด": j.get("mode", "—"),
                    "ไฟล์": j.get("file_count", 0),
                    "สถานะ": j.get("status", "—"),
                    "สร้างเมื่อ": created,
                })
            st.dataframe(pd.DataFrame(job_table), use_container_width=True, hide_index=True)
