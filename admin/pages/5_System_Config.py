"""
BigEye Pro Admin — System Configuration Page
App version, credit rates, processing config, maintenance mode, prompts, blacklist.
"""
import streamlit as st
from datetime import datetime

from utils.firestore_client import system_config_ref


st.header("🔧 System Configuration")


# ── Helpers ──

def load_config(doc_id: str) -> dict:
    """Load a system config document."""
    try:
        doc = system_config_ref().document(doc_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        st.error(f"Error loading {doc_id}: {e}")
    return {}


def save_config(doc_id: str, data: dict):
    """Save a system config document (merge)."""
    data["updated_at"] = datetime.utcnow()
    system_config_ref().document(doc_id).set(data, merge=True)


# ═══════════════════════════════════════
# 1. App Version
# ═══════════════════════════════════════

st.subheader("📱 App Version")

version_config = load_config("app_version")

with st.form("version_form"):
    col1, col2 = st.columns(2)
    with col1:
        latest_version = st.text_input(
            "Latest version",
            value=version_config.get("latest_version", "2.0.0"),
        )
        force_update_below = st.text_input(
            "Force update below",
            value=version_config.get("force_update_below", "1.9.0"),
        )
    with col2:
        download_url = st.text_input(
            "Download URL",
            value=version_config.get("download_url", ""),
        )
        release_notes = st.text_area(
            "Release notes",
            value=version_config.get("release_notes", ""),
            height=80,
        )

    if st.form_submit_button("💾 Save Version Config"):
        save_config("app_version", {
            "latest_version": latest_version,
            "force_update_below": force_update_below,
            "download_url": download_url,
            "release_notes": release_notes,
        })
        st.success("✅ Version config saved")

st.divider()

# ═══════════════════════════════════════
# 2. Credit Rates
# ═══════════════════════════════════════

st.subheader("💰 Credit Rates")

rates_config = load_config("credit_rates")

with st.form("rates_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        istock_rate = st.number_input(
            "iStock (cr/file)",
            value=rates_config.get("istock_rate", 3),
            min_value=1, step=1,
        )
    with col2:
        adobe_rate = st.number_input(
            "Adobe (cr/file)",
            value=rates_config.get("adobe_rate", 2),
            min_value=1, step=1,
        )
    with col3:
        shutterstock_rate = st.number_input(
            "Shutterstock (cr/file)",
            value=rates_config.get("shutterstock_rate", 2),
            min_value=1, step=1,
        )
    with col4:
        exchange_rate = st.number_input(
            "1 THB = ? credits",
            value=rates_config.get("exchange_rate", 4),
            min_value=1, step=1,
        )

    if st.form_submit_button("💾 Save Rates"):
        save_config("credit_rates", {
            "istock_rate": istock_rate,
            "adobe_rate": adobe_rate,
            "shutterstock_rate": shutterstock_rate,
            "exchange_rate": exchange_rate,
        })
        st.success("✅ Credit rates saved")

st.divider()

# ═══════════════════════════════════════
# 3. Processing Config
# ═══════════════════════════════════════

st.subheader("⚙️ Processing")

proc_config = load_config("processing")

with st.form("proc_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        cache_threshold = st.number_input(
            "Cache threshold (files)",
            value=proc_config.get("cache_threshold", 20),
            min_value=1, step=5,
        )
    with col2:
        max_images = st.number_input(
            "Max concurrent images",
            value=proc_config.get("max_concurrent_images", 5),
            min_value=1, step=1,
        )
    with col3:
        max_videos = st.number_input(
            "Max concurrent videos",
            value=proc_config.get("max_concurrent_videos", 2),
            min_value=1, step=1,
        )

    if st.form_submit_button("💾 Save Processing Config"):
        save_config("processing", {
            "cache_threshold": cache_threshold,
            "max_concurrent_images": max_images,
            "max_concurrent_videos": max_videos,
        })
        st.success("✅ Processing config saved")

st.divider()

# ═══════════════════════════════════════
# 4. Maintenance Mode
# ═══════════════════════════════════════

st.subheader("🚧 Maintenance Mode")

maint_config = load_config("maintenance")
is_maintenance = maint_config.get("enabled", False)

if is_maintenance:
    st.error(f"🔴 Maintenance mode is **ON** — Message: {maint_config.get('message', '')}")
else:
    st.success("🟢 Maintenance mode is **OFF**")

maint_message = st.text_input(
    "Maintenance message",
    value=maint_config.get("message", "System is under maintenance. Please try again later."),
)

col1, col2 = st.columns(2)
with col1:
    if not is_maintenance:
        if st.button("🔴 Enable Maintenance", type="primary"):
            save_config("maintenance", {"enabled": True, "message": maint_message})
            st.warning("Maintenance mode enabled")
            st.rerun()
    else:
        if st.button("🟢 Disable Maintenance", type="primary"):
            save_config("maintenance", {"enabled": False, "message": maint_message})
            st.success("Maintenance mode disabled")
            st.rerun()

st.divider()

# ═══════════════════════════════════════
# 5. Prompts (Encrypted — view only first 100 chars)
# ═══════════════════════════════════════

st.subheader("📝 Prompts")

prompts_config = load_config("prompts")

if prompts_config:
    for key, val in prompts_config.items():
        if key == "updated_at":
            continue
        preview = str(val)[:100] + "..." if len(str(val)) > 100 else str(val)
        st.text_input(f"**{key}**", value=preview, disabled=True, key=f"prompt_{key}")
else:
    st.info("No prompts configured yet.")

with st.expander("📤 Update Prompts"):
    prompt_key = st.selectbox("Prompt key", ["istock", "hybrid", "single", "custom"])
    prompt_text = st.text_area("Prompt text (will be encrypted by backend)", height=150)
    if st.button("Upload Prompt"):
        if prompt_text:
            save_config("prompts", {prompt_key: prompt_text})
            st.success(f"✅ Prompt '{prompt_key}' updated")
            st.rerun()
        else:
            st.warning("Please enter prompt text")

st.divider()

# ═══════════════════════════════════════
# 6. Blacklist
# ═══════════════════════════════════════

st.subheader("🚫 Blacklist")

blacklist_config = load_config("blacklist")
terms = blacklist_config.get("terms", [])

st.markdown(f"**Current:** {len(terms)} terms")

with st.expander("View All Terms"):
    if terms:
        st.text_area("Blacklisted terms", value="\n".join(sorted(terms)), height=200, disabled=True)
    else:
        st.info("No blacklisted terms.")

col1, col2 = st.columns(2)
with col1:
    new_term = st.text_input("Add term", placeholder="Enter term to blacklist")
    if st.button("➕ Add"):
        if new_term and new_term.strip():
            term = new_term.strip().lower()
            if term not in terms:
                terms.append(term)
                save_config("blacklist", {"terms": terms})
                st.success(f"Added: '{term}'")
                st.rerun()
            else:
                st.warning("Term already exists")

with col2:
    remove_term = st.text_input("Remove term", placeholder="Enter term to remove")
    if st.button("➖ Remove"):
        if remove_term and remove_term.strip():
            term = remove_term.strip().lower()
            if term in terms:
                terms.remove(term)
                save_config("blacklist", {"terms": terms})
                st.success(f"Removed: '{term}'")
                st.rerun()
            else:
                st.warning("Term not found")
