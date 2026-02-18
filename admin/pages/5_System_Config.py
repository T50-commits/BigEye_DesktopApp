"""
BigEye Pro Admin — หน้าตั้งค่าระบบ
เวอร์ชันแอป, อัตราเครดิต, การประมวลผล, โหมดปิดปรับปรุง, พรอมต์, คำต้องห้าม
"""
import streamlit as st
from utils.auth import require_auth
require_auth()

from datetime import datetime, timezone

from utils.firestore_client import system_config_ref
from utils.theme import inject_css

inject_css()
st.header("🔧 ตั้งค่าระบบ")


# ── Helpers ──

APP_SETTINGS_DOC = "app_settings"

def load_app_settings() -> dict:
    """Load the single app_settings document that backend uses."""
    try:
        doc = system_config_ref().document(APP_SETTINGS_DOC).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดค่าระบบ: {e}")
    return {}


def save_app_settings(data: dict):
    """Merge-update the single app_settings document."""
    data["updated_at"] = datetime.now(timezone.utc)
    system_config_ref().document(APP_SETTINGS_DOC).set(data, merge=True)


# Load once
_settings = load_app_settings()


# ═══════════════════════════════════════
# 1. App Version
# ═══════════════════════════════════════

st.subheader("📱 เวอร์ชันแอป")

with st.form("version_form"):
    col1, col2 = st.columns(2)
    with col1:
        latest_version = st.text_input(
            "เวอร์ชันล่าสุด",
            value=_settings.get("app_latest_version", "2.0.0"),
        )
        force_update_below = st.text_input(
            "บังคับอัพเดทต่ำกว่า",
            value=_settings.get("force_update_below", "1.9.0"),
        )
    with col2:
        download_url = st.text_input(
            "ลิงก์ดาวน์โหลด",
            value=_settings.get("app_download_url", ""),
        )
        release_notes = st.text_area(
            "บันทึกการอัพเดท",
            value=_settings.get("app_update_notes", ""),
            height=80,
        )

    if st.form_submit_button("💾 บันทึกเวอร์ชัน"):
        save_app_settings({
            "app_latest_version": latest_version,
            "force_update_below": force_update_below,
            "app_download_url": download_url,
            "app_update_notes": release_notes,
        })
        st.success("✅ บันทึกเวอร์ชันแล้ว")
        st.rerun()

st.divider()

# ═══════════════════════════════════════
# 2. Credit Rates (split by platform & type)
# ═══════════════════════════════════════

st.subheader("💰 อัตราเครดิต")

rates_config = _settings.get("credit_rates", {})

with st.form("rates_form"):
    st.markdown("**iStock**")
    col1, col2 = st.columns(2)
    with col1:
        istock_photo_rate = st.number_input(
            "iStock ภาพ (cr/ไฟล์)",
            value=rates_config.get("istock_photo", 3),
            min_value=1, step=1,
        )
    with col2:
        istock_video_rate = st.number_input(
            "iStock วิดีโอ (cr/ไฟล์)",
            value=rates_config.get("istock_video", 3),
            min_value=1, step=1,
        )

    st.markdown("**Adobe & Shutterstock**")
    col3, col4 = st.columns(2)
    with col3:
        adobe_ss_photo_rate = st.number_input(
            "Adobe & SS ภาพ (cr/ไฟล์)",
            value=rates_config.get("adobe_photo", 2),
            min_value=1, step=1,
        )
    with col4:
        adobe_ss_video_rate = st.number_input(
            "Adobe & SS วิดีโอ (cr/ไฟล์)",
            value=rates_config.get("adobe_video", 2),
            min_value=1, step=1,
        )

    st.markdown("**อัตราแลกเปลี่ยน**")
    exchange_rate = st.number_input(
        "1 บาท = ? เครดิต",
        value=_settings.get("exchange_rate", 4),
        min_value=1, step=1,
    )

    if st.form_submit_button("💾 บันทึกอัตราเครดิต"):
        save_app_settings({
            "credit_rates": {
                "istock_photo": istock_photo_rate,
                "istock_video": istock_video_rate,
                "adobe_photo": adobe_ss_photo_rate,
                "adobe_video": adobe_ss_video_rate,
                "shutterstock_photo": adobe_ss_photo_rate,
                "shutterstock_video": adobe_ss_video_rate,
            },
            "exchange_rate": exchange_rate,
        })
        st.success("✅ บันทึกอัตราเครดิตแล้ว")
        st.rerun()

