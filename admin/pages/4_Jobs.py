"""
BigEye Pro Admin — หน้าตรวจสอบงาน
กรอง, ดูรายละเอียดงาน, คืนเครดิตงานค้าง
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import jobs_ref, users_ref, transactions_ref


st.header("⚙️ ตรวจสอบงาน")


# ── Data loading ──

def load_jobs(status_filter: str = "ALL", limit: int = 100) -> list[dict]:
    results = []
    try:
        ref = jobs_ref()
        if status_filter != "ALL":
            query = ref.where(filter=FieldFilter("status", "==", status_filter)).limit(limit)
        else:
            query = ref.limit(limit)

        docs = list(query.stream())
        docs.sort(
            key=lambda d: d.to_dict().get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        for doc in docs[:limit]:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดงาน: {e}")
    return results


def force_refund_job(job: dict):
    job_id = job.get("id", "")
    uid = job.get("user_id", job.get("uid", ""))
    reserved = job.get("reserved_credits", job.get("file_count", 0) * job.get("credit_rate", 3))

    jobs_ref().document(job_id).update({
        "status": "EXPIRED",
        "expired_at": datetime.now(timezone.utc),
        "refund_amount": reserved,
        "admin_force_refund": True,
    })

    user_doc = users_ref().document(uid)
    user_snap = user_doc.get()
    if user_snap.exists:
        user_data = user_snap.to_dict()
        current = user_data.get("credits", 0)
        new_balance = current + reserved
        user_doc.update({"credits": new_balance})

        transactions_ref().add({
            "user_id": uid,
            "type": "REFUND",
            "amount": reserved,
            "balance_after": new_balance,
            "job_id": job_id,
            "description": f"แอดมินคืนเครดิตงานค้าง {job_id[:8]}",
            "created_at": datetime.now(timezone.utc),
            "admin": True,
        })

    return reserved


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


# ── Filter ──

col_filter, col_refresh = st.columns([3, 1])
with col_filter:
    status_filter = st.selectbox(
        "กรองตามสถานะ",
        ["ALL", "RESERVED", "COMPLETED", "EXPIRED", "FAILED"],
        index=0,
    )
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 รีเฟรช"):
        st.cache_data.clear()
        st.rerun()

jobs = load_jobs(status_filter)

if not jobs:
    st.info(f"ไม่พบงานที่มีสถานะ: {status_filter}")
    st.stop()

st.caption(f"แสดง {len(jobs)} งาน")

# ── Jobs table ──

table_data = []
for j in jobs:
    created = j.get("created_at", "")
    if hasattr(created, "strftime"):
        created_str = format_time_ago(created)
    else:
        created_str = str(created)

    table_data.append({
        "Token": j.get("id", "")[:8] + "...",
        "ผู้ใช้": j.get("email", j.get("user_id", "—")[:12]),
        "โหมด": j.get("mode", "—"),
        "ไฟล์": j.get("file_count", 0),
        "สถานะ": j.get("status", "—"),
        "สร้างเมื่อ": created_str,
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
    st.subheader(f"📋 รายละเอียดงาน: `{job_id[:12]}...`")

    col1, col2, col3 = st.columns(3)
    with col1:
        reserved = job.get("reserved_credits", 0)
        used = job.get("actual_usage", job.get("used_credits", 0))
        refunded = job.get("refund_amount", job.get("refunded", 0))
        st.markdown(f"**จองไว้:** {reserved:,} cr")
        st.markdown(f"**ใช้แล้ว:** {used:,} cr")
        st.markdown(f"**คืนแล้ว:** {refunded:,} cr")

    with col2:
        successful = job.get("success_count", job.get("successful", 0))
        failed = job.get("failed_count", job.get("failed", 0))
        st.markdown(f"**สำเร็จ:** {successful}")
        st.markdown(f"**ล้มเหลว:** {failed}")
        st.markdown(f"**สถานะ:** {job.get('status', '—')}")

    with col3:
        client_info = job.get("client_info", {})
        st.markdown(f"**โมเดล:** {client_info.get('model_used', job.get('model', '—'))}")
        st.markdown(f"**เวอร์ชัน:** {client_info.get('app_version', job.get('version', '—'))}")
        st.markdown(f"**โหมด:** {job.get('mode', '—')}")

    st.markdown(f"**Job ID:** `{job_id}`")
    st.markdown(f"**User ID:** `{job.get('user_id', job.get('uid', '—'))}`")

    created = job.get("created_at", "")
    if hasattr(created, "strftime"):
        st.markdown(f"**สร้างเมื่อ:** {created.strftime('%Y-%m-%d %H:%M:%S')}")

    if job.get("status") == "RESERVED":
        st.divider()
        st.warning("⚠️ งานนี้อยู่ในสถานะ RESERVED")

        created_dt = job.get("created_at")
        is_stuck = False
        if hasattr(created_dt, "timestamp"):
            now = datetime.now(timezone.utc)
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            age = now - created_dt
            is_stuck = age > timedelta(hours=2)
            st.markdown(f"**อายุ:** {format_time_ago(created_dt)}")

        if is_stuck:
            st.error("🔴 งานนี้ค้างเกิน 2 ชั่วโมง")

        if st.button("💰 คืนเครดิต", key=f"refund_{job_id}", type="primary"):
            try:
                refunded_amount = force_refund_job(job)
                st.success(f"✅ คืนเครดิตแล้ว {refunded_amount:,} เครดิต")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"ล้มเหลว: {e}")
