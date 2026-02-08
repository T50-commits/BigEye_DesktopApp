"""
BigEye Pro Admin — หน้าตั้งค่าระบบ
เวอร์ชันแอป, อัตราเครดิต, การประมวลผล, โหมดปิดปรับปรุง, พรอมต์, คำต้องห้าม
"""
import streamlit as st
from datetime import datetime, timezone

from utils.firestore_client import system_config_ref


st.header("🔧 ตั้งค่าระบบ")


# ── Helpers ──

def load_config(doc_id: str) -> dict:
    try:
        doc = system_config_ref().document(doc_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด {doc_id}: {e}")
    return {}


def save_config(doc_id: str, data: dict):
    data["updated_at"] = datetime.now(timezone.utc)
    system_config_ref().document(doc_id).set(data, merge=True)


# ═══════════════════════════════════════
# 1. App Version
# ═══════════════════════════════════════

st.subheader("📱 เวอร์ชันแอป")

version_config = load_config("app_version")

with st.form("version_form"):
    col1, col2 = st.columns(2)
    with col1:
        latest_version = st.text_input(
            "เวอร์ชันล่าสุด",
            value=version_config.get("latest_version", "2.0.0"),
        )
        force_update_below = st.text_input(
            "บังคับอัพเดทต่ำกว่า",
            value=version_config.get("force_update_below", "1.9.0"),
        )
    with col2:
        download_url = st.text_input(
            "ลิงก์ดาวน์โหลด",
            value=version_config.get("download_url", ""),
        )
        release_notes = st.text_area(
            "บันทึกการอัพเดท",
            value=version_config.get("release_notes", ""),
            height=80,
        )

    if st.form_submit_button("💾 บันทึกเวอร์ชัน"):
        save_config("app_version", {
            "latest_version": latest_version,
            "force_update_below": force_update_below,
            "download_url": download_url,
            "release_notes": release_notes,
        })
        st.success("✅ บันทึกเวอร์ชันแล้ว")

st.divider()

# ═══════════════════════════════════════
# 2. Credit Rates (split by platform & type)
# ═══════════════════════════════════════

st.subheader("💰 อัตราเครดิต")

rates_config = load_config("credit_rates")

with st.form("rates_form"):
    st.markdown("**iStock**")
    col1, col2 = st.columns(2)
    with col1:
        istock_photo_rate = st.number_input(
            "iStock ภาพ (cr/ไฟล์)",
            value=rates_config.get("istock_photo_rate", 3),
            min_value=1, step=1,
        )
    with col2:
        istock_video_rate = st.number_input(
            "iStock วิดีโอ (cr/ไฟล์)",
            value=rates_config.get("istock_video_rate", 5),
            min_value=1, step=1,
        )

    st.markdown("**Adobe & Shutterstock**")
    col3, col4 = st.columns(2)
    with col3:
        adobe_ss_photo_rate = st.number_input(
            "Adobe & SS ภาพ (cr/ไฟล์)",
            value=rates_config.get("adobe_ss_photo_rate", 2),
            min_value=1, step=1,
        )
    with col4:
        adobe_ss_video_rate = st.number_input(
            "Adobe & SS วิดีโอ (cr/ไฟล์)",
            value=rates_config.get("adobe_ss_video_rate", 4),
            min_value=1, step=1,
        )

    st.markdown("**อัตราแลกเปลี่ยน**")
    exchange_rate = st.number_input(
        "1 บาท = ? เครดิต",
        value=rates_config.get("exchange_rate", 4),
        min_value=1, step=1,
    )

    if st.form_submit_button("💾 บันทึกอัตราเครดิต"):
        save_config("credit_rates", {
            "istock_photo_rate": istock_photo_rate,
            "istock_video_rate": istock_video_rate,
            "adobe_ss_photo_rate": adobe_ss_photo_rate,
            "adobe_ss_video_rate": adobe_ss_video_rate,
            "exchange_rate": exchange_rate,
        })
        st.success("✅ บันทึกอัตราเครดิตแล้ว")

st.divider()

# ═══════════════════════════════════════
# 3. Processing Config
# ═══════════════════════════════════════

st.subheader("⚙️ การประมวลผล")

proc_config = load_config("processing")

with st.form("proc_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        cache_threshold = st.number_input(
            "Context Cache (ไฟล์)",
            value=proc_config.get("cache_threshold", 20),
            min_value=1, step=5,
        )
    with col2:
        max_images = st.number_input(
            "ภาพพร้อมกันสูงสุด",
            value=proc_config.get("max_concurrent_images", 5),
            min_value=1, step=1,
        )
    with col3:
        max_videos = st.number_input(
            "วิดีโอพร้อมกันสูงสุด",
            value=proc_config.get("max_concurrent_videos", 2),
            min_value=1, step=1,
        )

    if st.form_submit_button("💾 บันทึกค่าประมวลผล"):
        save_config("processing", {
            "cache_threshold": cache_threshold,
            "max_concurrent_images": max_images,
            "max_concurrent_videos": max_videos,
        })
        st.success("✅ บันทึกค่าประมวลผลแล้ว")

st.divider()

# ═══════════════════════════════════════
# 4. Maintenance Mode
# ═══════════════════════════════════════

st.subheader("🚧 โหมดปิดปรับปรุง")

maint_config = load_config("maintenance")
is_maintenance = maint_config.get("enabled", False)

if is_maintenance:
    st.error(f"🔴 โหมดปิดปรับปรุง **เปิดอยู่** — ข้อความ: {maint_config.get('message', '')}")
else:
    st.success("🟢 โหมดปิดปรับปรุง **ปิดอยู่**")

maint_message = st.text_input(
    "ข้อความแจ้งผู้ใช้",
    value=maint_config.get("message", "ระบบกำลังปรับปรุง กรุณาลองใหม่ภายหลัง"),
)

col1, col2 = st.columns(2)
with col1:
    if not is_maintenance:
        if st.button("🔴 เปิดโหมดปิดปรับปรุง", type="primary"):
            save_config("maintenance", {"enabled": True, "message": maint_message})
            st.warning("เปิดโหมดปิดปรับปรุงแล้ว")
            st.rerun()
    else:
        if st.button("🟢 ปิดโหมดปิดปรับปรุง", type="primary"):
            save_config("maintenance", {"enabled": False, "message": maint_message})
            st.success("ปิดโหมดปิดปรับปรุงแล้ว")
            st.rerun()

st.divider()

# ═══════════════════════════════════════
# 5. Prompts
# ═══════════════════════════════════════

st.subheader("📝 พรอมต์")

prompts_config = load_config("prompts")

if prompts_config:
    for key, val in prompts_config.items():
        if key == "updated_at":
            continue
        preview = str(val)[:100] + "..." if len(str(val)) > 100 else str(val)
        st.text_input(f"**{key}**", value=preview, disabled=True, key=f"prompt_{key}")
else:
    st.info("ยังไม่มีพรอมต์ที่ตั้งค่า")

with st.expander("📤 อัพเดทพรอมต์"):
    prompt_key = st.selectbox("ประเภทพรอมต์", ["istock", "hybrid", "single", "custom"])
    prompt_text = st.text_area("ข้อความพรอมต์ (จะถูกเข้ารหัสโดย backend)", height=150)
    if st.button("อัพโหลดพรอมต์"):
        if prompt_text:
            save_config("prompts", {prompt_key: prompt_text})
            st.success(f"✅ อัพเดทพรอมต์ '{prompt_key}' แล้ว")
            st.rerun()
        else:
            st.warning("กรุณากรอกข้อความพรอมต์")

st.divider()

# ═══════════════════════════════════════
# 6. Blacklist
# ═══════════════════════════════════════

st.subheader("🚫 คำต้องห้าม (Blacklist)")

blacklist_config = load_config("blacklist")
terms = blacklist_config.get("terms", [])

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
                save_config("blacklist", {"terms": terms})
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
                save_config("blacklist", {"terms": terms})
                st.success(f"ลบแล้ว: '{term}'")
                st.rerun()
            else:
                st.warning("ไม่พบคำนี้")