st.divider()

# ═══════════════════════════════════════
# 2.5 Bank Account Info (for top-up display)
# ═══════════════════════════════════════

st.subheader("🏦 บัญชีธนาคารรับเงิน")
st.caption("ข้อมูลนี้จะแสดงในหน้าเติมเงินของแอป เพื่อให้ผู้ใช้โอนเงินมาถูกบัญชี")

bank_config = _settings.get("bank_info", {})

with st.form("bank_form"):
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        bank_name = st.text_input(
            "ชื่อธนาคาร",
            value=bank_config.get("bank_name", ""),
            placeholder="เช่น ธนาคารกสิกรไทย",
        )
        account_number = st.text_input(
            "เลขที่บัญชี",
            value=bank_config.get("account_number", ""),
            placeholder="เช่น 123-4-56789-0",
        )
    with b_col2:
        account_name = st.text_input(
            "ชื่อบัญชี",
            value=bank_config.get("account_name", ""),
            placeholder="เช่น นายสมชาย ใจดี",
        )

    if st.form_submit_button("💾 บันทึกข้อมูลธนาคาร"):
        save_app_settings({
            "bank_info": {
                "bank_name": bank_name.strip(),
                "account_number": account_number.strip(),
                "account_name": account_name.strip(),
            },
        })
        st.success("✅ บันทึกข้อมูลธนาคารแล้ว — จะแสดงในแอปทันที")
        st.rerun()

if bank_config.get("bank_name"):
    st.info(
        f"**ข้อมูลปัจจุบัน:** {bank_config.get('bank_name')}  "
        f"{bank_config.get('account_number', '—')}  "
        f"({bank_config.get('account_name', '—')})"
    )
else:
    st.warning("⚠️ ยังไม่ได้ตั้งค่าข้อมูลธนาคาร — ผู้ใช้จะเห็น 'ยังไม่ได้ตั้งค่า' ในหน้าเติมเงิน")

st.divider()

# ═══════════════════════════════════════
# 3. Processing Config
# ═══════════════════════════════════════

st.subheader("⚙️ การประมวลผล")

with st.form("proc_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        cache_threshold = st.number_input(
            "Context Cache (ไฟล์)",
            value=_settings.get("context_cache_threshold", 20),
            min_value=1, step=5,
        )
    with col2:
        max_images = st.number_input(
            "ภาพพร้อมกันสูงสุด",
            value=_settings.get("max_concurrent_images", 5),
            min_value=1, step=1,
        )
    with col3:
        max_videos = st.number_input(
            "วิดีโอพร้อมกันสูงสุด",
            value=_settings.get("max_concurrent_videos", 2),
            min_value=1, step=1,
        )

    if st.form_submit_button("💾 บันทึกค่าประมวลผล"):
        save_app_settings({
            "context_cache_threshold": cache_threshold,
            "max_concurrent_images": max_images,
            "max_concurrent_videos": max_videos,
        })
        st.success("✅ บันทึกค่าประมวลผลแล้ว")
        st.rerun()

st.divider()

# ═══════════════════════════════════════
# 4. Maintenance Mode
# ═══════════════════════════════════════

st.subheader("🚧 โหมดปิดปรับปรุง")

is_maintenance = _settings.get("maintenance_mode", False)

if is_maintenance:
    st.error(f"🔴 โหมดปิดปรับปรุง **เปิดอยู่** — ข้อความ: {_settings.get('maintenance_message', '')}")
else:
    st.success("🟢 โหมดปิดปรับปรุง **ปิดอยู่**")

maint_message = st.text_input(
    "ข้อความแจ้งผู้ใช้",
    value=_settings.get("maintenance_message", "ระบบกำลังปรับปรุง กรุณาลองใหม่ภายหลัง"),
)

