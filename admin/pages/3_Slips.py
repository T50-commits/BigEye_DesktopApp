"""
BigEye Pro Admin — Slips (Top-Up Management) Page
Filter, view slip image, approve/reject slips, flag duplicates.
"""
import streamlit as st
import base64
from datetime import datetime
from google.cloud.firestore_v1 import FieldFilter

from utils.firestore_client import slips_ref, users_ref, transactions_ref


st.header("🧾 Slips")


# ── Data loading ──

def load_slips(status_filter: str = "ALL", limit: int = 100) -> list[dict]:
    """Load slips from Firestore with optional status filter."""
    results = []
    try:
        ref = slips_ref()
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
        st.error(f"Error loading slips: {e}")
    return results


def approve_slip(slip_id: str, slip: dict, credit_amount: int):
    """Approve a slip: update status, add credits, create transaction."""
    uid = slip.get("uid", "")
    amount_thb = slip.get("amount", 0)

    # Update slip status
    slips_ref().document(slip_id).update({
        "status": "VERIFIED",
        "verified_at": datetime.utcnow(),
        "credit_amount": credit_amount,
    })

    # Add credits to user
    user_doc = users_ref().document(uid)
    user_snap = user_doc.get()
    if user_snap.exists:
        user_data = user_snap.to_dict()
        current = user_data.get("credits", 0)
        new_balance = current + credit_amount
        total_topup = user_data.get("total_topup", 0) + amount_thb
        user_doc.update({
            "credits": new_balance,
            "total_topup": total_topup,
        })

        # Create transaction
        transactions_ref().add({
            "uid": uid,
            "type": "topup",
            "amount": credit_amount,
            "amount_thb": amount_thb,
            "balance_after": new_balance,
            "slip_id": slip_id,
            "description": f"Top-up {amount_thb} THB → {credit_amount} credits",
            "created_at": datetime.utcnow(),
        })


def reject_slip(slip_id: str, reason: str):
    """Reject a slip with reason."""
    slips_ref().document(slip_id).update({
        "status": "REJECTED",
        "rejected_at": datetime.utcnow(),
        "reject_reason": reason,
    })


# ── Filter ──

col_filter, col_refresh = st.columns([3, 1])
with col_filter:
    status_filter = st.selectbox(
        "Filter by status",
        ["PENDING", "VERIFIED", "REJECTED", "ALL"],
        index=0,
    )
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()


slips = load_slips(status_filter)

if not slips:
    st.info(f"No slips with status: {status_filter}")
    st.stop()

st.caption(f"Showing {len(slips)} slip(s)")

# ── Slips table ──

import pandas as pd

table_data = []
for s in slips:
    created = s.get("created_at", "")
    if hasattr(created, "strftime"):
        created = created.strftime("%m/%d %H:%M")
    table_data.append({
        "Date": created,
        "User": s.get("email", s.get("uid", "—")[:12]),
        "Amount": f"{s.get('amount', 0)} THB",
        "Status": s.get("status", "—"),
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
    st.subheader("🔍 Slip Review")

    review_left, review_right = st.columns([1, 1])

    with review_left:
        # Show slip image
        slip_image = slip.get("slip_base64", slip.get("slip_image", ""))
        if slip_image:
            try:
                # Handle both raw base64 and data URI
                if slip_image.startswith("data:"):
                    img_data = slip_image.split(",", 1)[1]
                else:
                    img_data = slip_image
                img_bytes = base64.b64decode(img_data)
                st.image(img_bytes, caption="Payment Slip", use_container_width=True)
            except Exception:
                st.warning("Cannot display slip image")
        else:
            st.info("No slip image attached")

    with review_right:
        # Slip info
        st.markdown(f"**User:** {slip.get('email', slip.get('uid', '—'))}")
        st.markdown(f"**Amount:** {slip.get('amount', 0)} THB")

        bank_ref = slip.get("bank_ref", slip.get("reference", "—"))
        st.markdown(f"**Bank Ref:** {bank_ref}")

        created = slip.get("created_at", "—")
        if hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"**Submitted:** {created}")

        st.markdown(f"**Status:** {slip.get('status', '—')}")

        # Actions for PENDING slips
        if slip.get("status") == "PENDING":
            st.divider()

            # Credit calculation
            amount_thb = slip.get("amount", 0)
            exchange_rate = 4  # default
            default_credits = amount_thb * exchange_rate

            credit_amount = st.number_input(
                "Credit amount",
                value=default_credits,
                min_value=0,
                step=100,
                key=f"credit_{slip_id}",
            )

            action_col1, action_col2 = st.columns(2)

            with action_col1:
                if st.button("✅ Approve", key=f"approve_{slip_id}", type="primary"):
                    try:
                        approve_slip(slip_id, slip, credit_amount)
                        st.success(f"✅ Approved: +{credit_amount:,} credits")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

            with action_col2:
                reject_reason = st.text_input(
                    "Reject reason",
                    key=f"reject_reason_{slip_id}",
                    placeholder="Duplicate / Invalid / etc.",
                )
                if st.button("❌ Reject", key=f"reject_{slip_id}"):
                    if not reject_reason:
                        st.warning("Please provide a reason")
                    else:
                        try:
                            reject_slip(slip_id, reject_reason)
                            st.success("❌ Slip rejected")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
