# config.py - BigEye Pro
# ==========================================
# Static constants ONLY - Prompts are fetched from server at runtime
# ==========================================

# ==========================================
# 1. UI & SYSTEM CONSTANTS
# ==========================================
THEME_COLOR_1 = "#FF00CC"
THEME_COLOR_2 = "#3333FF"
STOP_COLOR = "#FF4B4B"

VALID_IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp')
VALID_VIDEO_EXT = ('.mp4', '.mov', '.avi', '.mkv', '.webm')

# Timeout Settings (Seconds)
TIMEOUT_VIDEO = 600
TIMEOUT_PHOTO = 60
WAIT_TIME_RETRY = 5
MAX_RETRIES = 3

# ==========================================
# 2. CSV COLUMN DEFINITIONS
# ==========================================

# iStock CSV Columns
ISTOCK_COLS_PHOTO = [
    "file name", "created date", "description", "country", "brief code", 
    "title", "keywords", "Niche Strategy", "Missing Keywords"
]
ISTOCK_COLS_VIDEO = [
    "file name", "description", "country", "title", "keywords", 
    "poster timecode", "date created", "shot speed", "Missing Keywords"
]

# Adobe Stock CSV Columns
ADOBE_CSV_COLUMNS = [
    "Filename", "Title", "Keywords", "Category", "Releases"
]

# Shutterstock CSV Columns
SHUTTERSTOCK_CSV_COLUMNS = [
    "Filename", "Description", "Keywords", "Categories",
    "Illustration", "Mature Content", "Editorial"
]

# ==========================================
# 3. VIDEO INSTRUCTION (Static - Not Sensitive)
# ==========================================
VIDEO_INSTRUCTION_TEXT = """
**VIDEO SPECIFICS:**
1. **POSTER TIMECODE (CRITICAL):**
   - You MUST analyze the video to find the most attractive frame.
   - **STRICT OUTPUT FORMAT:** You must return the timecode as **HH:MM:SS:FF** (Hours:Minutes:Seconds:Frames).
   - *Example:* If the best shot is at 5 seconds, write "00:00:05:00".
   - *Example:* If the best shot is at 1 minute 12 seconds, write "00:01:12:00".
   - **DO NOT** use "00:05" or "5s". You MUST fill all fields: 00:00:05:00.

2. **SHOT SPEED:** Analyze if the footage is 'Real Time', 'Slow Motion', or 'Time Lapse'.
"""

# ==========================================
# 4. KEYWORD MODE OPTIONS
# ==========================================
KEYWORD_MODE_OPTIONS = {
    "Single Words": {
        "prompt_key": "prompt_single",
        "description": "เน้นคำเดี่ยว เหมาะสำหรับ Shutterstock"
    },
    "HYBRID (Phrase & Single Words)": {
        "prompt_key": "prompt_hybrid",
        "description": "ผสมวลีและคำเดี่ยว เหมาะสำหรับ Adobe Stock"
    }
}

# ==========================================
# 5. PLATFORM SETTINGS MAP
# ==========================================
# NOTE: Prompts are now fetched from server via fetch_secure_config()
# These settings only define CSV columns and platform behavior
PLATFORM_SETTINGS = {
    "iStock": {
        "prompt_key": "prompt_istock",  # Key to fetch from server config
        "csv_columns_photo": ISTOCK_COLS_PHOTO,
        "csv_columns_video": ISTOCK_COLS_VIDEO,
        "requires_db": True,
        "default_country": "Thailand"
    },
    "Adobe & Shutterstock": {
        "prompt_key_hybrid": "prompt_hybrid",
        "prompt_key_single": "prompt_single",
        "csv_columns_adobe": ADOBE_CSV_COLUMNS,
        "csv_columns_shutterstock": SHUTTERSTOCK_CSV_COLUMNS,
        "requires_db": False,
        "keyword_placeholder_text": "",
        "default_country": "Thailand",
        "has_keyword_mode": True
    }
}