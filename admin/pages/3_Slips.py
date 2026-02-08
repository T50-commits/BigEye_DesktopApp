"""
BigEye Pro Admin — หน้าจัดการสลิป (เติมเงิน)
กรองสถานะ, ดูภาพสลิป, อนุมัติ/ปฏิเสธ
"""
import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timezone
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import slips_ref, users_ref, transactions_ref
from utils.theme import inject_css

inject_css()
st.header("🧾 สลิปเติมเงิน")


# ── Data loading ──

def load_slips(status_filter: str = "ALL", limit: int = 100) -> list[dict]:
    results = []
    try:
        ref = slips_ref()
        if status_filter != "ALL":
            # Use simple filter without ordering to avoid composite index requirement
            query = ref.where(filter=FieldFilter("status", "==", status_filter)).limit(limit)
        else:
            query = ref.limit(limit)

        docs = list(query.stream())
        # Sort in Python to avoid Firestore composite index
        docs.sort(
            key=lambda d: d.to_dict().get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        for doc in docs[:limit]:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดสลิป: {e}")
    return results


def approve_slip(slip_id: str, slip: dict, credit_amount: int):
    uid = slip.get("user_id", slip.get("uid", ""))
    amount_thb = slip.get("amount", slip.get("amount_detected", 0))

    slips_ref().document(slip_id).update({
        "status": "VERIFIED",
        "verified_at": datetime.now(timezone.utc),
        "credit_amount": credit_amount,
    })

    user_doc = users_ref().document(uid)
    user_snap = user_doc.get()
    if user_snap.exists:
        user_data = user_snap.to_dict()
        current = user_data.get("credits", 0)
        new_balance = current + credit_amount
        total_topup = user_data.get("total_topup_baht", 0) + amount_thb
        user_doc.update({
            "credits": new_balance,
            "total_topup_baht": total_topup,
        })

        transactions_ref().add({
            "user_id": uid,
            "type": "TOPUP",
            "amount": credit_amount,
            "amount_thb": amount_thb,
            "balance_after": new_balance,
            "slip_id": slip_id,
            "description": f"เติมเงิน {amount_thb} บาท → {credit_amount} เครดิต",
            "created_at": datetime.now(timezone.utc),
        })


def reject_slip(slip_id: str, reason: str):
    slips_ref().document(slip_id).update({
        "status": "REJECTED",
        "rejected_at": datetime.now(timezone.utc),
        "reject_reason": reason,
    })


# ── Filter ──

col_filter, col_refresh = st.columns([3, 1])
with col_filter:
    status_filter = st.selectbox(
        "กรองตามสถานะ",
        ["PENDING", "VERIFIED", "REJECTED", "ALL"],
        index=0,
    )
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 รีเฟรช"):
        st.cache_data.clear()
        st.rerun()


slips = load_slips(status_filter)

if not slips:
    st.info(f"ไม่พบสลิปที่มีสถานะ: {status_filter}")
    st.stop()

st.caption(f"แสดง {len(slips)} รายการ")

# ── Slips table ──

table_data = []
for s in slips:
    created = s.get("created_at", "")
    if hasattr(created, "strftime"):
        created = created.strftime("%d/%m %H:%M")
    table_data.append({
        "วันที่": created,
        "ผู้ใช้": s.get("email", s.get("user_id", "—")[:12]),
        "จำนวน": f"{s.get('amount', s.get('amount_detected', 0))} บาท",
        "สถานะ": s.get("status", "—"),
    })

df = pd.DataFrame(table_data)
event = st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# ── Slip Review Panel ──

selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    idx = selected_rows[0]
    slip = slips[idx]
    slip_id = slip.get("id", "")

    st.divider()
    st.subheader("🔍 ตรวจสอบสลิป")

    review_left, review_right = st.columns([1, 1])

    with review_left:
        slip_image = slip.get("slip_base64", slip.get("slip_image", ""))
        if slip_image:
            try:
                if slip_image.startswith("data:"):
                    img_data = slip_image.split(",", 1)[1]
                else:
                    img_data = slip_image
                img_bytes = base64.b64decode(img_data)
                st.image(img_bytes, caption="สลิปการชำระเงิน", use_container_width=True)
            except Exception:
                st.warning("ไม่สามารถแสดงภาพสลิปได้")
        else:
            st.info("ไม่มีภาพสลิปแนบ")

    with review_right:
        st.markdown(f"**ผู้ใช้:** {slip.get('email', slip.get('user_id', '—'))}")
        st.markdown(f"**จำนวน:** {slip.get('amount', slip.get('amount_detected', 0))} บาท")

        bank_ref = slip.get("bank_ref", slip.get("reference", "—"))
        st.markdown(f"**เลขอ้างอิงธนาคาร:** {bank_ref}")

        created = slip.get("created_at", "—")
        if hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"**ส่งเมื่อ:** {created}")

        st.markdown(f"**สถานะ:** {slip.get('status', '—')}")

        if slip.get("status") == "PENDING":
            st.divider()

            amount_thb = slip.get("amount", 0)
            exchange_rate = 4
            default_credits = amount_thb * exchange_rate

            credit_amount = st.number_input(
                "จำนวนเครดิต",
                value=default_credits,
                min_value=0,
                step=100,
                key=f"credit_{slip_id}",
            )

            action_col1, action_col2 = st.columns(2)

            with action_col1:
                if st.button("✅ อนุมัติ", key=f"approve_{slip_id}", type="primary"):
                    try:
                        approve_slip(slip_id, slip, credit_amount)
                        st.success(f"✅ อนุมัติแล้ว: +{credit_amount:,} เครดิต")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"ล้มเหลว: {e}")

            with action_col2:
                reject_reason = st.text_input(
                    "เหตุผลที่ปฏิเสธ",
                    key=f"reject_reason_{slip_id}",
                    placeholder="ซ้ำ / ไม่ถูกต้อง / อื่นๆ",
                )
                if st.button("❌ ปฏิเสธ", key=f"reject_{slip_id}"):
                    if not reject_reason:
                        st.warning("กรุณาระบุเหตุผล")
                    else:
                        try:
                            reject_slip(slip_id, reject_reason)
                            st.success("❌ ปฏิเสธสลิปแล้ว")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"ล้มเหลว: {e}")