col1, col2 = st.columns(2)
with col1:
    if not is_maintenance:
        if st.button("🔴 เปิดโหมดปิดปรับปรุง", type="primary"):
            save_app_settings({"maintenance_mode": True, "maintenance_message": maint_message})
            st.warning("เปิดโหมดปิดปรับปรุงแล้ว")
            st.rerun()
    else:
        if st.button("🟢 ปิดโหมดปิดปรับปรุง", type="primary"):
            save_app_settings({"maintenance_mode": False, "maintenance_message": maint_message})
            st.success("ปิดโหมดปิดปรับปรุงแล้ว")
            st.rerun()

st.divider()

# ═══════════════════════════════════════
# 5. Prompts
# ═══════════════════════════════════════

st.subheader("📝 พรอมต์")

prompts_config = _settings.get("prompts", {})

_PROMPT_LABELS = {
    "istock": "iStock (Dictionary-Strict)",
    "hybrid": "Hybrid Mode (Adobe/SS)",
    "single": "Single Words Mode",
}

if prompts_config:
    for key in ["istock", "hybrid", "single"]:
        val = prompts_config.get(key, "")
        if val:
            preview = val[:120].replace("\n", " ") + "..." if len(val) > 120 else val
            label = _PROMPT_LABELS.get(key, key)
            st.text_input(f"{label}", value=f"✅ {len(val):,} ตัวอักษร", disabled=True, key=f"prompt_{key}")
    # Show version info
    ver = _settings.get("prompts_version", "—")
    st.caption(f"เวอร์ชันพรอมต์: {ver}")
else:
    st.info("ยังไม่มีพรอมต์ที่ตั้งค่า — กรุณารัน upload_prompts.py ก่อน")

with st.expander("📤 อัพเดทพรอมต์"):
    prompt_key = st.selectbox("ประเภทพรอมต์", ["istock", "hybrid", "single"])
    # Show current prompt content
    current_prompt = prompts_config.get(prompt_key, "")
    if current_prompt:
        with st.container():
            st.caption(f"พรอมต์ปัจจุบัน ({len(current_prompt):,} ตัวอักษร):")
            st.text_area("พรอมต์ปัจจุบัน", value=current_prompt[:2000], height=150, disabled=True, key=f"current_{prompt_key}")
    prompt_text = st.text_area("ข้อความพรอมต์ใหม่ (จะเขียนทับของเดิม)", height=150, key=f"new_{prompt_key}")
    if st.button("อัพโหลดพรอมต์"):
        if prompt_text:
            updated_prompts = dict(prompts_config)
            updated_prompts[prompt_key] = prompt_text
            save_app_settings({"prompts": updated_prompts})
            st.success(f"✅ อัพเดทพรอมต์ '{prompt_key}' แล้ว")
            st.rerun()
        else:
            st.warning("กรุณากรอกข้อความพรอมต์")

st.divider()

# ═══════════════════════════════════════
# 6. Blacklist
# ═══════════════════════════════════════

st.subheader("🚫 คำต้องห้าม (Blacklist)")

terms = list(_settings.get("blacklist", []))

st.markdown(f"**ปัจจุบัน:** {len(terms)} คำ")

with st.expander("ดูคำทั้งหมด"):
    if terms:
        st.text_area("คำต้องห้าม", value="\n".join(sorted(terms)), height=200, disabled=True)
    else:
        st.info("ยังไม่มีคำต้องห้าม")

col1, col2 = st.columns(2)
with col1:
    new_term = st.text_input("เพิ่มคำ", placeholder="พิมพ์คำที่ต้องการเพิ่ม")
    if st.button("➕ เพิ่ม"):
        if new_term and new_term.strip():
            term = new_term.strip().lower()
            if term not in terms:
                terms.append(term)
                save_app_settings({"blacklist": terms})
                st.success(f"เพิ่มแล้ว: '{term}'")
                st.rerun()
            else:
                st.warning("คำนี้มีอยู่แล้ว")

with col2:
    remove_term = st.text_input("ลบคำ", placeholder="พิมพ์คำที่ต้องการลบ")
    if st.button("➖ ลบ"):
        if remove_term and remove_term.strip():
            term = remove_term.strip().lower()
            if term in terms:
                terms.remove(term)
                save_app_settings({"blacklist": terms})
                st.success(f"ลบแล้ว: '{term}'")
                st.rerun()
            else:
                st.warning("ไม่พบคำนี้")
