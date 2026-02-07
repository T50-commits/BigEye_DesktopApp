import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import pandas as pd
import time
import json
import os
import shutil
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import config  # ต้องมีไฟล์ config.py อยู่ในโฟลเดอร์เดียวกัน
import platform
import sys
import tkinter as tk
from tkinter import filedialog
import logging
import gc
import nltk
import tempfile
import atexit
from nltk.stem import SnowballStemmer
import base64
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Proxy files tracking for cleanup
_PROXY_FILES = set()
_PROXY_TEMP_DIR = None

def _cleanup_proxy_files():
    """ลบไฟล์ proxy ทั้งหมดเมื่อปิดโปรแกรม"""
    global _PROXY_FILES, _PROXY_TEMP_DIR
    for proxy_path in list(_PROXY_FILES):
        try:
            if os.path.exists(proxy_path):
                os.remove(proxy_path)
                logging.info(f"Cleanup: removed proxy {proxy_path}")
        except Exception as e:
            logging.warning(f"Cleanup failed for {proxy_path}: {e}")
    _PROXY_FILES.clear()
    
    # ลบโฟลเดอร์ temp ถ้ามี
    if _PROXY_TEMP_DIR and os.path.exists(_PROXY_TEMP_DIR):
        try:
            shutil.rmtree(_PROXY_TEMP_DIR)
            logging.info(f"Cleanup: removed temp dir {_PROXY_TEMP_DIR}")
        except Exception as e:
            logging.warning(f"Cleanup temp dir failed: {e}")

# ลงทะเบียน cleanup function
atexit.register(_cleanup_proxy_files)

# API Key Storage (Encrypted)
API_KEY_FILE = os.path.join(BASE_DIR, "api_key.enc")

def load_database() -> str:
    """
    โหลด Keyword Dictionary จาก Server (RAM only)
    ไม่มี local fallback - ต้องมี internet connection
    """
    server_config = st.session_state.get('server_config', {})
    if server_config and server_config.get('dictionary'):
        return server_config['dictionary']
    
    logging.warning("Dictionary not available - server_config is empty")
    return ""

# ==========================================
# API KEY FUNCTIONS (Protected in compiled module)
# ==========================================
from license.validator_api import load_api_key as _load_api_key
from license.validator_api import save_api_key as _save_api_key
from license.validator_api import clear_api_key as _clear_api_key

def load_api_key() -> str:
    """โหลด API Key (ถอดรหัสอัตโนมัติ)"""
    return _load_api_key(BASE_DIR)

def save_api_key(api_key: str) -> bool:
    """บันทึก API Key (เข้ารหัสอัตโนมัติ)"""
    return _save_api_key(BASE_DIR, api_key)

def clear_api_key() -> bool:
    """ลบ API Key"""
    return _clear_api_key(BASE_DIR)


# ==========================================
# SERVER CONFIG HELPERS (Prompts from Google Apps Script)
# ==========================================
def get_server_prompt(prompt_key: str) -> str:
    """
    ดึง prompt จาก server_config (RAM only)
    prompt_key: 'prompt_istock', 'prompt_hybrid', 'prompt_single'
    Returns: prompt string หรือ empty string ถ้าไม่พบ
    """
    server_config = st.session_state.get('server_config', {})
    if server_config:
        return server_config.get(prompt_key, '')
    return ''

def get_server_dictionary() -> str:
    """ดึง keyword dictionary จาก server_config (RAM only)"""
    server_config = st.session_state.get('server_config', {})
    if server_config:
        return server_config.get('dictionary', '')
    return ''

def is_server_config_loaded() -> bool:
    """ตรวจสอบว่าโหลด server config แล้วหรือยัง"""
    server_config = st.session_state.get('server_config', {})
    return bool(server_config and server_config.get('prompt_istock'))


# เช็คและโหลดข้อมูล NLTK อัตโนมัติ (กัน Error)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except Exception as e:
        logging.warning(f"Cannot download NLTK data: {e}")
        st.warning("⚠️ Cannot download NLTK data - some features may not work")

# ตั้งค่าให้บันทึก Error ลงไฟล์ debug_log.txt
logging.basicConfig(
    filename='debug_log.txt',
    filemode='a',  # 'a' = append (เขียนต่อท้าย ไม่ลบของเก่า)
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
    force=True,
    encoding='utf-8' # รองรับภาษาไทย
)

logging.info("=== Program Started (Session New) ===")
# --- [END] LOGGING SETUP ---

# ==========================================
# LICENSE CHECK (ต้องผ่านก่อนถึงจะใช้งานได้)
# ==========================================
from license.validator_api import check_license
if not check_license(st, logging):
    st.stop()

