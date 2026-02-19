"""
BigEye Pro — Application Configuration
"""
import os
import sys


APP_NAME = "BigEye Pro"
APP_VERSION = "2.0.0"
KEYRING_SERVICE = "BigEyePro"
KEYRING_API_KEY = "gemini_api_key"
KEYRING_JWT = "jwt_token"
KEYRING_USER = "user_data"

# Backend API
API_BASE_URL = os.environ.get("BIGEYE_API_URL", "http://localhost:8080/api/v1")

# Directories
HOME_DIR = os.path.expanduser("~")
APP_DATA_DIR = os.path.join(HOME_DIR, ".bigeye")
DEBUG_LOG_PATH = os.path.join(APP_DATA_DIR, "debug_log.txt")
RECOVERY_PATH = os.path.join(APP_DATA_DIR, "recovery.json")

# Ensure app data dir exists
os.makedirs(APP_DATA_DIR, exist_ok=True)

# Window sizes
MAIN_WINDOW_WIDTH = 1400
MAIN_WINDOW_HEIGHT = 800
MAIN_WINDOW_MIN_WIDTH = 1200
MAIN_WINDOW_MIN_HEIGHT = 700
AUTH_WINDOW_WIDTH = 480

# Layout sizes
SIDEBAR_WIDTH = 270
INSPECTOR_WIDTH = 300
TOP_BAR_HEIGHT = 48
STATUS_BAR_HEIGHT = 22
THUMBNAIL_SIZE = 130

# Credit refresh interval (ms)
CREDIT_REFRESH_INTERVAL = 5 * 60 * 1000  # 5 minutes
LOW_CREDIT_THRESHOLD = 50

# Platform rates — populated from server on startup via /credit/balance
# Structure: {platform: {"photo": N, "video": N}}
PLATFORM_RATES = {
    "iStock": {"photo": 3, "video": 3},
    "Adobe & Shutterstock": {"photo": 2, "video": 2},
}

# AI Models — list of model IDs shown in dropdown (newest first)
AI_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# AI Model metadata: {model_id: {label, supports_cache, description}}
AI_MODEL_INFO = {
    "gemini-2.5-pro": {
        "label": "Gemini 2.5 Pro",
        "supports_cache": False,
        "description": "ฉลาดที่สุด | คุณภาพสูงสุด | ช้ากว่า",
    },
    "gemini-2.5-flash": {
        "label": "Gemini 2.5 Flash",
        "supports_cache": False,
        "description": "ใหม่ล่าสุด | เร็ว + ฉลาด | แนะนำ",
    },
    "gemini-2.0-flash": {
        "label": "Gemini 2.0 Flash",
        "supports_cache": False,
        "description": "เร็ว | คุณภาพดี | ราคาถูก",
    },
    "gemini-2.0-flash-lite": {
        "label": "Gemini 2.0 Flash-Lite",
        "supports_cache": False,
        "description": "เร็วมาก | ราคาถูกที่สุด | ใช้งานทั่วไป",
    },
    "gemini-1.5-pro": {
        "label": "Gemini 1.5 Pro",
        "supports_cache": True,
        "description": "รองรับ Context Cache | วิดีโอยาวได้ดี",
    },
    "gemini-1.5-flash": {
        "label": "Gemini 1.5 Flash",
        "supports_cache": True,
        "description": "รองรับ Context Cache | เร็ว + ประหยัด",
    },
    "gemini-1.5-flash-8b": {
        "label": "Gemini 1.5 Flash-8B",
        "supports_cache": True,
        "description": "รองรับ Context Cache | เร็วที่สุด | ราคาต่ำสุด",
    },
}

# Keyword styles
KEYWORD_STYLES = [
    "Hybrid (Phrase & Single)",
    "Single Words",
]

# Platforms display
PLATFORMS = [
    "iStock",
    "Adobe & Shutterstock",
]

# Metadata slider configs
SLIDER_CONFIGS = {
    "keywords": {"min": 10, "max": 50, "default": 45, "step": 1},
    "title_length": {"min": 50, "max": 200, "default": 70, "step": 5},
    "description": {"min": 100, "max": 500, "default": 200, "step": 10},
}

# Supported file extensions (stock-site compatible only)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".eps"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# AES key for decrypting server config (placeholder — set from server)
AES_KEY_HEX = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

# Deep Navy Theme (v3)
THEME = {
    "bg": "#1A1A2E",
    "surface": "#16213E",
    "surface_alt": "#0F3460",
    "border": "#1A3A6B",
    "border_light": "#264773",
    "text": "#E8E8E8",
    "text_sec": "#8892A8",
    "text_dim": "#4A5568",
    "accent": "#FF00CC",
    "accent2": "#7B2FFF",
    "success": "#00E396",
    "warning": "#FEB019",
    "error": "#FF4560",
    "credit": "#FFD700",
    "blue": "#00B4D8",
}

# Processing timeouts (seconds)
TIMEOUT_VIDEO = 600
TIMEOUT_PHOTO = 60
MAX_RETRIES = 3

# Credit rates per platform — populated from server on startup
CREDIT_RATES = {"iStock": {"photo": 3, "video": 3}, "Adobe": {"photo": 2, "video": 2}, "Shutterstock": {"photo": 2, "video": 2}}

# CSV column definitions (must match platform upload formats exactly)
ISTOCK_COLS_PHOTO = [
    "file name", "created date", "description", "country", "brief code",
    "title", "keywords",
]
ISTOCK_COLS_VIDEO = [
    "file name", "description", "country", "title", "keywords",
    "poster timecode", "date created", "shot speed",
]
ADOBE_CSV_COLUMNS = ["Filename", "Title", "Keywords", "Category", "Releases"]
SHUTTERSTOCK_CSV_COLUMNS = [
    "Filename", "Description", "Keywords", "Categories",
    "Illustration", "Mature Content", "Editorial",
]


def get_asset_path(relative_path: str) -> str:
    """Get absolute path to asset, works for dev and Nuitka build."""
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    elif getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)
