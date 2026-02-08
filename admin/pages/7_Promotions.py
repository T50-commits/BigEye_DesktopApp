"""
BigEye Pro Admin — หน้าจัดการโปรโมชั่น
สร้าง, แก้ไข, เปิด/หยุด/ยกเลิก, โคลน, ดูสถิติ
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from utils.firestore_client import promotions_ref, promo_redemptions_ref, users_ref
from utils.theme import inject_css

inject_css()
st.header("🎁 โปรโมชั่น")


# ── Helpers ──

def load_promotions(status_filter: str = "ALL") -> list[dict]:
    results = []
    try:
        ref = promotions_ref()
        if status_filter != "ALL":
            docs = list(ref.where("status", "==", status_filter).stream())
        else:
            docs = list(ref.stream())

        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            results.append(d)

        # Sort: ACTIVE first, then DRAFT/PAUSED, then EXPIRED/CANCELLED
        status_order = {"ACTIVE": 0, "DRAFT": 1, "PAUSED": 1, "EXPIRED": 2, "CANCELLED": 3}
        results.sort(key=lambda p: (status_order.get(p.get("status", ""), 9), -p.get("priority", 0)))
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดโปรโมชั่น: {e}")
    return results


def status_emoji(status: str) -> str:
    return {
        "ACTIVE": "🟢",
        "DRAFT": "📝",
        "PAUSED": "⏸️",
        "EXPIRED": "⬜",
        "CANCELLED": "❌",
    }.get(status, "⚪")


def format_date(dt) -> str:
    if not dt:
        return "—"
    if hasattr(dt, "strftime"):
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(dt)


# ── Filter + Create button ──

col_filter, col_create = st.columns([3, 1])
with col_filter:
    status_filter = st.selectbox(
        "กรองตามสถานะ",
        ["ALL", "ACTIVE", "DRAFT", "PAUSED", "EXPIRED", "CANCELLED"],
        index=0,
    )
with col_create:
    st.markdown("<br>", unsafe_allow_html=True)
    create_new = st.button("➕ สร้างโปรโมชั่นใหม่", type="primary")


# ═══════════════════════════════════════
# Create / Edit Form
# ═══════════════════════════════════════

if create_new or st.session_state.get("show_promo_form"):
    st.session_state["show_promo_form"] = True
    st.divider()
    st.subheader("📝 สร้างโปรโมชั่นใหม่")

    with st.form("create_promo_form", clear_on_submit=True):
        # Basic Info
        st.markdown("**ข้อมูลพื้นฐาน**")
        col1, col2 = st.columns(2)
        with col1:
            promo_name = st.text_input("ชื่อโปร", placeholder="โปรปีใหม่ 2027")
            promo_code = st.text_input("รหัสโปร (ไม่บังคับ)", placeholder="NEWYEAR2027")
        with col2:
            promo_priority = st.number_input("ลำดับความสำคัญ", value=0, step=1)
            require_code = st.checkbox("ต้องกรอกรหัสโปร", help="⚠️ ถ้าเปิด โปรนี้จะไม่แสดงในแอปอัตโนมัติ ผู้ใช้ต้องกรอกรหัสเองตอนเติมเงิน")

        # Type
        st.markdown("**ประเภทโปรโมชั่น**")
        promo_type = st.selectbox("ประเภท", [
            "TIERED_BONUS", "RATE_BOOST", "FLAT_BONUS",
            "WELCOME_BONUS", "FIRST_TOPUP", "USAGE_REWARD",
        ], format_func=lambda x: {
            "TIERED_BONUS": "โบนัสขั้นบันได",
            "RATE_BOOST": "อัตราแลกเปลี่ยนพิเศษ",
            "FLAT_BONUS": "โบนัสเครดิตคงที่",
            "WELCOME_BONUS": "โบนัสสมัครใหม่",
            "FIRST_TOPUP": "โบนัสเติมครั้งแรก",
            "USAGE_REWARD": "รางวัลตามการใช้งาน",
        }.get(x, x))

        # Reward
        st.markdown("**รางวัล**")
        reward_type = st.selectbox("ประเภทรางวัล", [
            "BONUS_CREDITS", "RATE_OVERRIDE", "PERCENTAGE_BONUS", "TIERED_BONUS",
        ], format_func=lambda x: {
            "BONUS_CREDITS": "เครดิตโบนัสคงที่",
            "RATE_OVERRIDE": "เปลี่ยนอัตราแลกเปลี่ยน",
            "PERCENTAGE_BONUS": "โบนัสเป็น %",
            "TIERED_BONUS": "ขั้นบันได (Tiers)",
        }.get(x, x))

        reward_data = {"type": reward_type}
        if reward_type == "BONUS_CREDITS":
            reward_data["bonus_credits"] = st.number_input("จำนวนเครดิตโบนัส", value=200, step=50)
        elif reward_type == "RATE_OVERRIDE":
            reward_data["override_rate"] = st.number_input("อัตราใหม่ (1 บาท = ? เครดิต)", value=5, step=1)
        elif reward_type == "PERCENTAGE_BONUS":
            reward_data["bonus_percentage"] = st.number_input("เปอร์เซ็นต์โบนัส (%)", value=10, step=5)
        elif reward_type == "TIERED_BONUS":
            st.markdown("กรอก Tiers (JSON array)")
            tiers_json = st.text_area(
                "Tiers",
                value='[{"min_baht": 100, "max_baht": 299, "credits": 400}, {"min_baht": 300, "max_baht": 499, "credits": 1300}, {"min_baht": 500, "max_baht": null, "credits": 2200}]',
                height=100,
            )

        # Conditions
        st.markdown("**เงื่อนไข**")
        cond_col1, cond_col2 = st.columns(2)
        with cond_col1:
            start_date = st.date_input("วันเริ่ม")
            min_topup = st.number_input("เติมขั้นต่ำ (บาท, 0=ไม่จำกัด)", value=0, step=50)
            max_redemptions = st.number_input("จำนวนครั้งรวมสูงสุด (0=ไม่จำกัด)", value=0, step=10)
            new_users_only = st.checkbox("เฉพาะผู้ใช้ใหม่")
        with cond_col2:
            end_date = st.date_input("วันสิ้นสุด")
            max_topup = st.number_input("เติมสูงสุด (บาท, 0=ไม่จำกัด)", value=0, step=50)
            max_per_user = st.number_input("จำนวนครั้งต่อผู้ใช้ (0=ไม่จำกัด)", value=0, step=1)
            first_topup_only = st.checkbox("เฉพาะเติมครั้งแรก")

        # Display
        st.markdown("**การแสดงผลในแอป**")
        banner_text = st.text_input("ข้อความ Banner", placeholder="🎄 โปรพิเศษ! เติม 500+ รับ 2,200 เครดิต!")
        banner_color = st.selectbox("สี Banner", ["#FF4560", "#00E396", "#FEB019", "#775DD0"])
        disp_col1, disp_col2 = st.columns(2)
        with disp_col1:
            show_in_client = st.checkbox("แสดง Banner ในแอป", value=True)
        with disp_col2:
            show_in_topup = st.checkbox("แสดงในหน้าเติมเงิน", value=True)

        submitted = st.form_submit_button("💾 บันทึกเป็น Draft")

    if submitted and promo_name:
        import json as _json
        now = datetime.now(timezone.utc)

        conditions = {
            "start_date": datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc),
            "end_date": datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc),
            "min_topup_baht": min_topup if min_topup > 0 else None,
            "max_topup_baht": max_topup if max_topup > 0 else None,
            "max_redemptions": max_redemptions if max_redemptions > 0 else None,
            "max_per_user": max_per_user if max_per_user > 0 else None,
            "new_users_only": new_users_only,
            "first_topup_only": first_topup_only,
            "require_code": require_code,
        }

        if reward_type == "TIERED_BONUS":
            try:
                reward_data["tiers"] = _json.loads(tiers_json)
            except Exception:
                st.error("JSON ของ Tiers ไม่ถูกต้อง")
                st.stop()

        promo_data = {
            "name": promo_name,
            "code": promo_code or None,
            "type": promo_type,
            "status": "DRAFT",
            "priority": promo_priority,
            "conditions": conditions,
            "reward": reward_data,
            "display": {
                "banner_text": banner_text,
                "banner_color": banner_color,
                "show_in_client": show_in_client,
                "show_in_topup": show_in_topup,
            },
            "stats": {
                "total_redemptions": 0,
                "total_bonus_credits": 0,
                "total_baht_collected": 0,
                "unique_users": 0,
            },
            "created_at": now,
            "updated_at": now,
            "created_by": "admin",
        }

        try:
            promotions_ref().add(promo_data)
            st.success(f"✅ สร้างโปรโมชั่น '{promo_name}' แล้ว (สถานะ: DRAFT)")
            st.session_state["show_promo_form"] = False
            st.rerun()
        except Exception as e:
            st.error(f"ล้มเหลว: {e}")

    if st.session_state.get("show_promo_form"):
        if st.button("❌ ยกเลิก"):
            st.session_state["show_promo_form"] = False
            st.rerun()

st.divider()

# ═══════════════════════════════════════
# Promotions List
# ═══════════════════════════════════════

promos = load_promotions(status_filter)

if not promos:
    st.info(f"ไม่พบโปรโมชั่นที่มีสถานะ: {status_filter}")
    st.stop()

st.caption(f"แสดง {len(promos)} โปรโมชั่น")

for promo in promos:
    pid = promo.get("id", "")
    name = promo.get("name", "—")
    status = promo.get("status", "—")
    ptype = promo.get("type", "—")
    emoji = status_emoji(status)
    stats = promo.get("stats", {})

    cond = promo.get("conditions", {})
    start_str = format_date(cond.get("start_date"))
    end_str = format_date(cond.get("end_date"))

    with st.expander(f"{emoji} **{name}** — {status} — ประเภท: {ptype}"):
        # Info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**ประเภท:** {ptype}")
            st.markdown(f"**ลำดับ:** {promo.get('priority', 0)}")
            st.markdown(f"**รหัสโปร:** {promo.get('code') or '—'}")
        with col2:
            st.markdown(f"**ช่วงเวลา:** {start_str} → {end_str}")
            st.markdown(f"**เติมขั้นต่ำ:** {cond.get('min_topup_baht') or 'ไม่จำกัด'} บาท")
            st.markdown(f"**จำกัดต่อคน:** {cond.get('max_per_user') or 'ไม่จำกัด'} ครั้ง")
        with col3:
            st.metric("ใช้แล้ว", f"{stats.get('total_redemptions', 0)} ครั้ง")
            st.metric("โบนัสแจกไป", f"{stats.get('total_bonus_credits', 0):,} เครดิต")
            st.metric("รายได้", f"฿{stats.get('total_baht_collected', 0):,}")

        # Reward details
        reward = promo.get("reward", {})
        if reward.get("tiers"):
            st.markdown("**ขั้นบันได (Tiers):**")
            tier_data = []
            for t in reward["tiers"]:
                tier_data.append({
                    "ขั้นต่ำ (บาท)": t.get("min_baht", 0),
                    "สูงสุด (บาท)": t.get("max_baht") or "ไม่จำกัด",
                    "เครดิตที่ได้": t.get("credits", 0),
                })
            st.dataframe(pd.DataFrame(tier_data), use_container_width=True, hide_index=True)

        # Display info
        display = promo.get("display", {})
        if display.get("banner_text"):
            st.info(f"Banner: {display['banner_text']}")

        # Sync info
        if cond.get("require_code"):
            st.caption("🔒 โปรนี้ต้องกรอกรหัส — จะไม่แสดง Banner อัตโนมัติในแอป")
        if cond.get("new_users_only"):
            st.caption("👤 เฉพาะผู้ใช้ใหม่เท่านั้น")

        # Actions
        st.markdown("---")
        act_cols = st.columns(6)

        with act_cols[0]:
            if status in ("DRAFT", "PAUSED"):
                if st.button("🟢 เปิดใช้งาน", key=f"activate_{pid}"):
                    try:
                        promotions_ref().document(pid).update({
                            "status": "ACTIVE",
                            "updated_at": datetime.now(timezone.utc),
                        })
                        st.success("เปิดใช้งานแล้ว")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ล้มเหลว: {e}")

        with act_cols[1]:
            if status == "ACTIVE":
                if st.button("⏸️ หยุดชั่วคราว", key=f"pause_{pid}"):
                    try:
                        promotions_ref().document(pid).update({
                            "status": "PAUSED",
                            "updated_at": datetime.now(timezone.utc),
                        })
                        st.success("หยุดชั่วคราวแล้ว")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ล้มเหลว: {e}")

        with act_cols[2]:
            if status not in ("CANCELLED",):
                if st.button("❌ ยกเลิก", key=f"cancel_{pid}"):
                    try:
                        promotions_ref().document(pid).update({
                            "status": "CANCELLED",
                            "updated_at": datetime.now(timezone.utc),
                        })
                        st.success("ยกเลิกแล้ว")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ล้มเหลว: {e}")

        with act_cols[3]:
            if st.button("📋 โคลน", key=f"clone_{pid}"):
                try:
                    now = datetime.now(timezone.utc)
                    clone_data = {
                        "name": f"{name} (สำเนา)",
                        "code": None,
                        "type": promo.get("type", ""),
                        "status": "DRAFT",
                        "priority": promo.get("priority", 0),
                        "conditions": promo.get("conditions", {}),
                        "reward": promo.get("reward", {}),
                        "display": promo.get("display", {}),
                        "stats": {"total_redemptions": 0, "total_bonus_credits": 0, "total_baht_collected": 0, "unique_users": 0},
                        "created_at": now,
                        "updated_at": now,
                        "created_by": "admin",
                    }
                    promotions_ref().add(clone_data)
                    st.success(f"โคลนเป็น '{name} (สำเนา)' แล้ว")
                    st.rerun()
                except Exception as e:
                    st.error(f"ล้มเหลว: {e}")

        with act_cols[4]:
            if st.button("✏️ แก้ไข", key=f"edit_{pid}"):
                st.session_state[f"editing_{pid}"] = True

        with act_cols[5]:
            if st.button("🗑️ ลบ", key=f"del_{pid}"):
                st.session_state[f"confirm_del_{pid}"] = True

        # ── Delete confirmation ──
        if st.session_state.get(f"confirm_del_{pid}"):
            st.warning(f"⚠️ ยืนยันลบโปรโมชั่น **{name}**? การลบไม่สามารถกู้คืนได้")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("🗑️ ยืนยันลบ", key=f"confirm_yes_{pid}", type="primary"):
                    try:
                        promotions_ref().document(pid).delete()
                        st.success(f"ลบโปรโมชั่น '{name}' แล้ว")
                        st.session_state.pop(f"confirm_del_{pid}", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"ล้มเหลว: {e}")
            with dc2:
                if st.button("ยกเลิก", key=f"confirm_no_{pid}"):
                    st.session_state.pop(f"confirm_del_{pid}", None)
                    st.rerun()

        # ── Edit form ──
        if st.session_state.get(f"editing_{pid}"):
            st.markdown("### ✏️ แก้ไขโปรโมชั่น")
            with st.form(f"edit_form_{pid}"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    edit_name = st.text_input("ชื่อโปร", value=name, key=f"en_{pid}")
                    edit_code = st.text_input("รหัสโปร", value=promo.get("code") or "", key=f"ec_{pid}")
                    edit_priority = st.number_input("ลำดับ", value=promo.get("priority", 0), step=1, key=f"ep_{pid}")
                with e_col2:
                    edit_banner = st.text_input("ข้อความ Banner", value=display.get("banner_text", ""), key=f"eb_{pid}")
                    edit_color = st.selectbox("สี Banner", ["#FF4560", "#00E396", "#FEB019", "#775DD0"],
                        index=["#FF4560", "#00E396", "#FEB019", "#775DD0"].index(display.get("banner_color", "#FF4560"))
                        if display.get("banner_color") in ["#FF4560", "#00E396", "#FEB019", "#775DD0"] else 0,
                        key=f"ebc_{pid}")
                    edit_min_topup = st.number_input("เติมขั้นต่ำ (บาท)", value=cond.get("min_topup_baht") or 0, step=50, key=f"emt_{pid}")

                if reward.get("bonus_credits"):
                    edit_bonus = st.number_input("เครดิตโบนัส", value=reward.get("bonus_credits", 0), step=50, key=f"ebn_{pid}")
                else:
                    edit_bonus = None

                e_sub = st.form_submit_button("💾 บันทึกการแก้ไข")

            if e_sub:
                try:
                    update_data = {
                        "name": edit_name,
                        "code": edit_code or None,
                        "priority": edit_priority,
                        "display.banner_text": edit_banner,
                        "display.banner_color": edit_color,
                        "conditions.min_topup_baht": edit_min_topup if edit_min_topup > 0 else None,
                        "updated_at": datetime.now(timezone.utc),
                    }
                    if edit_bonus is not None:
                        update_data["reward.bonus_credits"] = edit_bonus
                    promotions_ref().document(pid).update(update_data)
                    st.success(f"✅ แก้ไข '{edit_name}' แล้ว")
                    st.session_state.pop(f"editing_{pid}", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"ล้มเหลว: {e}")

            if st.button("ยกเลิกแก้ไข", key=f"cancel_edit_{pid}"):
                st.session_state.pop(f"editing_{pid}", None)
                st.rerun()

        # Redemption log
        with st.expander("📊 ประวัติการใช้โปร"):
            try:
                rdocs = list(
                    promo_redemptions_ref()
                    .where("promo_id", "==", pid)
                    .limit(50)
                    .stream()
                )
                if rdocs:
                    r_data = []
                    for rd in rdocs:
                        r = rd.to_dict()
                        r_data.append({
                            "วันที่": format_date(r.get("created_at")),
                            "ผู้ใช้": r.get("user_id", "—")[:12],
                            "เติม (บาท)": r.get("topup_baht", 0),
                            "เครดิตปกติ": r.get("base_credits", 0),
                            "โบนัส": r.get("bonus_credits", 0),
                            "รวม": r.get("total_credits", 0),
                        })
                    st.dataframe(pd.DataFrame(r_data), use_container_width=True, hide_index=True)
                else:
                    st.info("ยังไม่มีประวัติการใช้โปร")
            except Exception as e:
                st.error(f"ไม่สามารถโหลดประวัติ: {e}")