# ==========================================
# 1. CONFIGURATION & CSS
# ==========================================
st.set_page_config(
    page_title="BigEye",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700;900&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Sarabun', sans-serif;
    }}

    .main-header {{
        font-size: 3.5rem;
        font-weight: 900;
        background: -webkit-linear-gradient(45deg, {config.THEME_COLOR_1}, {config.THEME_COLOR_2});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 20px;
    }}
    .dev-credit {{
        font-size: 1rem; color: {config.THEME_COLOR_2}; text-align: center;
        font-weight: 400; letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 30px; opacity: 0.8;
    }}

    /* Radio Button Styling - ยืดเต็มความกว้าง Sidebar */
    section[data-testid="stSidebar"] div[data-testid="stRadio"],
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > div,
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        width: 100% !important;
        max-width: 100% !important;
    }}
    div[role="radiogroup"] {{
        display: flex !important;
        flex-direction: column !important;
        gap: 10px !important;
        width: 100% !important;
        margin-bottom: 15px !important;
    }}
    div[role="radiogroup"] label > div:first-child {{
        display: none !important;
    }}
    div[role="radiogroup"] label {{
        justify-content: center !important;
        text-align: center !important;
        background-color: white !important;
        border: 2px solid #e0e0e0 !important;
        border-radius: 10px !important;
        padding: 12px 15px !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        margin: 0 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }}
    div[role="radiogroup"] label:hover {{
        border-color: {config.THEME_COLOR_1} !important;
        transform: translateY(-2px);
    }}
    div[role="radiogroup"] label:has(input:checked) {{
        background: linear-gradient(90deg, {config.THEME_COLOR_1} 0%, {config.THEME_COLOR_2} 100%) !important;
        border: 2px solid transparent !important;
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(51, 51, 255, 0.3) !important;
    }}
    div[role="radiogroup"] label:has(input:checked) * {{
        color: white !important;
        font-weight: 700 !important;
    }}

    /* Save & Clear Buttons */
    button[kind="primary"], button[kind="secondary"] {{
        height: 50px !important;
        padding: 0 20px !important;
        width: 100% !important;
        border-radius: 10px !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
        line-height: 1 !important;
    }}
    button[kind="primary"] {{
        background: linear-gradient(90deg, {config.THEME_COLOR_1} 0%, {config.THEME_COLOR_2} 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(51, 51, 255, 0.2);
    }}
    button[kind="primary"]:hover {{
        transform: scale(1.02);
        box-shadow: 0 6px 15px rgba(51, 51, 255, 0.4);
    }}
    button[kind="secondary"] {{
        background-color: white !important;
        color: {config.STOP_COLOR} !important;
        border: 2px solid {config.STOP_COLOR} !important;
        box-sizing: border-box !important; 
    }}
    button[kind="secondary"]:hover {{
        background-color: {config.STOP_COLOR} !important;
        color: white !important;
        border-color: {config.STOP_COLOR} !important;
        transform: scale(1.02);
        box-shadow: 0 4px 10px rgba(255, 75, 75, 0.3);
    }}

    .success-box {{
        padding: 1rem; border-radius: 10px; background-color: #f0f7ff;
        border: 1px solid {config.THEME_COLOR_2}; color: {config.THEME_COLOR_2};
        text-align: center; margin-top: 15px;
    }}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CORE FUNCTIONS
# ==========================================

def cleanup_orphaned_files(api_key):
    if not api_key: return
    # Prevent multiple cleanup runs in same session
    if 'cleanup_done' in st.session_state and st.session_state['cleanup_done']:
        return
    try:
        genai.configure(api_key=api_key)
        deleted_count = 0
        now = datetime.now(timezone.utc)
        for f in genai.list_files():
            try:
                if f.create_time and (now - f.create_time > timedelta(hours=1)):
                    f.delete()
                    deleted_count += 1
            except:
                pass
        if deleted_count > 0:
            st.toast(f"🧹 Auto-Cleanup: {deleted_count} files", icon="✨")
    except:
        pass

    try:
        from google.generativeai import caching
        # วนลูปหา Cache ทั้งหมดในระบบ
        for c in caching.CachedContent.list():
            # เช็คชื่อว่าเป็น Cache ของโปรแกรมเราไหม (ป้องกันไปลบของโปรแกรมอื่น)
            if hasattr(c, 'display_name') and c.display_name == "istock_db_cache":
                try:
                    c.delete()
                    print(f"🧹 Auto-Cleaned Orphaned Cache: {c.name}")
                except Exception as e:
                    print(f"Failed to delete cache {c.name}: {e}")
    except ImportError:
        print("Google Generative AI caching not available")
    except Exception as e:
        print(f"Cache Cleanup Error: {e}")


def organize_output_files(source_folder, results, platform_name, filename_suffix, keyword_style=None):
    """
    จัดระเบียบไฟล์หลังประมวลผลเสร็จ:
    1. สร้างโฟลเดอร์ 'Completed_[platform]_[style]_[timestamp]'
    2. Copy ไฟล์ที่ทำสำเร็จเข้าโฟลเดอร์ใหม่
    3. สร้างไฟล์ error_report.txt สำหรับไฟล์ที่มีปัญหา
    
    Returns: (completed_folder_path, error_count, success_count)
    """
    from datetime import datetime
    
    # แยกผลลัพธ์เป็น success และ error
    success_files = [r for r in results if 'error' not in r]
    error_files = [r for r in results if 'error' in r]
    
    # สร้างชื่อโฟลเดอร์ใหม่ (รวม keyword_style ถ้ามี)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_platform = platform_name.replace(' ', '_').replace('&', 'and').replace('(', '').replace(')', '')
    
    # เพิ่ม keyword_style ในชื่อโฟลเดอร์ (สำหรับ Adobe & Shutterstock)
    if keyword_style:
        clean_style = keyword_style.replace(' ', '_').replace('&', 'and').replace('(', '').replace(')', '')
        completed_folder_name = f"Completed_{clean_platform}_{clean_style}_{timestamp}"
    else:
        completed_folder_name = f"Completed_{clean_platform}_{timestamp}"
    completed_folder_path = os.path.join(source_folder, completed_folder_name)
    
    # สร้างโฟลเดอร์
    try:
        os.makedirs(completed_folder_path, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create completed folder: {e}")
        return None, len(error_files), len(success_files)
    
    # Copy ไฟล์ที่ทำสำเร็จเข้าโฟลเดอร์ใหม่
    copied_count = 0
    for result in success_files:
        filename = result.get('file_name', '')
        if filename:
            source_path = os.path.join(source_folder, filename)
            dest_path = os.path.join(completed_folder_path, filename)
            
            try:
                if os.path.exists(source_path):
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
            except Exception as e:
                logging.error(f"Failed to copy {filename}: {e}")
    
    # ย้ายไฟล์ CSV ที่สร้างไว้เข้าโฟลเดอร์ด้วย
    for csv_file in os.listdir(source_folder):
        if csv_file.startswith("Metadata") and csv_file.endswith(".csv") and filename_suffix in csv_file:
            try:
                src_csv = os.path.join(source_folder, csv_file)
                dst_csv = os.path.join(completed_folder_path, csv_file)
                shutil.move(src_csv, dst_csv)
            except Exception as e:
                logging.error(f"Failed to move CSV {csv_file}: {e}")
    
    # สร้าง Error Report (ถ้ามีไฟล์ที่ Error)
    if error_files:
        error_report_path = os.path.join(completed_folder_path, f"error_report_{timestamp}.txt")
        try:
            with open(error_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("           📋 ERROR REPORT - รายงานข้อผิดพลาด\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"🎯 Platform: {platform_name}\n")
                f.write(f"📊 Total Files Processed: {len(results)}\n")
                f.write(f"✅ Success: {len(success_files)}\n")
                f.write(f"❌ Errors: {len(error_files)}\n")
                f.write("\n" + "=" * 60 + "\n")
                f.write("                    📝 ERROR DETAILS\n")
                f.write("=" * 60 + "\n\n")
                
                # จัดกลุ่ม Error ตามประเภท
                error_by_type = {}
                for err in error_files:
                    err_type = err.get('error_type', 'UNKNOWN')
                    if err_type not in error_by_type:
                        error_by_type[err_type] = []
                    error_by_type[err_type].append(err)
                
                # แสดง Error แยกตามประเภท
                for err_type, errors in error_by_type.items():
                    f.write(f"\n🔴 [{err_type}] - {len(errors)} ไฟล์\n")
                    f.write("-" * 50 + "\n")
                    
                    for i, err in enumerate(errors, 1):
                        f.write(f"   {i}. {err.get('file_name', 'Unknown')}\n")
                        f.write(f"      └─ {err.get('error', 'Unknown error')}\n")
                        
                        # แสดง raw error ถ้ามี
                        if err.get('error_raw'):
                            f.write(f"      └─ [RAW] {err.get('error_raw')[:200]}...\n")
                        f.write("\n")
                
                # เพิ่มคำแนะนำการแก้ไข
                f.write("\n" + "=" * 60 + "\n")
                f.write("              💡 คำแนะนำการแก้ไขปัญหา\n")
                f.write("=" * 60 + "\n\n")
                
                recommendations = {
                    "API_QUOTA_EXCEEDED": "• รอ 1-2 นาทีแล้วลองใหม่\n• ใช้ API Key อื่น\n• ลดจำนวน Parallel Threads",
                    "RATE_LIMIT": "• ลด Parallel Threads ลงเหลือ 1-2\n• รอ 30 วินาทีแล้วลองใหม่",
                    "TIMEOUT": "• ลองใช้ไฟล์ที่มีขนาดเล็กลง\n• ตรวจสอบการเชื่อมต่อ Internet\n• สำหรับ Video ลองใช้ Proxy",
                    "PERMISSION_DENIED": "• ตรวจสอบว่า API Key ถูกต้อง\n• ตรวจสอบว่า API เปิดใช้งานแล้ว",
                    "INVALID_API_KEY": "• ตรวจสอบ API Key ใหม่\n• สร้าง API Key ใหม่จาก Google AI Studio",
                    "JSON_PARSE_ERROR": "• ลองใช้ Model อื่น (เช่น gemini-2.0-flash)\n• ลองประมวลผลไฟล์นี้แยกต่างหาก",
                    "CONTENT_BLOCKED": "• เนื้อหาอาจไม่เหมาะสม\n• ลองใช้ภาพ/วิดีโออื่น",
                    "NETWORK_ERROR": "• ตรวจสอบการเชื่อมต่อ Internet\n• ลองใหม่อีกครั้ง"
                }
                
                for err_type in error_by_type.keys():
                    if err_type in recommendations:
                        f.write(f"🔧 {err_type}:\n{recommendations[err_type]}\n\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write("📖 TIP: ดู debug_log.txt สำหรับรายละเอียดทางเทคนิคเพิ่มเติม\n")
                f.write("=" * 60 + "\n")
        except Exception as e:
            logging.error(f"Failed to create error report: {e}")
    else:
        # สร้าง Success Report เมื่อทำงานสำเร็จทั้งหมด
        success_report_path = os.path.join(completed_folder_path, f"success_report_{timestamp}.txt")
        try:
            with open(success_report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("      🎉 SUCCESS REPORT - ทำงานสำเร็จสมบูรณ์แบบ!\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"🎯 Platform: {platform_name}\n")
                f.write(f"📊 Total Files Processed: {len(results)}\n")
                f.write(f"✅ All Success: {len(success_files)} ไฟล์\n")
                f.write(f"❌ Errors: 0 ไฟล์\n\n")
                f.write("=" * 60 + "\n")
                f.write("              ✨ รายการไฟล์ที่ทำสำเร็จ\n")
                f.write("=" * 60 + "\n\n")
                
                for i, result in enumerate(success_files, 1):
                    filename = result.get('file_name', 'Unknown')
                    f.write(f"   {i}. ✅ {filename}\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write("   🎊 ยินดีด้วย! งานทั้งหมดเสร็จสมบูรณ์ไม่มีข้อผิดพลาด\n")
                f.write("=" * 60 + "\n")
        except Exception as e:
            logging.error(f"Failed to create success report: {e}")
    
    return completed_folder_path, len(error_files), len(success_files)


def select_folder_mac():
    try:
        script = '''
        tell application "System Events"
            activate
            set f to choose folder with prompt "Select Folder (เลือกโฟลเดอร์)"
            return POSIX path of f
        end tell
        '''
        proc = subprocess.run(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0:
            return proc.stdout.strip()
        else:
            return None
    except Exception as e:
        st.error(f"Mac Finder Error: {e}")
        return None


def get_dynamic_timeout(file_path, base_timeout):
    """Calculate timeout based on file size to handle different file sizes efficiently"""
    try:
        size_mb = os.path.getsize(file_path) / (1024*1024)
        # Add 10% more timeout per 10MB, max 2x base timeout
        multiplier = min(1 + (size_mb / 100), 2.0)
        return int(base_timeout * multiplier)
    except:
        return base_timeout


def enforce_istock_timecode(tc_str):
    """
    แปลง Timecode ใดๆ ให้เป็น format HH:MM:SS:FF เสมอ
    Input: "00:05", "0:05", "00:00:05", "5s"
    Output: "00:00:05:00"
    """
    if not tc_str or not isinstance(tc_str, str):
        return "00:00:00:00"

    # ลบตัวอักษรขยะและเปลี่ยน . เป็น :
    clean_tc = tc_str.strip().replace(".", ":").replace("s", "")
    parts = clean_tc.split(":")

    # กรณี: มาแค่ MM:SS (เช่น 00:05) -> เติม HH=00, FF=00
    if len(parts) == 2:
        return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"

    # กรณี: มา HH:MM:SS (เช่น 00:00:05) -> เติม FF=00
    elif len(parts) == 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}:00"

    # กรณี: มาครบ HH:MM:SS:FF แล้ว (เช็คความชัวร์เรื่องเลข 0 นำหน้า)
    elif len(parts) == 4:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}:{parts[3].zfill(2)}"

    return "00:00:00:00"  # กรณี Error ให้คืนค่า Default


def finalize_keywords_v5_ai_driven(keywords_list, target_count):
    """
    ARCHITECTURE V6: Smart Deduplication & Phrase Preservation
    - รักษาลำดับความสำคัญตามที่ AI ส่งมา (วลี -> คำเดี่ยว -> นามธรรม)
    - ใช้ Stemming เพื่อตัดคำซ้ำ (Woman/Women, Run/Running)
    - เก็บคำที่ดีที่สุด (สั้นที่สุด) สำหรับคำที่มีรากศัพท์เดียวกัน
    """

    # 1. SETUP TOOLS & BLACKLIST
    stemmer = SnowballStemmer("english")

    blacklist = {
        "filter", "presets", "instagram", "tiktok", "4k", "hd", "8k", "1080p",
        "macbook", "iphone", "samsung", "sony", "canon", "nikon",
        "facebook", "twitter", "youtube", "generated",
        "image", "photo", "picture", "shot", "concept", "view", "background",
        "of", "the", "a", "an", "with", "in", "on", "at", "by"
    }

    # Map คำกริยา/พหูพจน์ผิดปกติ ให้เป็นรากศัพท์เดียวกัน
    irregular_map = {
        "women": "woman", "men": "man", "children": "child",
        "people": "person", "feet": "foot", "teeth": "tooth",
        "mice": "mouse", "geese": "goose",
        "better": "good", "best": "good",
        "running": "run", "runner": "run", "runs": "run",
        "walking": "walk", "walked": "walk", "walks": "walk",
        "smiling": "smile", "smiled": "smile", "smiles": "smile",
        "working": "work", "worked": "work", "works": "work"
    }

    # --- PHASE 1: สร้าง Map เก็บคำที่ดีที่สุดสำหรับแต่ละ stem ---
    stem_best_word = {}  # {stem: best_word} - เก็บคำที่สั้นที่สุดสำหรับแต่ละ stem
    seen_phrases = set()  # เก็บวลีที่เจอแล้ว
    processed_keywords = []  # เก็บคำที่ผ่านการประมวลผลแล้ว

    for kw in keywords_list:
        # Clean text
        kw_clean = kw.lower().strip().strip(".").replace("-", " ")
        
        if not kw_clean or len(kw_clean) < 2 or kw_clean in blacklist:
            continue

        parts = kw_clean.split()

        # กรณี 1: เป็นคำเดี่ยว (Single Word)
        if len(parts) == 1:
            # จัดการคำผิดปกติ - แปลงเป็นคำที่ดีที่สุด
            if kw_clean in irregular_map:
                kw_clean = irregular_map[kw_clean]
            
            stem_val = stemmer.stem(kw_clean)
            
            # เช็คว่า stem นี้มีอยู่แล้วหรือยัง
            if stem_val in stem_best_word:
                # ถ้าคำใหม่สั้นกว่า ให้เก็บคำใหม่แทน
                if len(kw_clean) < len(stem_best_word[stem_val]):
                    stem_best_word[stem_val] = kw_clean
            else:
                stem_best_word[stem_val] = kw_clean
        
        # กรณี 2: เป็นวลี (Phrase)
        else:
            if kw_clean not in seen_phrases:
                seen_phrases.add(kw_clean)
                processed_keywords.append(("phrase", kw_clean))

    # เพิ่มคำเดี่ยวที่ดีที่สุดเข้าไป
    for stem, word in stem_best_word.items():
        processed_keywords.append(("single", word))

    # --- PHASE 2: รวมผลลัพธ์โดยรักษาลำดับ (วลีก่อน) ---
    final_result = []
    added_stems = set()  # เก็บ stem ที่เพิ่มแล้ว
    
    # เพิ่มวลีก่อน
    for kw_type, kw in processed_keywords:
        if kw_type == "phrase":
            final_result.append(kw.title())
            if len(final_result) >= target_count:
                break
    
    # เพิ่มคำเดี่ยว (ไม่ซ้ำ stem)
    if len(final_result) < target_count:
        for kw_type, kw in processed_keywords:
            if kw_type == "single":
                stem = stemmer.stem(kw)
                if stem not in added_stems:
                    final_result.append(kw.title())
                    added_stems.add(stem)
                    if len(final_result) >= target_count:
                        break

    return final_result


def explode_phrases(keywords_list, target_count=45):
    """
    Adobe Strategy (Enhanced with Stemming Deduplication):
    1. Keep original phrases first (High Priority)
    2. Explode phrases into single words (appended at the end)
    3. Use stemming to detect duplicates - keep the best (shortest) word
    
    Input: ["woman running", "morning jog", "runner"]
    Output: ["Woman Running", "Morning Jog", "Woman", "Running", "Morning", "Jog"]
    (Note: "runner" is removed because "running" shares the same stem and is shorter/better)
    """
    if not keywords_list: return []
    
    stemmer = SnowballStemmer("english")
    
    # Map คำกริยา/พหูพจน์ผิดปกติ
    irregular_map = {
        "women": "woman", "men": "man", "children": "child",
        "people": "person", "feet": "foot", "teeth": "tooth",
        "mice": "mouse", "geese": "goose"
    }
    
    # Blacklist คำที่ไม่ต้องการ
    blacklist = {"the", "and", "for", "a", "an", "of", "in", "on", "at", "to", "with", "by"}
    
    phrases = []  # วลีต้นฉบับ
    single_words = []  # คำเดี่ยวที่แตกออกมา
    stem_map = {}  # {stem: best_word} - เก็บคำที่ดีที่สุดสำหรับแต่ละ stem
    seen_phrases = set()  # เก็บวลีที่เจอแล้ว (case-insensitive)
    
    # --- PHASE 1: รวบรวมวลีต้นฉบับ ---
    for kw in keywords_list:
        clean = kw.strip().title()
        clean_lower = clean.lower()
        
        if clean and clean_lower not in seen_phrases:
            phrases.append(clean)
            seen_phrases.add(clean_lower)
    
    # --- PHASE 2: แตกวลีเป็นคำเดี่ยว พร้อมเช็ค Stem ---
    for kw in keywords_list:
        clean_for_split = kw.replace("-", " ").strip()
        parts = clean_for_split.split()
        
        if len(parts) > 1:  # แตกเฉพาะวลี (มากกว่า 1 คำ)
            for p in parts:
                p_clean = p.strip().title().strip(".,")
                p_lower = p_clean.lower()
                
                # กรองคำสั้นหรือ blacklist
                if len(p_clean) < 2 or p_lower in blacklist:
                    continue
                
                # จัดการคำผิดปกติ
                if p_lower in irregular_map:
                    p_clean = irregular_map[p_lower].title()
                    p_lower = p_clean.lower()
                
                # หา stem ของคำนี้
                stem = stemmer.stem(p_lower)
                
                # เช็คว่า stem นี้มีอยู่แล้วหรือไม่
                if stem in stem_map:
                    # ถ้ามีแล้ว เปรียบเทียบความยาว - เก็บคำที่สั้นกว่า (ดีกว่า)
                    existing_word = stem_map[stem]
                    if len(p_clean) < len(existing_word):
                        stem_map[stem] = p_clean
                else:
                    stem_map[stem] = p_clean
    
    # --- PHASE 3: รวมผลลัพธ์ (วลี + คำเดี่ยว) ---
    # เริ่มจากวลีต้นฉบับก่อน
    result = phrases.copy()
    seen_in_result = set(p.lower() for p in phrases)
    
    # เพิ่มคำเดี่ยวที่ไม่ซ้ำกับวลี
    for stem, word in stem_map.items():
        if word.lower() not in seen_in_result:
            result.append(word)
            seen_in_result.add(word.lower())
    
    return result


def filter_stems(keywords_list):
    """
    Shutterstock Strategy:
    Input: ["run", "running", "runner"]
    Output: ["run"] (Keep strongest/simplest, prevent spam)
    """
    if not keywords_list: return []
    
    stemmer = SnowballStemmer("english")
    stem_map = {} # {stem: shortest_word}
    
    for kw in keywords_list:
        clean = kw.strip().title()
        if not clean: continue
            
        stem = stemmer.stem(clean.lower())
        
        # Logic: If stem not seen, add it.
        # If seen, keep the shorter word? (e.g. run < running)
        if stem not in stem_map:
            stem_map[stem] = clean
        else:
            current_best = stem_map[stem]
            if len(clean) < len(current_best): # Prefer shorter word
                stem_map[stem] = clean
                
    return list(stem_map.values())


def create_proxies_for_videos(file_paths):
    proxy_map = {}
    video_files = [p for p in file_paths if os.path.basename(p).lower().endswith(config.VALID_VIDEO_EXT)]
    if not video_files:
        return proxy_map

    progress = st.progress(0, text="Creating proxies...")
    total = len(video_files)
    for i, fp in enumerate(video_files, 1):
        if st.session_state.get('stop_flag'):
            break
        filename = os.path.basename(fp)
        progress.progress((i - 1) / max(total, 1), text=f"Creating proxy ({i}/{total}): {filename}")
        proxy_path = create_proxy_video(fp)
        if proxy_path and os.path.exists(proxy_path):
            proxy_map[fp] = proxy_path
            logging.info(f"Proxy Created Successfully: {filename}")
        else:
            logging.warning(f"Proxy Creation Failed for {filename}, using original file.")
        progress.progress(i / max(total, 1), text=f"Creating proxy ({i}/{total}): {filename}")

    if st.session_state.get('stop_flag'):
        progress.progress(1.0, text="Proxy creation stopped")
    else:
        progress.progress(1.0, text="Proxy creation completed")

    return proxy_map


def process_single_file(model, file_path, platform_config, db_content, keyword_count_val, title_limit, desc_limit, upload_path_override=None, keyword_mode=None, server_config=None):
    """
    Process a single file with AI analysis.
    server_config: dict containing prompts - passed directly because st.session_state is not accessible in worker threads
    """
    filename = os.path.basename(file_path)
    is_video = filename.lower().endswith(config.VALID_VIDEO_EXT)
    media_type_str = "VIDEO FOOTAGE" if is_video else "STILL PHOTO"
    video_instr = config.VIDEO_INSTRUCTION_TEXT if is_video else ""

    if platform_config["requires_db"]:
        keyword_input = db_content
    else:
        keyword_input = platform_config.get("keyword_placeholder_text", "")

    # --- SELECT PROMPT BASED ON MODE (From Server Config passed as parameter) ---
    # Note: st.session_state is NOT accessible in worker threads, so we use server_config parameter
    if not server_config:
        logging.error("CRITICAL: server_config is None! Cannot process without prompts.")
        return {"file_name": filename, "error": "Server config not available"}
    
    if platform_config.get('has_keyword_mode') and keyword_mode:
        # Adobe & Shutterstock mode - เลือก prompt ตาม keyword_mode
        if keyword_mode == "Single Words":
            prompt_template = server_config.get('prompt_single', '')
            prompt_key_used = 'prompt_single'
        else:  # HYBRID (Phrase & Single Words)
            prompt_template = server_config.get('prompt_hybrid', '')
            prompt_key_used = 'prompt_hybrid'
        
        # Debug: ตรวจสอบว่า prompt โหลดมาหรือไม่
        if not prompt_template:
            logging.error(f"CRITICAL: {prompt_key_used} is empty in server_config!")
            logging.error(f"server_config keys: {list(server_config.keys())}")
            return {"file_name": filename, "error": f"Prompt {prompt_key_used} not available"}
        
        # คำนวณ min_limit (75% ของ max_limit)
        title_min = int(title_limit * 0.75)
        desc_min = int(desc_limit * 0.75)
        
        # ขอ keywords เพิ่ม 10 คำ เพื่อให้แน่ใจว่าได้ครบตามต้องการ (แล้วค่อย trim ทีหลัง)
        keyword_request_count = keyword_count_val + 10
        
        prompt = prompt_template.format(
            media_type_str=media_type_str,
            video_instruction=video_instr,
            keyword_count=keyword_request_count,
            title_limit=title_limit,
            title_min=title_min,
            desc_limit=desc_limit,
            desc_min=desc_min
        )
    else:
        # iStock mode - ใช้ prompt จาก server_config parameter
        prompt_template = server_config.get('prompt_istock', '')
        
        # Debug: ตรวจสอบว่า prompt โหลดมาหรือไม่
        if not prompt_template:
            logging.error("CRITICAL: prompt_istock is empty in server_config!")
            logging.error(f"server_config keys: {list(server_config.keys())}")
            return {"file_name": filename, "error": "Prompt istock not available"}
        
        # คำนวณ title_min (75% ของ title_limit) สำหรับ iStock prompt
        title_min = int(title_limit * 0.75)
        
        prompt = prompt_template.format(
            media_type_str=media_type_str,
            video_instruction=video_instr,
            keyword_data=keyword_input,
            keyword_count=keyword_count_val + 15,  # ขอเพิ่ม 15 คำเพื่อให้แน่ใจว่าได้ครบ
            title_limit=title_limit,
            title_min=title_min,
            desc_limit=desc_limit
        )

    request_timeout = get_dynamic_timeout(file_path, config.TIMEOUT_VIDEO if is_video else config.TIMEOUT_PHOTO)
    uploaded_file = None

    try:
        upload_path = upload_path_override or file_path

        for attempt in range(config.MAX_RETRIES):
            try:
                uploaded_file = genai.upload_file(upload_path)

                start_wait = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(5)
                    uploaded_file = genai.get_file(uploaded_file.name)
                    if time.time() - start_wait >= 300:
                        return {"file_name": filename, "error": "Timeout"}

                if uploaded_file.state.name == "FAILED":
                    return {"file_name": filename, "error": "Upload Failed"}

                response = model.generate_content(
                    [uploaded_file, prompt],
                    request_options={'timeout': request_timeout},
                    safety_settings={HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE}
                )

                text_resp = response.text
                json_str = ""
                match = re.search(r'```json\s*(\{.*?\})\s*```', text_resp, re.DOTALL)

                if match:
                    # กรณีมี Backticks ครอบ (เอาเนื้อใน group 1)
                    json_str = match.group(1)
                else:
                    # กรณีไม่มี Backticks (หาปีกกาเปิดปิด แล้วเอาทั้งก้อน group 0)
                    match = re.search(r'\{.*\}', text_resp, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                    else:
                        # กรณีหาไม่เจอเลย ให้ลอง Clean text ดิบๆ ดู
                        json_str = text_resp.replace("```json", "").replace("```", "").strip()

                # แปลง String เป็น JSON
                data = json.loads(json_str)
                data['file_name'] = filename
                try:
                    # แปลง string เป็น list ก่อนเสมอ
                    if "keywords" in data and isinstance(data["keywords"], str):
                        data["keywords"] = [k.strip() for k in data["keywords"].split(",")]

                    # --- ADOBE & SHUTTERSTOCK MODE (NEW) ---
                    if platform_config.get('has_keyword_mode') and keyword_mode:
                        # โหมดใหม่: AI ส่ง keywords รวมมาใน data["keywords"]
                        raw_kw = data.get("keywords", [])
                        if isinstance(raw_kw, str):
                            raw_kw = [k.strip() for k in raw_kw.split(",")]
                        
                        # ใช้ finalize_keywords_v5_ai_driven เพื่อ stemming deduplication
                        processed_kw = finalize_keywords_v5_ai_driven(raw_kw, keyword_count_val)
                        data["keywords"] = processed_kw[:keyword_count_val]
                        
                        # เก็บ title และ description ไว้ใช้งาน
                        # (AI ส่งมาใน data["title"] และ data["description"] โดยตรง)

                    elif not platform_config["requires_db"]:
                        # Fallback สำหรับโหมดอื่นที่ไม่ใช้ DB
                        data["keywords"] = finalize_keywords_v5_ai_driven(
                            data.get("keywords", []),
                            keyword_count_val
                        )

                    else:
                        # --- ส่วนของ iStock ปล่อยไว้เหมือนเดิม ---
                        raw_kw = data.get("keywords", [])
                        cleaned_istock = []
                        for k in raw_kw:
                            k_clean = k.strip().strip(".")
                            if k_clean and len(k_clean) > 1:
                                cleaned_istock.append(k_clean)

                        data["keywords"] = cleaned_istock[:keyword_count_val]

                except Exception as e:
                    logging.error(f"Error filtering keywords for {filename}: {e}")
                # -------------------------------------------------------
                try:
                    if hasattr(response, 'usage_metadata') and response.usage_metadata:
                        data['token_input'] = response.usage_metadata.prompt_token_count
                        data['token_output'] = response.usage_metadata.candidates_token_count
                        data['token_total'] = response.usage_metadata.total_token_count
                    else:
                        data['token_input'] = 0
                        data['token_output'] = 0
                        data['token_total'] = 0
                except Exception:
                    data['token_input'] = 0
                    data['token_output'] = 0
                    data['token_total'] = 0
                return data


            except Exception as e:
                # ถ้ายัง Retry ได้ ให้รอแล้วลองใหม่
                if attempt < config.MAX_RETRIES - 1:
                    logging.warning(f"Retry {attempt + 1}/{config.MAX_RETRIES} for {filename} due to: {e}")
                    time.sleep(config.WAIT_TIME_RETRY * (attempt + 1))
                    continue
                
                # --- ENHANCED ERROR CLASSIFICATION ---
                error_str = str(e).lower()
                error_type = "UNKNOWN_ERROR"
                error_detail = str(e)
                
                # ตรวจจับประเภท Error เฉพาะ
                if "quota" in error_str or "resource exhausted" in error_str:
                    error_type = "API_QUOTA_EXCEEDED"
                    error_detail = "API Quota เต็ม - รอสักครู่หรือเปลี่ยน API Key"
                elif "rate limit" in error_str or "429" in error_str:
                    error_type = "RATE_LIMIT"
                    error_detail = "ส่งคำขอเร็วเกินไป - ลองลด Parallel Threads"
                elif "timeout" in error_str or "deadline" in error_str:
                    error_type = "TIMEOUT"
                    error_detail = "หมดเวลารอ - ไฟล์อาจใหญ่เกินไปหรือ Network ช้า"
                elif "permission" in error_str or "403" in error_str:
                    error_type = "PERMISSION_DENIED"
                    error_detail = "ไม่มีสิทธิ์ - ตรวจสอบ API Key"
                elif "invalid" in error_str and "api" in error_str:
                    error_type = "INVALID_API_KEY"
                    error_detail = "API Key ไม่ถูกต้อง"
                elif "not found" in error_str or "404" in error_str:
                    error_type = "NOT_FOUND"
                    error_detail = "ไม่พบไฟล์หรือ Model"
                elif "json" in error_str or "parse" in error_str:
                    error_type = "JSON_PARSE_ERROR"
                    error_detail = "AI ตอบกลับในรูปแบบที่ไม่ถูกต้อง"
                elif "safety" in error_str or "blocked" in error_str:
                    error_type = "CONTENT_BLOCKED"
                    error_detail = "เนื้อหาถูกบล็อกโดย Safety Filter"
                elif "connection" in error_str or "network" in error_str:
                    error_type = "NETWORK_ERROR"
                    error_detail = "ปัญหาการเชื่อมต่อ Internet"
                
                # บันทึก Error เต็มรูปแบบลงไฟล์ debug_log.txt
                logging.error(f"[{error_type}] {filename}: {error_detail}", exc_info=True)
                
                # ส่งค่ากลับไปพร้อมรายละเอียด Error
                return {
                    "file_name": filename, 
                    "error": f"[{error_type}] {error_detail}",
                    "error_type": error_type,
                    "error_raw": str(e)[:500]  # เก็บ raw error ไว้ด้วย (ตัดไม่เกิน 500 ตัวอักษร)
                }

    finally:
        if uploaded_file:
            try:
                uploaded_file.delete()
            except Exception as e:
                logging.warning(f"Failed to delete uploaded file: {e}")
        
        # Memory cleanup after processing each file
        gc.collect()

def play_notification_sound():
    st.markdown(
        """<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg"></audio>""",
        unsafe_allow_html=True)


def create_proxy_video(input_path):
    """
    สร้างไฟล์วิดีโอขนาดเล็ก (Proxy) สำหรับส่งให้ AI
    - Resolution: 480p (Height)
    - Preset: Ultrafast (เน้นสร้างเร็ว ไม่เน้นสวย)
    - CRF: 28 (คุณภาพพอประมาณ ขนาดเล็กมาก)
    - สร้างใน temp directory เพื่อไม่ให้รกโฟลเดอร์ผู้ใช้
    """
    global _PROXY_FILES, _PROXY_TEMP_DIR
    try:
        filename = os.path.basename(input_path)
        
        # สร้าง temp directory ถ้ายังไม่มี
        if _PROXY_TEMP_DIR is None or not os.path.exists(_PROXY_TEMP_DIR):
            _PROXY_TEMP_DIR = tempfile.mkdtemp(prefix="bigeye_proxy_")
        
        # สร้างชื่อไฟล์ใน temp directory
        proxy_path = os.path.join(_PROXY_TEMP_DIR, f"proxy_{filename}")

        # ถ้ามีไฟล์ค้างอยู่ ลบก่อน
        if os.path.exists(proxy_path):
            os.remove(proxy_path)

        # คำสั่ง FFmpeg
        # scale=-2:480 หมายถึง ปรับความสูงเป็น 480p ความกว้างปรับตามสัดส่วน (หาร 2 ลงตัว)
        base_path = os.path.dirname(os.path.abspath(__file__))

        # เช็คว่าเป็น Windows, Mac หรือ Linux และเลือก FFmpeg ที่เหมาะสม
        ffmpeg_binary = None
        system = platform.system()
        machine = platform.machine()
        
        if system == "Windows":
            ffmpeg_path = os.path.join(base_path, "bin", "ffmpeg.exe")
            if os.path.exists(ffmpeg_path):
                ffmpeg_binary = ffmpeg_path
        elif system == "Darwin":  # macOS
            # ลองหา FFmpeg ตาม architecture
            if machine == "arm64":  # Apple Silicon (M1-M4)
                ffmpeg_path = os.path.join(base_path, "bin", "macos-arm64", "ffmpeg")
            else:  # Intel Mac
                ffmpeg_path = os.path.join(base_path, "bin", "macos-x64", "ffmpeg")
            
            if os.path.exists(ffmpeg_path):
                ffmpeg_binary = ffmpeg_path
            else:
                # Fallback: ลองหาใน bin/macos-arm64 (Intel Mac สามารถรันผ่าน Rosetta 2)
                fallback_path = os.path.join(base_path, "bin", "macos-arm64", "ffmpeg")
                if os.path.exists(fallback_path):
                    ffmpeg_binary = fallback_path
        elif system == "Linux":
            ffmpeg_path = os.path.join(base_path, "bin", "ffmpeg")
            if os.path.exists(ffmpeg_path):
                ffmpeg_binary = ffmpeg_path
        
        # ถ้าไม่เจอไฟล์ใน bin ให้ลองเรียกจาก system PATH
        if ffmpeg_binary is None:
            ffmpeg_binary = "ffmpeg"

        # 2. สร้างคำสั่ง cmd โดยใช้ path ที่หามาได้
        cmd = [
            ffmpeg_binary,  # <--- จุดสำคัญคือตรงนี้ มันจะชี้ไปที่ไฟล์ใน bin
            '-i', input_path,
            '-vf', 'scale=-2:480',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '28',
            '-y',
            proxy_path
        ]

        # รันคำสั่งแบบซ่อนหน้าต่าง (ไม่ให้เด้ง pop-up)
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Track สำหรับ cleanup เมื่อปิดโปรแกรม
        _PROXY_FILES.add(proxy_path)
        return proxy_path

    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg conversion failed for {filename}: {e}")
        return None
    except FileNotFoundError:
        logging.error("FFmpeg not found. Please install FFmpeg or ensure it's in the bin folder.")
        return None
    except Exception as e:
        logging.error(f"Proxy creation failed: {e}")
        return None  # ถ้าบีบอัดไม่ผ่าน ให้คืนค่า None (เพื่อไปใช้ไฟล์เดิม)


def open_folder_selector():
    folder_path = None
    system_platform = platform.system()  # เช็คว่ารันบนเครื่องอะไร

    # --- กรณี MAC (Darwin) ---
    if system_platform == "Darwin":
        try:
            # ใช้ AppleScript เพื่อเรียก Finder แบบ Native
            script = """
            tell application "System Events"
                activate
                set f to choose folder with prompt "Select Folder (เลือกโฟลเดอร์รูป/วิดีโอ)"
                return POSIX path of f
            end tell
            """
            # รันคำสั่ง
            proc = subprocess.run(['osascript', '-e', script],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode == 0:
                folder_path = proc.stdout.strip()
            else:
                print(f"Mac Picker Cancelled/Error: {proc.stderr}")
        except subprocess.SubprocessError as e:
            logging.error(f"Mac AppleScript error: {e}")
        except Exception as e:
            logging.error(f"Mac System Error: {e}")

    # --- กรณี WINDOWS ---
    elif system_platform == "Windows":
        try:
            import tkinter as tk
            from tkinter import filedialog

            # สร้างหน้าต่าง Tkinter แบบซ่อน (ไม่เอาหน้าต่างหลัก)
            root = tk.Tk()
            root.withdraw()

            # [สำคัญ] สั่งให้หน้าต่างเด้งมาอยู่ "บนสุด" เสมอ (Topmost)
            # แก้ปัญหา Windows บางเครื่องที่หน้าต่างชอบไปหลบหลัง Chrome
            root.wm_attributes('-topmost', 1)

            # เปิด Dialog เลือกโฟลเดอร์
            folder_path = filedialog.askdirectory(master=root)

            root.destroy()
        except ImportError:
            logging.error("Tkinter not available on this Windows system")
        except Exception as e:
            logging.error(f"Windows Picker Error: {e}")

    # --- กรณี LINUX ---
    elif system_platform == "Linux":
        try:
            # Try zenity first (most common on Linux desktops)
            result = subprocess.run(['zenity', '--file-selection', '--directory'], 
                               capture_output=True, text=True)
            if result.returncode == 0:
                folder_path = result.stdout.strip()
            else:
                # Fallback to console input
                folder_path = input("Enter folder path: ").strip()
        except FileNotFoundError:
            # Zenity not available, use console input
            try:
                folder_path = input("Enter folder path: ").strip()
            except:
                folder_path = None
        except Exception as e:
            logging.error(f"Linux Picker Error: {e}")

    return folder_path

# ==========================================
# 3. SIDEBAR (CONTROLS)
# ==========================================

if "my_api_key" not in st.session_state:
    # โหลด API Key จากไฟล์เข้ารหัส (มี auto-migration จาก .txt ไป .enc)
    st.session_state.my_api_key = load_api_key()

with st.sidebar:
    st.title("🎛 BigEye Control Panel")
    
    # แสดงสถานะ License และวันหมดอายุ (จาก session ที่ตรวจสอบ online แล้ว)
    try:
        from datetime import datetime
        
        # Use days_left from server (more accurate)
        days_left = st.session_state.get('license_days_left', 0)
        expire_date = st.session_state.get('license_expire', '')
        
        if days_left > 0 or expire_date:
            if days_left <= 0 and expire_date:
                # Fallback to calculating from expire_date
                expiry = datetime.strptime(expire_date, '%d/%m/%Y')
                days_left = (expiry - datetime.now()).days
            
            if days_left <= 7:
                st.warning(f"⚠️ License เหลือ **{days_left}** วัน")
            elif days_left <= 14:
                st.info(f"📅 License เหลือ **{days_left}** วัน")
            else:
                st.success(f"✅ License เหลือ **{days_left}** วัน")
            
            if expire_date:
                st.caption(f"หมดอายุ: {expire_date}")
    except Exception:
        pass
    
    st.markdown("---")
    
    # [PERFORMANCE FIX] รัน cleanup ใน background thread เพื่อไม่บล็อก UI (30-40 วินาที)
    if st.session_state.my_api_key and "cleanup_done" not in st.session_state:
        import threading
        def run_cleanup_background():
            try:
                cleanup_orphaned_files(st.session_state.my_api_key)
            except:
                pass
        cleanup_thread = threading.Thread(target=run_cleanup_background, daemon=True)
        cleanup_thread.start()
        st.session_state.cleanup_done = True

    # 1. Google API Key
    api_input = st.text_input("🔑 Google API Key", value=st.session_state.my_api_key, type="password")

    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Save", type="primary", use_container_width=True):
            if save_api_key(api_input):
                st.session_state.my_api_key = api_input
                st.toast("API Key Saved! (เข้ารหัสแล้ว)", icon="✅")
                st.rerun()
            else:
                st.error("ไม่สามารถบันทึก API Key ได้")

    with col_clear:
        if st.button("🗑 Clear", type="secondary", use_container_width=True):
            clear_api_key()
            st.session_state.my_api_key = ""
            st.toast("API Key Cleared!", icon="🗑")
            st.rerun()

    st.markdown("---")

    # 2. AI Model
    import google.generativeai as genai

    # 1. กำหนดชื่อโมเดลที่คุณใช้ประจำ (ไม่ต้องเรียก API ทุกครั้ง)
    # เรียงลำดับโดย gemini-2.5-pro เป็นค่าเริ่มต้น (index=0)
    my_favorite_models = [
        "models/gemini-2.5-pro",        # Default - คุณภาพสูงสุด
        "models/gemini-2.5-flash",       # เร็วและประหยัด
        "models/gemini-2.0-flash",
        "models/gemini-3-pro-preview",
        "models/gemini-2.0-pro-exp-02-05"
    ]

    # [PERFORMANCE FIX] ใช้ list ตรงๆ แทนการเรียก API ที่ช้ามาก (30-40 วินาที)
    allowed_models = my_favorite_models

    model_choice = st.selectbox(
        "AI Model",
        options=allowed_models,
        # ตั้งค่าเริ่มต้นที่ gemini-2.5-pro (index=0)
        index=0
    )
    
    st.markdown("---")

    # 3. Select Mode
    st.subheader("🎯 Select Mode")
    
    # ใช้ selectbox แทน radio เพื่อให้ยืดเต็มความกว้าง
    platform_options = list(config.PLATFORM_SETTINGS.keys())
    if 'platform_name' not in st.session_state:
        st.session_state.platform_name = platform_options[0]
    
    # สร้างปุ่มเลือกโหมดแบบ full-width
    for i, option in enumerate(platform_options):
        is_selected = st.session_state.platform_name == option
        btn_type = "primary" if is_selected else "secondary"
        if st.button(option, key=f"mode_btn_{i}", use_container_width=True, type=btn_type):
            st.session_state.platform_name = option
            st.rerun()
    
    platform_name = st.session_state.platform_name

    st.session_state.platform_name = platform_name

    current_platform_cfg = config.PLATFORM_SETTINGS[platform_name]
    # ซ่อนสถานะโหมดไว้ (ไม่แสดงให้ผู้ใช้เห็น)
    # mode_status = "🔒 Strict Mode" if current_platform_cfg['requires_db'] else "✨ Open Mode"
    # st.caption(f"Status: {mode_status}")

    # --- KEYWORD MODE SELECTION (สำหรับ Adobe & Shutterstock) ---
    if current_platform_cfg.get('has_keyword_mode'):
        st.markdown("---")
        st.subheader("🔤 Keyword Style")
        
        # Initialize keyword_mode in session state
        if 'keyword_mode' not in st.session_state:
            st.session_state.keyword_mode = "HYBRID (Phrase & Single Words)"
        
        keyword_mode_options = list(config.KEYWORD_MODE_OPTIONS.keys())
        
        # สร้างปุ่มเลือก Keyword Mode
        for i, kw_option in enumerate(keyword_mode_options):
            is_selected = st.session_state.keyword_mode == kw_option
            btn_type = "primary" if is_selected else "secondary"
            
            # แสดงคำอธิบายโหมด
            option_desc = config.KEYWORD_MODE_OPTIONS[kw_option].get('description', '')
            btn_label = f"{kw_option}"
            
            if st.button(btn_label, key=f"kw_mode_btn_{i}", use_container_width=True, type=btn_type):
                st.session_state.keyword_mode = kw_option
                st.rerun()

    # 4. Parallel Threads
    workers = st.slider("Parallel Threads", 1, 8, 4)

    st.markdown("---")
    
    # 5. Metadata Settings
    # ตรวจสอบสถานะการประมวลผลเพื่อล็อค settings
    is_processing = st.session_state.get('is_processing', False)
    
    if is_processing:
        st.subheader("🔒 Metadata Settings (ล็อค)")
        st.caption("⚠️ ไม่สามารถเปลี่ยนค่าระหว่างประมวลผล")
    else:
        st.subheader("📏 Metadata Settings")

    # --- 1. TITLE LIMIT ---
    if 'title_slider' not in st.session_state: 
        st.session_state.title_slider = 70
    if 'title_input' not in st.session_state:
        st.session_state.title_input = 70
    
    def update_title_slider():
        st.session_state.title_input = st.session_state.title_slider

    def update_title_input():
        st.session_state.title_slider = st.session_state.title_input

    c1, c2 = st.columns([3, 1])
    with c1:
        st.slider("Title Length", 50, 200, key="title_slider", on_change=update_title_slider, disabled=is_processing)
    with c2:
        st.number_input("Chars", 50, 200, key="title_input", on_change=update_title_input, label_visibility="collapsed", disabled=is_processing)
    
    title_char_limit = st.session_state.title_slider


    # --- 2. DESCRIPTION LIMIT ---
    if 'desc_slider' not in st.session_state: 
        st.session_state.desc_slider = 200
    if 'desc_input' not in st.session_state:
        st.session_state.desc_input = 200
    
    def update_desc_slider():
        st.session_state.desc_input = st.session_state.desc_slider

    def update_desc_input():
        st.session_state.desc_slider = st.session_state.desc_input

    c1, c2 = st.columns([3, 1])
    with c1:
        st.slider("Description Length", 100, 500, key="desc_slider", on_change=update_desc_slider, disabled=is_processing)
    with c2:
        st.number_input("Chars", 100, 500, key="desc_input", on_change=update_desc_input, label_visibility="collapsed", disabled=is_processing)
    
    desc_char_limit = st.session_state.desc_slider


    # --- 3. KEYWORD COUNT ---
    if 'kw_slider' not in st.session_state: st.session_state.kw_slider = 45
    if 'kw_input' not in st.session_state: st.session_state.kw_input = 45
    
    def update_kw_slider():
        st.session_state.kw_input = st.session_state.kw_slider

    def update_kw_input():
        st.session_state.kw_slider = st.session_state.kw_input

    c1, c2 = st.columns([3, 1])
    with c1:
        st.slider("Keywords Count", 10, 50, key="kw_slider", on_change=update_kw_slider, disabled=is_processing)
    with c2:
        st.number_input("Count", 10, 50, key="kw_input", on_change=update_kw_input, label_visibility="collapsed", disabled=is_processing)

    target_kw_count = st.session_state.kw_slider
    # Negative Keywords ถูกลบออกแล้ว
    
    st.markdown("---")
    
    # 6. Debug Tools
    st.subheader("🔧 Debug Tools")
    if st.button("🕵️ Check Active Caches"):
        try:
            genai.configure(api_key=st.session_state.my_api_key)

            from google.generativeai import caching

            # สั่งให้ Google List รายการ Cache ทั้งหมดออกมา
            caches = list(caching.CachedContent.list())

            if not caches:
                st.success("✅ Clean! ไม่พบ Cache ค้างในระบบ")
            else:
                st.warning(f"⚠️ พบ Cache ค้างอยู่ {len(caches)} รายการ:")
                for c in caches:
                    st.caption(f"- {c.name} (Exp: {c.expire_time})")
                    # ถ้าอยากลบมือ ก็สั่งลบตรงนี้ได้เลย
                    # c.delete()
        except Exception as e:
            st.error(f"Error checking cache: {e}")

    # ======================================================
    # 7. Keyword Database (ซ่อนจาก UI แต่ยังทำงานอยู่)
    # ======================================================
    db_content = ""
    current_platform_cfg = config.PLATFORM_SETTINGS[st.session_state.platform_name]
    if current_platform_cfg["requires_db"]:
        db_content = load_database()  # โหลดฐานข้อมูลเบื้องหลัง (ไม่แสดง UI)

# ==========================================
# 4. MAIN INTERFACE
# ==========================================

st.markdown(
    f'<h1 class="main-header">BigEye <span style="font-size:0.4em; vertical-align: middle; color:#333;">(Pro)</span></h1>',
    unsafe_allow_html=True)

# --- FOLDER PICKER ---

# --- FOLDER SELECTION UI (Universal Fix) ---


# จัดวางปุ่มและช่องกรอกให้อยู่บรรทัดเดียวกัน
col_btn, col_input = st.columns([1, 4])

with col_btn:
    # 1. ปุ่มกดเลือก (Pop-up)
    if st.button("Browse...", type="primary", use_container_width=True):
        selected = open_folder_selector()
        if selected:
            st.session_state['folder_path'] = selected
            st.rerun()

with col_input:
    # 2. ช่องกรอก Path (รองรับการ Paste)
    current_val = st.session_state.get('folder_path', '')

    new_path_input = st.text_input(
        "Folder Path",
        value=current_val,
        label_visibility="collapsed",
        placeholder="Paste path here..."
    )

    # --- [FIX] แก้ปัญหา Mac แถมเครื่องหมาย ' มาให้ ---
    if new_path_input:
        # 1. .strip() ลบช่องว่างหัวท้าย
        # 2. .strip("'") ลบเครื่องหมายฝนทอง ' ที่ Mac แถมมา
        # 3. .strip('"') ลบเครื่องหมายฟันหนู " (เผื่อมี)
        clean_path = new_path_input.strip().strip("'").strip('"')
    else:
        clean_path = ""
    # ------------------------------------------------

    # Logic: ถ้า User เปลี่ยนค่าในช่องนี้เอง ให้ถือว่า User เป็นคนสั่ง
    if clean_path != current_val:
        st.session_state['folder_path'] = clean_path
        st.rerun()

# ตรวจสอบว่า Path ที่ได้มา (ไม่ว่าจะจากปุ่ม หรือ พิมพ์เอง) มีอยู่จริงไหม
final_path = st.session_state.get('folder_path', '')
if final_path:
    if os.path.isdir(final_path):
        st.success(f"✅ Selected: {final_path}")
    else:
        st.error("❌ ไม่พบโฟลเดอร์นี้ (Path Incorrect)")
        final_path = None  # reset ถ้า path ผิด

# ส่งค่าไปให้ตัวแปรเดิมทำงานต่อ
current_path = final_path

# --- MAIN LOGIC ---
if current_path and os.path.isdir(current_path):
    # 1. อ่านไฟล์ทั้งหมดในโฟลเดอร์
    all_items = [f for f in os.listdir(current_path) if not f.startswith('.')]
    valid_exts = config.VALID_IMAGE_EXT + config.VALID_VIDEO_EXT

    # -------------------------------------------------------------
    # [FIXED LOGIC] ระบบจัดการไฟล์ Proxy (กันไฟล์ขยะหลุดเข้า CSV)
    # -------------------------------------------------------------

    # Step A: ล้างบางไฟล์ Proxy เก่าที่ตกค้างทิ้งก่อน (Auto-Cleanup)
    # เผื่อรอบที่แล้วกด Stop หรือโปรแกรมดับไปก่อนลบเสร็จ จะได้ไม่รกเครื่อง
    for f in all_items:
        if f.startswith("proxy_"):
            try:
                os.remove(os.path.join(current_path, f))
                logging.info(f"Cleaned up old proxy: {f}")
            except PermissionError:
                logging.warning(f"Permission denied removing proxy: {f}")
            except FileNotFoundError:
                pass  # File already deleted
            except Exception as e:
                logging.error(f"Failed to remove proxy {f}: {e}")

    # Step B: เลือกเฉพาะไฟล์งานจริง (Ignore Proxy)
    # เพิ่มเงื่อนไข 'and not f.startswith("proxy_")' เพื่อความชัวร์ 100% ว่าจะไม่หยิบไฟล์ขยะมาทำ
    target_files = [
        os.path.join(current_path, f)
        for f in all_items
        if f.lower().endswith(valid_exts) and not f.startswith("proxy_")
    ]

    st.info(f"📂 พร้อมทำงาน: **{len(target_files)}** ไฟล์ | โหมด: **{platform_name}**")

    if 'is_processing' not in st.session_state:
        st.session_state['is_processing'] = False
    if 'completion_summary' not in st.session_state:
        st.session_state['completion_summary'] = None

    controls_placeholder = st.empty()

    def _render_controls():
        with controls_placeholder.container():
            c_start, c_stop = st.columns([3, 1])
            with c_start:
                start_label = "⏳ กำลังทำงาน..." if st.session_state['is_processing'] else f"🚀 เริ่มวิเคราะห์ ({platform_name})"
                start_disabled = (len(target_files) == 0) or st.session_state['is_processing']
                start_clicked = st.button(start_label, disabled=start_disabled,
                                          use_container_width=True, type="primary")
            with c_stop:
                stop_clicked = st.button("🛑 STOP", use_container_width=True, type="secondary", disabled=not st.session_state['is_processing'])
        return start_clicked, stop_clicked

    start_process, stop_process = _render_controls()

    # แสดงสรุปผลการทำงาน (ถ้ามี)
    if st.session_state.get('completion_summary'):
        summary = st.session_state['completion_summary']
        st.success(f"""
### [OK] ทำงานเสร็จสิ้น

| รายการ | จำนวน |
|--------|-------|
| [IMG] ภาพถ่าย | {summary['photo_count']} ไฟล์ |
| [VDO] วิดีโอ | {summary['video_count']} ไฟล์ |
| **รวมทั้งหมด** | **{summary['total_count']} ไฟล์** |

[FOLDER] **ไฟล์ผลลัพธ์ถูกเก็บไว้ที่:**  
`{summary['output_folder']}`
""")
        # ล้าง summary หลังแสดงแล้ว (จะหายไปเมื่อ user กดปุ่มใหม่)
        st.session_state['completion_summary'] = None

    if stop_process:
        st.session_state['stop_flag'] = True
    else:
        if 'stop_flag' not in st.session_state:
            st.session_state['stop_flag'] = False

    if start_process:
        st.session_state['stop_flag'] = False
        st.session_state['is_processing'] = True
        st.rerun()

    if st.session_state.get('is_processing'):
        if not st.session_state.my_api_key:
            st.error("❌ ยังไม่ได้ใส่ API Key (ดูเมนูซ้ายมือ)")
            st.session_state['is_processing'] = False
        elif current_platform_cfg["requires_db"] and not db_content:
            st.error("❌ โหมดนี้ต้องใช้ Database (ดูเมนูซ้ายมือ)")
            st.session_state['is_processing'] = False
        else:
            results = []
            run_state = "error"
            try:
                genai.configure(api_key=st.session_state.my_api_key)
                model = genai.GenerativeModel(model_name=model_choice,
                                              generation_config={"response_mime_type": "application/json"})

                from google.generativeai import caching
                import datetime

                CACHE_THRESHOLD = 10

                if platform_name == "iStock" and db_content and len(target_files) >= CACHE_THRESHOLD:
                    try:
                        st.info(f"🚀 Large Batch Detected ({len(target_files)} files) -> Initializing Context Cache...")

                        sys_instruction = f"""
                            You are an expert Stock Keyword Generator for BigEye.
                            CRITICAL INSTRUCTION: You have been provided with a massive 'Reference Dictionary' in this System Context.
                            When asked to generate keywords, you MUST STRICTLY use words from this cached dictionary only.

                            --- REFERENCE DICTIONARY START ---
                            {db_content}
                            --- REFERENCE DICTIONARY END ---
                            """

                        cache = caching.CachedContent.create(
                            model=model_choice,
                            display_name="istock_db_cache",
                            system_instruction=sys_instruction,
                            ttl=datetime.timedelta(minutes=60),
                        )

                        model = genai.GenerativeModel.from_cached_content(cached_content=cache)
                        db_content = "(*** REFERENCE DICTIONARY IS CACHED IN SYSTEM CONTEXT - DO NOT REPEAT ***)"

                        st.success("✅ Context Caching Active! (Database loaded into memory)")
                    except Exception as e:
                        st.warning(f"⚠️ Caching Skipped (Standard Mode): {e}")

                proxy_map = create_proxies_for_videos(target_files)

                # Check if stopped during proxy creation
                if st.session_state.get('stop_flag'):
                    run_state = "stopped"
                    st.warning("🛑 หยุดทำงาน (Stopped during proxy creation)")
                else:
                    run_state = "completed"
                    with st.status("🤖 กำลังวิเคราะห์... (AI Working)", expanded=True) as status:
                        progress_bar = st.progress(0, text="Uploading files...")
                        # ดึง keyword_mode จาก session state (สำหรับ Adobe & Shutterstock)
                        current_keyword_mode = st.session_state.get('keyword_mode', None)
                        # ดึง server_config จาก session state ก่อนส่งไป worker threads
                        # (เพราะ st.session_state ไม่สามารถเข้าถึงได้จาก worker threads)
                        current_server_config = st.session_state.get('server_config', {})
                        
                        if not current_server_config:
                            st.error("❌ Server config ไม่พร้อมใช้งาน กรุณา Refresh หน้าเว็บ")
                            run_state = "error"
                        else:
                            with ThreadPoolExecutor(max_workers=workers) as executor:
                                future_to_file = {
                                    executor.submit(
                                        process_single_file,
                                        model,
                                        f,
                                        current_platform_cfg,
                                        db_content,
                                        target_kw_count,
                                        title_char_limit,
                                        desc_char_limit,
                                        proxy_map.get(f),
                                        current_keyword_mode,  # ส่ง keyword_mode ไปด้วย
                                        current_server_config  # ส่ง server_config ไปด้วย (thread-safe)
                                    ): f for f in target_files
                                }
                                for i, future in enumerate(as_completed(future_to_file)):
                                    if st.session_state.get('stop_flag'):
                                        run_state = "stopped"
                                        executor.shutdown(wait=False, cancel_futures=True)
                                        progress_bar.progress((i + 1) / len(target_files), text="หยุดทำงาน")
                                        status.update(label="🛑 หยุดทำงาน", state="error")
                                        break
                                    data = future.result()
                                    results.append(data)
                                    progress_bar.progress((i + 1) / len(target_files), text=f"กำลังวิเคราะห์ ({i+1}/{len(target_files)}): {data.get('file_name','')}")

                            if run_state == "completed":
                                progress_bar.progress(1.0, text="เสร็จสิ้น")
                                status.update(label="✅ เสร็จสิ้น", state="complete")

                for original_path, proxy_path in proxy_map.items():
                    try:
                        if proxy_path and os.path.exists(proxy_path):
                            os.remove(proxy_path)
                    except Exception as e:
                        logging.warning(f"Failed to delete proxy {proxy_path}: {e}")

                if run_state == "completed" and results:
                    play_notification_sound()
                    st.balloons()
                elif run_state == "stopped":
                    st.info("🛑 Stopped")

                if run_state == "completed" and results:
                    success_data = [r for r in results if "error" not in r]

                    if success_data:
                        df = pd.DataFrame(success_data)

                        # 1. จัดการข้อมูลเบื้องต้นให้เป็นมาตรฐานเดียวกัน
                        df.rename(columns={"file_name": "Filename"}, inplace=True)

                        # แปลง List ใน Keywords เป็น String (comma-separated)
                        if "keywords" in df.columns:
                            df["keywords"] = df["keywords"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

                        # ---------------------------------------------------------
                        # LOGIC การเซฟไฟล์แยกตามโหมด (Fixed for iStock Template)
                        # ---------------------------------------------------------
                        from datetime import datetime

                        # ดึงวันที่ปัจจุบัน (Format: YYYY-MM-DD)
                        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

                        # ดึงชื่อโมเดลและลบอักขระพิเศษ
                        clean_model = model_choice.replace("models/", "").replace(":", "").replace(".", "-")

                        # รวมเป็นส่วนขยายท้ายไฟล์
                        # ตัวอย่างผลลัพธ์: "_gemini-2-0-flash_2024-02-14_14-30-05"
                        filename_suffix = f"_{clean_model}_{current_datetime}"

                        if platform_name == "Adobe & Shutterstock":
                            # ส่วนของ Adobe/Shutterstock (แยก 2 ไฟล์ - ใช้ข้อมูลเดียวกัน)
                            df_base = df.copy()

                            # 1. Adobe Version (Title + Keywords)
                            df_adobe = df_base.copy()
                            df_adobe.rename(columns={"title": "Title", "keywords": "Keywords"}, inplace=True)
                            
                            # แปลง Keywords list เป็น comma-separated string
                            if "Keywords" in df_adobe.columns:
                                df_adobe["Keywords"] = df_adobe["Keywords"].apply(
                                    lambda x: ", ".join(x) if isinstance(x, list) else x
                                )
                            
                            df_adobe["Category"] = ""
                            df_adobe["Releases"] = ""
                            final_adobe = df_adobe.reindex(columns=config.ADOBE_CSV_COLUMNS)
                            final_adobe.to_csv(os.path.join(current_path, f"Metadata Adobe{filename_suffix}.csv"), index=False, encoding='utf-8')

                            # 2. Shutterstock Version (Description + Keywords)
                            df_ss = df_base.copy()
                            df_ss.rename(columns={"description": "Description", "keywords": "Keywords"}, inplace=True)
                            
                            # แปลง Keywords list เป็น comma-separated string
                            if "Keywords" in df_ss.columns:
                                df_ss["Keywords"] = df_ss["Keywords"].apply(
                                    lambda x: ", ".join(x) if isinstance(x, list) else x
                                )
                            
                            df_ss["Categories"] = ""
                            df_ss["Illustration"] = "No"
                            df_ss["Mature Content"] = "No"
                            df_ss["Editorial"] = "No"
                            final_ss = df_ss.reindex(columns=config.SHUTTERSTOCK_CSV_COLUMNS)
                            final_ss.to_csv(os.path.join(current_path, f"Metadata Shutterstock{filename_suffix}.csv"), index=False, encoding='utf-8')

                        elif platform_name == "iStock":
                            df_istock_base = df.copy()
                            is_video_mask = df_istock_base['Filename'].str.lower().str.endswith(config.VALID_VIDEO_EXT)
                            df_photo = df_istock_base[~is_video_mask]
                            df_video = df_istock_base[is_video_mask]
                            if not df_photo.empty:
                                df_p = df_photo.copy()
                                df_p.rename(columns={
                                    "Filename": "file name",
                                    "niche_analysis": "Niche Strategy",
                                    "missing_keywords": "Missing Keywords"
                                }, inplace=True)
                                final_photo = df_p.reindex(columns=config.ISTOCK_COLS_PHOTO)
                                final_photo.to_csv(os.path.join(current_path, f"Metadata iStock Photos{filename_suffix}.csv"), index=False, encoding='utf-8')
                            if not df_video.empty:
                                df_v = df_video.copy()
                                df_v.rename(columns={
                                    "Filename": "file name",
                                    "missing_keywords": "Missing Keywords",
                                    "poster_timecode": "poster timecode",
                                    "shot_speed": "shot speed"
                                }, inplace=True)
                                final_video = df_v.reindex(columns=config.ISTOCK_COLS_VIDEO)
                                final_video.to_csv(os.path.join(current_path, f"Metadata iStock Videos{filename_suffix}.csv"), index=False, encoding='utf-8')

                        if 'cache' in locals() and cache:
                            try:
                                cache.delete()
                                st.toast("🧹 Cache Deleted (Cost Saving)", icon="💸")
                                print(f"Deleted cache: {cache.name}")
                            except Exception as e:
                                print(f"Could not delete cache: {e}")

                        with st.spinner("📁 กำลังจัดระเบียบไฟล์..."):
                            completed_folder, error_count, success_count = organize_output_files(
                                source_folder=current_path,
                                results=results,
                                platform_name=platform_name,
                                filename_suffix=filename_suffix,
                                keyword_style=current_keyword_mode  # ส่ง keyword style ไปด้วย
                            )

                        # เก็บสรุปผลการทำงานไว้ใน session state
                        video_count = sum(1 for r in success_data if r.get('file_name', '').lower().endswith(config.VALID_VIDEO_EXT))
                        photo_count = len(success_data) - video_count
                        st.session_state['completion_summary'] = {
                            'photo_count': photo_count,
                            'video_count': video_count,
                            'total_count': len(success_data),
                            'output_folder': completed_folder
                        }
                        
                        # Report usage to server (async - non-blocking)
                        if st.session_state.get('license_key'):
                            try:
                                from license.validator_api import report_usage
                                report_usage(
                                    st.session_state.license_key,
                                    photo_count=photo_count,
                                    video_count=video_count
                                )
                            except Exception as e:
                                logging.warning(f"Failed to report usage: {e}")

            except Exception as e:
                logging.error(f"Processing failed: {e}")
                st.error(f"❌ Processing failed: {e}")
            finally:
                st.session_state['is_processing'] = False
                st.session_state['stop_flag'] = False
                controls_placeholder.empty()
                st.rerun()

elif not current_path:
    st.info("👈 เลือกโฟลเดอร์รูปภาพเพื่อเริ่มต้น")
else:
    st.error(f"❌ ไม่พบโฟลเดอร์: {current_path}")