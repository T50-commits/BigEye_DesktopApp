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

# Platform rates
PLATFORM_RATES = {
    "iStock": 3,
    "Adobe & Shutterstock": 2,
}

# AI Models
AI_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

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

# Supported file extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# AES key for decrypting server config (placeholder — set from server)
AES_KEY_HEX = "0000000000000000000000000000000000000000000000000000000000000000"

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

# Credit rates per platform
CREDIT_RATES = {"iStock": 3, "Adobe": 2, "Shutterstock": 2}

# CSV column definitions (placeholders — will be populated from server config)
ISTOCK_COLS_PHOTO = ["Filename", "Title", "Description", "Keywords", "Category"]
ISTOCK_COLS_VIDEO = ["Filename", "Title", "Description", "Keywords", "Category"]
ADOBE_CSV_COLUMNS = ["Filename", "Title", "Keywords", "Category", "Releases"]
SHUTTERSTOCK_CSV_COLUMNS = ["Filename", "Description", "Keywords", "Categories", "Editorial"]


def get_asset_path(relative_path: str) -> str:
    """Get absolute path to asset, works for dev and Nuitka build."""
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    elif getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)
