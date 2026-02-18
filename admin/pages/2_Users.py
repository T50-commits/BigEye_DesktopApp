"""
BigEye Pro Admin — หน้าจัดการผู้ใช้
ค้นหา, ดูข้อมูล, ปรับเครดิต, ระงับ/เปิดบัญชี, รีเซ็ต Hardware ID
"""
import streamlit as st
from utils.auth import require_auth
require_auth()

import pandas as pd
from datetime import datetime, timezone
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import users_ref, transactions_ref, jobs_ref
from utils.theme import inject_css
from utils.timezone import to_local, fmt_datetime, fmt_date

inject_css()
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
                    ref.where(filter=FieldFilter("full_name", ">=", query))
                    .where(filter=FieldFilter("full_name", "<=", query + "\uf8ff"))
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


def get_user_jobs(uid: str, limit: int = 50) -> list[dict]:
    results = []
    try:
        # Fetch all jobs for user, sort in Python to avoid composite index requirement
        docs = list(
            jobs_ref()
            .where(filter=FieldFilter("user_id", "==", uid))
            .stream()
        )
        docs.sort(
            key=lambda d: d.to_dict().get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        for doc in docs[:limit]:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
    except Exception as e:
        import streamlit as _st
        _st.warning(f"โหลดประวัติงานไม่ได้: {e}")
    return results


def get_user_transactions(uid: str, limit: int = 50) -> list[dict]:
    results = []
    try:
        # Fetch all transactions for user, sort in Python to avoid composite index requirement
        docs = list(
            transactions_ref()
            .where(filter=FieldFilter("user_id", "==", uid))
            .stream()
        )
        docs.sort(
            key=lambda d: d.to_dict().get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        for doc in docs[:limit]:
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
    return fmt_datetime(dt) if hasattr(dt, 'strftime') else str(dt)


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
        "ชื่อ": u.get("full_name", "—"),
        "เครดิต": u.get("credits", 0),
        "สถานะ": u.get("status", "active"),
        "ใช้งานล่าสุด": format_time_ago(u.get("last_login")),
    })

df = pd.DataFrame(table_data)
st.dataframe(df, use_container_width=True, hide_index=True)

# ── Select user for details ──

user_options = [f"{u.get('email', '—')}  ({u.get('full_name', '—')})" for u in users]
selected_idx = st.selectbox(
    "👤 เลือกผู้ใช้เพื่อดูรายละเอียด",
    range(len(users)),
    format_func=lambda i: user_options[i],
    index=None,
    placeholder="คลิกเพื่อเลือกผู้ใช้...",
)

# ── User Detail Panel ──

if selected_idx is not None:
    user = users[selected_idx]
    uid = user.get("uid", "")

    st.divider()
    st.subheader(f"👤 {user.get('email', '—')}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**ชื่อ:** {user.get('full_name', '—')}")
        st.markdown(f"**โทรศัพท์:** {user.get('phone', '—')}")
        st.markdown(f"**Hardware ID:** `{user.get('hardware_id', '—')}`")
    with col2:
        st.markdown(f"**เครดิต:** {user.get('credits', 0):,}")
        st.markdown(f"**เติมเงินรวม:** ฿{user.get('total_topup_baht', 0):,}")
        st.markdown(f"**สถานะ:** {user.get('status', 'active')}")
    with col3:
        created = user.get("created_at", "—")
        st.markdown(f"**สมัครเมื่อ:** {fmt_date(created) if hasattr(created, 'strftime') else created}")
        st.markdown(f"**เข้าสู่ระบบล่าสุด:** {format_time_ago(user.get('last_login'))}")
        st.markdown(f"**เวอร์ชันแอป:** {user.get('app_version', '—')}")

    st.divider()

    # ── Actions ──
    st.subheader("จัดการ")

    act_col1, act_col2, act_col3, act_col4 = st.columns(4)

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
                    "user_id": uid,
                    "type": "ADJUSTMENT",
                    "amount": adj_amount,
                    "balance_after": new_balance,
                    "reference_id": uid,
                    "description": f"แอดมินปรับ: {adj_reason or 'ไม่ระบุเหตุผล'}",
                    "created_at": datetime.now(timezone.utc),
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

    # Reset Password
    with act_col4:
        st.markdown("**รีเซ็ตรหัสผ่าน**")
        with st.form(f"reset_pw_{uid}", clear_on_submit=True):
            new_pw = st.text_input("รหัสผ่านใหม่", type="password", key=f"new_pw_{uid}",
                                   placeholder="อย่างน้อย 8 ตัวอักษร")
            reset_hw_too = st.checkbox("รีเซ็ต Hardware ID ด้วย", key=f"reset_hw_too_{uid}")
            pw_submit = st.form_submit_button("🔑 ตั้งรหัสใหม่")

        if pw_submit and new_pw:
            if len(new_pw) < 8:
                st.error("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
            else:
                try:
                    from passlib.context import CryptContext
                    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    hashed = pwd_ctx.hash(new_pw)
                    update_data = {"password_hash": hashed}
                    if reset_hw_too:
                        update_data["hardware_id"] = ""
                    users_ref().document(uid).update(update_data)
                    msg = "✅ รีเซ็ตรหัสผ่านแล้ว"
                    if reset_hw_too:
                        msg += " + รีเซ็ต Hardware ID"
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"ล้มเหลว: {e}")

    # ── User's History ──
    st.divider()
    hist_tab1, hist_tab2 = st.tabs(["💳 ประวัติเครดิต", "📋 ประวัติงาน"])

    with hist_tab1:
        txns = get_user_transactions(uid)
        if not txns:
            st.info("ไม่พบประวัติเครดิตของผู้ใช้นี้")
        else:
            tx_table = []
            for t in txns:
                created = t.get("created_at", "")
                created_str = fmt_datetime(created) if hasattr(created, 'strftime') else str(created)
                amount = t.get("amount", 0)
                tx_table.append({
                    "วันที่": created_str,
                    "รายการ": t.get("description", t.get("type", "—")),
                    "จำนวน": f"{'+' if amount > 0 else ''}{amount:,}",
                    "คงเหลือ": f"{t.get('balance_after', '—'):,}" if isinstance(t.get('balance_after'), (int, float)) else "—",
                })
            st.dataframe(pd.DataFrame(tx_table), use_container_width=True, hide_index=True)

    with hist_tab2:
        user_jobs = get_user_jobs(uid)
        if not user_jobs:
            st.info("ไม่พบประวัติงานของผู้ใช้นี้")
        else:
            job_table = []
            for j in user_jobs:
                created = j.get("created_at", "")
                created_str = fmt_datetime(created) if hasattr(created, 'strftime') else str(created)
                job_table.append({
                    "Token": j.get("job_token", j.get("id", ""))[:12] + "...",
                    "โหมด": j.get("mode", "—"),
                    "ไฟล์": j.get("file_count", 0),
                    "สถานะ": j.get("status", "—"),
                    "สร้างเมื่อ": created_str,
                })
            st.dataframe(pd.DataFrame(job_table), use_container_width=True, hide_index=True)
