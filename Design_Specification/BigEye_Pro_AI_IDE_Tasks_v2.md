# BigEye Pro — Implementation Tasks v2 for AI IDE
### Aligned with Frontend Design v3 FINAL + Database Design v2
### Copy each Task into AI IDE (Cursor / Claude Code / Windsurf) — do them in order
---

## TASK DEPENDENCY MAP
```
PHASE A (Backend) — do first:
A-01 → A-02 → A-03 → A-04 → A-05 → A-06 → A-07 → A-08 → A-09 → A-10

PHASE B (Client) — do after:
B-01 → B-02 → B-03 → B-04 → B-05 → B-05b → B-06 → B-07 → B-08 → B-09 → B-10

Cross-dependencies: A-03↔B-03, A-05↔B-09, A-06↔B-05
```

## WHAT CHANGED (v1 → v2)
```
❌ OLD: Thai UI labels            → ✅ NEW: English throughout
❌ OLD: Colors #1E1E1E/#2D2D2D   → ✅ NEW: Deep navy #1A1A2E/#16213E/#0F3460
❌ OLD: Accent #FF00CC→#3333FF   → ✅ NEW: Accent #FF00CC→#7B2FFF
❌ OLD: Credit section in Sidebar → ✅ NEW: Credit ONLY in Top Bar (no baht display)
❌ OLD: Sidebar 300px             → ✅ NEW: Sidebar 270px
❌ OLD: Inspector 320px           → ✅ NEW: Inspector 300px
❌ OLD: No hover effects          → ✅ NEW: Themed gradient hover on all ghost buttons
❌ OLD: Direct CSV export         → ✅ NEW: ExportCsvDialog with warning + checklist
❌ OLD: 6 dialog files            → ✅ NEW: 10 dialog files (added export_csv, confirm, insufficient, history, maintenance)
❌ OLD: No cost estimate bar      → ✅ NEW: Cost estimate bar in Gallery
❌ OLD: No completion sound       → ✅ NEW: Sound + toast notification
```

---
---

# ═══════════════════════════════════════════
# PHASE A: BACKEND (FastAPI + Firestore)
# ═══════════════════════════════════════════

> **Phase A tasks are UNCHANGED from v1. Copy them from the original BigEye_Pro_AI_IDE_Tasks.md.**
> Tasks A-01 through A-10 remain exactly the same — the backend API is language-agnostic
> and not affected by frontend design changes.

---
---

# ═══════════════════════════════════════════
# PHASE B: CLIENT DESKTOP (PySide6 + Nuitka)
# ═══════════════════════════════════════════

---

## [Task B-01] Client Project Setup (UPDATED v2)

> **Copy from here to END TASK B-01**

```
You are a Senior Python Desktop Developer specializing in PySide6.

TASK: Create BigEye Pro Desktop Client project structure.

TECH: Python 3.10+, PySide6, google-generativeai, httpx, opencv-python-headless,
Pillow, pandas, nltk, keyring, pycryptodome

CREATE FOLDER STRUCTURE:
client/
├── main.py                         # QApplication entry point
├── requirements.txt
├── assets/
│   ├── icons/app_icon.png, app_icon.ico, spinner.gif
│   ├── sounds/complete.wav         # Job completion sound
│   ├── nltk_data/stemmers/snowball_data/  # Pre-downloaded
│   └── styles/dark_theme.qss       # Deep Navy theme (see QSS below)
├── ui/
│   ├── __init__.py
│   ├── auth_window.py              # Login/Register QDialog
│   ├── main_window.py              # Main 3-column layout
│   └── components/
│       ├── __init__.py
│       ├── sidebar.py              # Left: API key + AI settings + sliders (270px)
│       ├── gallery.py              # Center: file grid + cost bar + progress (stretch)
│       ├── inspector.py            # Right: preview + edit + export button (300px)
│       ├── credit_bar.py           # Top bar: BIGEYE + credits + TopUp + user
│       ├── topup_dialog.py         # Slip upload for credit top-up
│       ├── update_dialog.py        # Version check (optional/force)
│       ├── recovery_dialog.py      # Crash recovery notification
│       ├── summary_dialog.py       # Job completion summary
│       ├── confirm_dialog.py       # Pre-processing confirmation
│       ├── insufficient_dialog.py  # Credit shortage options
│       ├── history_dialog.py       # Transaction history table
│       ├── maintenance_dialog.py   # Server maintenance notice
│       └── export_csv_dialog.py    # CSV export with warning + checklist
├── core/
│   ├── __init__.py
│   ├── api_client.py
│   ├── auth_manager.py
│   ├── job_manager.py
│   ├── config.py
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── gemini_engine.py
│   │   └── transcoder.py
│   ├── logic/
│   │   ├── __init__.py
│   │   ├── keyword_processor.py
│   │   └── copyright_guard.py
│   ├── managers/
│   │   ├── __init__.py
│   │   ├── queue_manager.py
│   │   └── journal_manager.py
│   └── data/
│       ├── __init__.py
│       └── csv_exporter.py
├── utils/
│   ├── __init__.py
│   ├── security.py
│   ├── helpers.py
│   └── logger.py
└── build/
    └── build_nuitka.py

main.py MUST:
- Use get_asset_path() that works in dev AND Nuitka compiled (sys._MEIPASS)
- Load dark_theme.qss (Deep Navy theme — colors below)
- Check AuthManager.has_valid_token() → show MainWindow or AuthWindow
- Setup logger to ~/.bigeye/debug_log.txt

dark_theme.qss — DEEP NAVY THEME (copy exactly):
  Main background:    #1A1A2E
  Surface/inputs:     #16213E
  Borders:            #1A3A6B
  Text primary:       #E8E8E8
  Text secondary:     #8892A8
  Text dim:           #4A5568
  Accent gradient:    #FF00CC → #7B2FFF
  Success:            #00E396
  Warning:            #FEB019
  Error:              #FF4560
  Credit gold:        #FFD700
  Export cyan:        #00B4D8

  Ghost buttons hover: gradient background (#FF00CC18→#7B2FFF18) + border #FF00CC66 + text #FF00CC
  Pill buttons: solid gradient #FF00CC→#7B2FFF, white text, border-radius 22px

requirements.txt:
PySide6==6.7.0, google-generativeai==0.8.0, httpx==0.27.0,
opencv-python-headless==4.10.0.84, Pillow==10.4.0, pandas==2.2.0,
nltk==3.9.0, keyring==25.3.0, pycryptodome==3.21.0

ACCEPTANCE CRITERIA:
✅ pip install succeeds
✅ python main.py starts without import errors
✅ get_asset_path works for dev and compiled
✅ Logger creates ~/.bigeye/debug_log.txt
✅ QSS loads and background is #1A1A2E (not black)
```

> **END TASK B-01**

---

## [Task B-02] Security Module (UNCHANGED)

> **Copy from original v1 — Task B-02 is identical.**
> get_hardware_id(), decrypt_aes(), keyring helpers — no UI involved.

---

## [Task B-03] API Client & Config (UPDATED v2)

> **Copy from here to END TASK B-03**

```
TASK: Implement centralized HTTP client for all backend API calls.

FILE: client/core/api_client.py

class APIClient:
  Uses httpx.Client with base_url, 30s timeout.
  set_token(jwt) → adds Authorization header
  is_authenticated property

  AUTH: register(...), login(...) → auto set_token on success
  CREDITS: get_balance(), get_history(limit=50), topup(slip_base64, amount)
  JOBS: reserve_job(file_count, mode, keyword_style, model, version),
        finalize_job(job_token, success, failed, photos, videos)
  SYSTEM: check_update(version, hardware_id)

  Error handling via _handle_errors():
    401 → AuthenticationError
    402 → InsufficientCreditsError (with required/available/shortfall fields)
    403 → ForbiddenError
    409 → ConflictError
    426 → UpdateRequiredError
    429 → RateLimitError
    503 → MaintenanceError
    Other → APIError

  All custom exceptions extend APIError.
  Create singleton: api = APIClient()

FILE: client/core/config.py (UPDATED COLORS)
  APP_VERSION = "2.0.0"
  BACKEND_URL = "https://api.bigeye.pro"  # or env var
  AES_KEY_HEX = "..."

  # DEEP NAVY THEME (v3)
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

  VALID_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
  VALID_VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
  TIMEOUT_VIDEO = 600
  TIMEOUT_PHOTO = 60
  MAX_RETRIES = 3
  CREDIT_RATES = {"iStock": 3, "Adobe": 2, "Shutterstock": 2}
  ISTOCK_COLS_PHOTO = [...]  # Copy from legacy config.py
  ISTOCK_COLS_VIDEO = [...]
  ADOBE_CSV_COLUMNS = [...]
  SHUTTERSTOCK_CSV_COLUMNS = [...]

ACCEPTANCE CRITERIA:
✅ api.login() returns token and sets header
✅ api.reserve_job() returns encrypted config
✅ InsufficientCreditsError has shortfall field
✅ Config theme colors are #1A1A2E (not #1E1E1E)
```

> **END TASK B-03**

---

## [Task B-04] Auth UI (UPDATED v2 — English)

> **Copy from here to END TASK B-04**

```
TASK: Create Login/Register QDialog with Deep Navy theme. ALL TEXT IN ENGLISH.

FILE: client/ui/auth_window.py — class AuthWindow(QDialog)
FILE: client/core/auth_manager.py — class AuthManager

AuthWindow (400px wide, centered, no resize, dark #1A1A2E):
  Logo: "BIGEYE PRO" gradient text (#FF00CC→#7B2FFF) at top, weight 900, 30px
  Subtitle: "STOCK METADATA GENERATOR" dim text 11px
  Tab selector with 2 options (NOT QTabWidget — use styled buttons):
    Active: background #FF00CC15, text #FF00CC
    Inactive: transparent, text #4A5568

  SIGN IN TAB:
    Email QLineEdit (placeholder: "Email")
    Password QLineEdit (password mode, placeholder: "Password")
    "Sign In" gradient pill button (full width)
    Error label (hidden, color #FF4560)
    On click: validate → QThread call api.login → on success: save token, self.accept()

  REGISTER TAB:
    Full Name (placeholder: "Full Name")
    Email (placeholder: "Email")
    Phone Number (placeholder: "Phone Number")
    Password (placeholder: "Password")
    Confirm Password (placeholder: "Confirm Password")
    "Create Account" gradient pill button
    Validate: pw match, pw≥8, phone 9-15 digits
    Call api.register (hardware_id auto-generated, never shown)

  ERROR MESSAGES (ALL ENGLISH):
    401 → "Incorrect email or password"
    403 → "Device mismatch — this account is bound to another device.\nPlease contact admin."
    409 → "This email is already registered"
    429 → "Too many attempts, please wait"
    Network → "Cannot connect to server. Please check your internet."

AuthManager:
  has_valid_token() → check keyring for saved JWT, decode expiry without verification
  login(email, pw) → api.login + save_session_token
  register(email, pw, name, phone) → api.register + save_session_token
  logout() → clear_session_token + api.clear_token
  refresh_balance() → api.get_balance

ACCEPTANCE CRITERIA:
✅ Deep Navy theme (#1A1A2E background, not black)
✅ ALL text in English (no Thai anywhere)
✅ Gradient pill button for Sign In / Create Account
✅ Successful login → main window opens
✅ Error messages display in English
✅ Token saved → next launch skips auth
```

> **END TASK B-04**

---

## [Task B-05] Main Window & UI Components (UPDATED v2 — Major Rewrite)

> **Copy from here to END TASK B-05**

```
You are a Senior PySide6 UI Developer.

TASK: Build the main window with 3-column layout and all UI components.
ALL TEXT IN ENGLISH. Use Deep Navy color theme. No Thai text anywhere.
This is a BIG task. Read carefully.

REFERENCE: BigEye_Pro_Frontend_Design_v3_FINAL.md
PROTOTYPE: BigEye_Pro_v4.jsx (React prototype for visual reference)

═══════════════════════════════════════
main_window.py — class MainWindow(QMainWindow)
═══════════════════════════════════════
- Window: 1400×800, min 1200×700
- Title: "BigEye Pro"
- Layout: QHBoxLayout → Sidebar(270px) | Center(stretch) | Inspector(300px)
- Top: CreditBar (custom QWidget, 48px height)
- Bottom: QStatusBar (22px, "Ready" left, "v2.0.0" right)
- On startup (parallel):
  1. POST /system/check-update → UpdateDialog if needed
  2. JournalManager.recover_on_startup() → RecoveryDialog if found
  3. GeminiEngine.cleanup_orphaned_caches()
  4. GET /credit/balance → update CreditBar
- Keyboard shortcuts: Ctrl+O (open), Ctrl+Enter (start/stop), Ctrl+S (export),
  Ctrl+R (refresh), Ctrl+T (topup), Ctrl+H (history), Escape (stop)

═══════════════════════════════════════
credit_bar.py — class CreditBar(QWidget) [48px top bar]
═══════════════════════════════════════
Background: linear-gradient(90deg, #16213E, #1A1A2E)
Border bottom: 1px solid #1A3A6B

Layout (left to right):
  "BIGEYE" — 14px weight 800, gradient text
  Vertical divider — 1px line
  "💰 1,200" — gold #FFD700, 14px bold (credit number only, NO BAHT)
  "credits" — dim text #4A5568, 11px
  [Top Up] — chip button, gold tint (#FFD70015 bg, #FFD700 text)
  [↻] — chip button, refresh
  [History] — chip button, opens HistoryDialog
  <spacer>
  "Somchai J." — secondary text #8892A8, 12px
  [Logout] — chip button, dim

Auto-refresh: QTimer every 5 minutes
Low credit (< 50): balance text turns #FF4560

CRITICAL: Credit display ONLY HERE. NOT in sidebar.

═══════════════════════════════════════
sidebar.py — class Sidebar(QWidget) [270px fixed]
═══════════════════════════════════════
NO CREDIT SECTION. Sidebar starts with API Key.
Section dividers: [─── SECTION TITLE ───] horizontal lines with centered text

1. ─── API KEY ───
   QLineEdit password mode, placeholder "Google Gemini API Key"
   [💾 Save] [🗑 Clear] — ghost buttons WITH THEMED HOVER:
     Default: transparent bg, border #1A3A6B, text #8892A8
     Hover: bg gradient(#FF00CC18→#7B2FFF18), border #FF00CC66, text #FF00CC,
            translateY(-1px), shadow 0 4px 12px #FF00CC15
   Save: keyring.set_password("BigEyePro", "gemini_api_key", key)
   Clear: keyring.delete_password + clear input

2. ─── AI SETTINGS ───
   Model QComboBox: gemini-2.5-pro (default), gemini-2.5-flash, gemini-2.0-flash
   Platform QComboBox: "iStock (3 cr/file)", "Adobe & Shutterstock (2 cr/file)"
   Keyword Style QComboBox: "Hybrid (Phrase & Single)", "Single Words"
     → VISIBLE ONLY when Platform = "Adobe & Shutterstock"

3. ─── METADATA ───
   Sliders with gradient fill track and #FF00CC handle:
   Keywords: min=10, max=50, default=45
   Title Length: min=50, max=200, default=70
   Description: min=100, max=500, default=200
   Each: custom slider with value label synced

4. [📋 Debug Log] — ghost button at bottom

Signal: settings_changed(dict)
Lock ALL during processing.

═══════════════════════════════════════
gallery.py — class Gallery(QWidget) [stretch]
═══════════════════════════════════════
TOOLBAR:
  [📂 Open Folder] ghost button + path (read-only, #16213E bg) + "📸9 🎬3" stats

GALLERY GRID:
  QListWidget IconMode, 130×130 thumbnails, border-radius 10px
  REAL IMAGE THUMBNAILS loaded from actual files (async via QThread)
  Video: show first frame + ▶ play overlay circle
  Bottom gradient on each: filename + "IMG"/"VID" badge
  Status overlays:
    Pending: type badge only
    Processing: 2px #FEB019 border + spinner animation + "Processing" text
    Completed: green circle ✓ top-right with shadow glow
    Error: red circle ✕ top-right, image dimmed + desaturated
  Selected: 2px #FF00CC border + shadow glow #FF00CC33

COST ESTIMATE BAR:
  Background: #16213E88
  "📁 12 files · ≈ 36 credits · (iStock × 3) · ✓ Sufficient"
  Insufficient: text turns #FF4560 + "✕ Insufficient"
  Recalculates on: folder change, platform change

ACTION BAR:
  Progress text + 6px gradient progress bar + percentage
  [START] — gradient pill, 220px wide, 14px bold
  [STOP] — replaces START during processing, solid #FF4560

Signals: file_selected, start_requested, stop_requested, folder_changed

═══════════════════════════════════════
inspector.py — class Inspector(QWidget) [300px fixed]
═══════════════════════════════════════
PREVIEW: 190px height, border-radius 10px, REAL IMAGE from file
  Video: first frame + ▶ overlay
  Status badge: "✓ Done" (green) / "Error" (red) top-right

FILE INFO: filename (bold), type (📷/🎬), token usage (only after processing)

EDIT FIELDS (visible when completed):
  Title: QLineEdit, 12px
  Description: QTextEdit, 3 rows, 12px
  Keywords: QTextEdit, 5 rows, 11px, comma-separated
  Edits auto-save to in-memory dict on focus-out

Other states: Processing → amber text, Error → red box, Pending → dim text

[💾 Export CSV] — ghost button with blue tint (#00B4D812 bg, #00B4D8 text)
  WITH themed hover effect
  On click → opens ExportCsvDialog (NOT direct export)

NO WARNING BANNER IN INSPECTOR. Warning is only in ExportCsvDialog.

ACCEPTANCE CRITERIA:
✅ Deep Navy theme throughout (#1A1A2E, not black)
✅ ALL text in English
✅ NO credit section in sidebar — only in Top Bar
✅ Top Bar shows credit number only (no baht)
✅ Ghost buttons have themed gradient hover effect
✅ Gallery shows real image thumbnails (async loaded)
✅ Cost estimate bar shows and recalculates
✅ Keyword Style hides/shows based on Platform
✅ Export CSV opens dialog (not direct save)
```

> **END TASK B-05**

---

## [Task B-05b] All Dialogs (NEW in v2)

> **Copy from here to END TASK B-05b**

```
You are a Senior PySide6 UI Developer.

TASK: Create all dialog windows. ALL TEXT IN ENGLISH. Deep Navy theme.
All dialogs: dark background #1A1A2E, border #1A3A6B, rounded 16px, shadow.
Info cards inside dialogs: background #16213E, rounded 10px.

═══════════════════════════════════════
confirm_dialog.py — class ConfirmDialog(QDialog)
═══════════════════════════════════════
Title: "Confirm Processing"
Width: 400px
Content:
  InfoCard: Files (count + breakdown), Model, Platform
  InfoCard: Cost (gold), After deduction
Buttons: [Start] gradient pill + [Cancel] ghost
Returns: accepted or rejected

═══════════════════════════════════════
insufficient_dialog.py — class InsufficientDialog(QDialog)
═══════════════════════════════════════
Title: "⚠️ Insufficient Credits"
Width: 420px
Content:
  Required: X credits
  Available: Y credits
  Shortfall: Z credits
Buttons (stacked):
  [Top Up] → opens TopUpDialog
  [Process N files (partial)] → returns partial count
  [Cancel]
Logic: max_files = floor(balance / rate)

═══════════════════════════════════════
export_csv_dialog.py — class ExportCsvDialog(QDialog)
═══════════════════════════════════════
Title: "💾 Export CSV"
Width: 440px
Content:
  WARNING BOX (amber gradient bg #FEB01912, border #FEB01933, rounded 12px):
    Icon: ⚠️ (28px)
    Title: "Please Review Before Uploading" — 13px bold, amber
    Body: "AI-generated metadata may contain errors or inaccuracies.
           We strongly recommend reviewing all titles, descriptions,
           and keywords before submitting to stock platforms to ensure
           the best acceptance rates and avoid potential rejections."
  CHECKLIST (3 items, checkbox style):
    □ Titles accurately describe the content
    □ Descriptions are relevant and detailed
    □ Keywords don't contain trademarked terms
Buttons: [Export CSV] gradient pill + [Cancel] ghost
On export: QFileDialog save → save CSV → show success toast

═══════════════════════════════════════
summary_dialog.py — class SummaryDialog(QDialog)
═══════════════════════════════════════
Title: "✅ Processing Complete"
Width: 440px
Content:
  InfoCard "RESULTS": Successful (green), Failed (red), Breakdown (photos/videos)
  InfoCard "CREDITS": Charged, Refunded (+green), Net cost, Balance (gold)
  InfoCard "CSV FILES": list of created CSVs with ✅
  Small note at bottom: "💡 Remember to review all metadata before uploading.
    AI results may need manual adjustments for best acceptance rates."
Button: [Close] ghost

═══════════════════════════════════════
history_dialog.py — class HistoryDialog(QDialog)
═══════════════════════════════════════
Title: "📜 Credit History"
Width: 520px
Content:
  QTableWidget: Date | Transaction | Amount
  Scrollable, max height 300px
  Green for positive, red for negative amounts
  Bottom bar: "Balance: X,XXX credits" in gradient subtle bg
Button: [Close]
Data: GET /credit/history

═══════════════════════════════════════
topup_dialog.py — class TopUpDialog(QDialog)
═══════════════════════════════════════
Title: "🪙 Top Up Credits"
Width: 460px
Content:
  InfoCard: Bank details, account, "Rate: 1 THB = 4 Credits"
  Drop zone: dashed border #264773, "Drop payment slip here / click to browse"
  Amount input: [___] THB
  [Submit Slip] gradient pill button
  Status: ⏳ Verifying / ✅ Added / ❌ Invalid
On submit: base64 encode → POST /credit/topup

═══════════════════════════════════════
update_dialog.py — class UpdateDialog(QDialog)
═══════════════════════════════════════
OPTIONAL: "🆕 Update Available" + version + [Update Now] [Skip]
FORCE: "⚠️ Update Required" + version + [Download Update] (no close)

═══════════════════════════════════════
recovery_dialog.py — class RecoveryDialog(QDialog)
═══════════════════════════════════════
"⚠️ Unfinished Job Found"
Shows: mode, file count, completed, credits reserved, refund amount
Auto-calls POST /job/finalize
Button: [OK]

═══════════════════════════════════════
maintenance_dialog.py — class MaintenanceDialog(QDialog)
═══════════════════════════════════════
"🔧 Server Maintenance"
"The server is temporarily unavailable. Please try again later."
Button: [OK]

ACCEPTANCE CRITERIA:
✅ All 9 dialogs render correctly with Deep Navy theme
✅ All text in English
✅ ExportCsvDialog has warning box + 3-item checklist (no video timecode item)
✅ SummaryDialog has small reminder note (not full warning)
✅ HistoryDialog table color-codes amounts
✅ TopUpDialog has drag-drop area
✅ All dialogs use Info Card style (#16213E bg, rounded 10px)
```

> **END TASK B-05b**

---

## [Task B-06] Gemini Engine (UNCHANGED)

> **Copy from original v1 — Task B-06 is identical.**
> Gemini API, context caching, error classification — no UI involved.

---

## [Task B-07] Keyword Processor (UNCHANGED)

> **Copy from original v1 — Task B-07 is identical.**
> NLTK stemming, dedup, irregular words — no UI involved.

---

## [Task B-08] Supporting Modules (UNCHANGED)

> **Copy from original v1 — Task B-08 is identical.**
> Transcoder, CopyrightGuard, CSVExporter — no UI involved.

---

## [Task B-09] Job Manager, Queue & Journal (UPDATED v2 — English dialogs)

> **Copy from here to END TASK B-09**

```
TASK: Implement the orchestration layer that ties everything together.

═══ FILE: client/core/job_manager.py ═══
class JobManager(QObject):
  Signals: progress_updated(int,int,str), file_completed(str,dict),
           job_completed(dict), job_failed(str), credit_updated(int)

  start_job(files, settings):
    1. Calculate cost, pre-check balance
       If insufficient: show InsufficientDialog (ENGLISH):
         "Required: X credits | Available: Y | Shortfall: Z"
         Options: [Top Up] [Process N files] [Cancel]
    2. If sufficient: show ConfirmDialog (ENGLISH):
         "Files: 24 (20 photos, 4 videos) | Model: gemini-2.5-pro | Platform: iStock"
         "Cost: 72 credits | After deduction: 1,128 credits"
         [Start] [Cancel]
    3. api.reserve_job() → get job_token + encrypted config
    4. Decrypt prompts with AES
    5. Download dictionary (if iStock)
    6. CopyrightGuard.initialize(blacklist)
    7. Create Context Cache if files >= threshold
    8. Create video proxies
    9. JournalManager.create_journal()
    10. Process files via QueueManager
    11. Post-process keywords via KeywordProcessor
    12. On each file: JournalManager.update_progress()
    13. On complete/stop: api.finalize_job() → get refund
    14. Show SummaryDialog (ENGLISH)
    15. CSVExporter.export()
    16. Play completion sound (assets/sounds/complete.wav)
    17. Cleanup: delete cache, guard.clear(), delete proxies, delete journal
    18. Emit job_completed

  stop_job(): Set flag, finalize partial results

═══ FILE: client/core/managers/queue_manager.py ═══
class QueueManager(QObject):
  Uses QThreadPool + QRunnable
  Image: max 5 concurrent (from server config)
  Video: max 2 concurrent
  QSemaphore per type
  Emits progress after each file

═══ FILE: client/core/managers/journal_manager.py ═══
class JournalManager:
  JOURNAL_PATH = ~/.bigeye/recovery.json
  create_journal(job_token, file_count, mode, credit_rate)
  update_progress(success: bool, is_video: bool)
  read_journal() → Optional[dict]
  delete_journal()
  recover_on_startup(api_client) → Optional[dict]:
    If recovery.json exists → api.finalize_job → get refund → delete json
    Return recovery summary message (ENGLISH)

ACCEPTANCE CRITERIA:
✅ Full Reserve→Process→Finalize flow works end-to-end
✅ All dialog text in ENGLISH
✅ Concurrent processing respects limits (5 image, 2 video)
✅ Crash recovery auto-finalizes and refunds
✅ Completion sound plays
✅ Context cache created for ≥20 files, deleted after job
```

> **END TASK B-09**

---

## [Task B-10] Nuitka Build & Integration Testing (UPDATED v2)

> **Copy from here to END TASK B-10**

```
TASK: Create build script and verify complete flow.

═══ FILE: client/build/build_nuitka.py ═══
Nuitka command:
  --standalone --onefile
  --enable-plugin=pyside6
  --include-data-dir=assets=assets
  --include-package=nltk
  --include-data-dir=assets/nltk_data=nltk_data
  --windows-icon-from-ico=assets/icons/app_icon.ico
  --windows-product-name="BigEye Pro"
  --windows-file-version=2.0.0
  --output-dir=dist --output-filename=BigEyePro

═══ INTEGRATION TEST SCENARIOS ═══

TEST 1: Full Happy Path (iStock)
  Register → Top up → 10 images iStock → ConfirmDialog → Process → SummaryDialog → ExportCsvDialog

TEST 2: Adobe Hybrid
  5 images → Reserve → Hybrid keywords → CSV for Adobe + Shutterstock

TEST 3: Partial Failure + Refund
  20 images → 15 ok + 5 fail → Refund shown in SummaryDialog

TEST 4: Insufficient Credits
  Low balance → InsufficientDialog with 3 options

TEST 5: Crash Recovery
  Kill at 10/20 → restart → RecoveryDialog → auto-refund

TEST 6: Device Mismatch
  Login on different machine → "Device mismatch" error in AuthWindow

TEST 7: CSV Export Warning
  ExportCsvDialog shows → warning + checklist → export succeeds

TEST 8: UI Theme Verification
  ALL backgrounds are #1A1A2E (deep navy, not black)
  ALL text is English (no Thai anywhere)
  Ghost buttons have themed hover effect
  Credit only in Top Bar (not in sidebar)

FINAL ACCEPTANCE CRITERIA:
✅ All 8 scenarios pass
✅ Deep Navy theme correct (#1A1A2E, #16213E, #0F3460)
✅ All text English
✅ No credit in sidebar
✅ Ghost button hover: gradient bg + accent border + accent text
✅ CSV export goes through ExportCsvDialog (not direct save)
✅ Memory stable during 100+ files
✅ Nuitka produces standalone .exe
```

> **END TASK B-10**

---

# ═══════════════════════════════════════════
# CHANGE SUMMARY: v1 → v2
# ═══════════════════════════════════════════

| Task | Status | What Changed |
|------|--------|-------------|
| A-01 to A-10 | UNCHANGED | Backend is language-agnostic |
| B-01 | UPDATED | New folder structure (10 dialog files), Deep Navy colors, sounds/ folder |
| B-02 | UNCHANGED | Security module has no UI |
| B-03 | UPDATED | Config colors changed to Deep Navy palette |
| B-04 | UPDATED | English UI, Deep Navy, error messages in English |
| B-05 | MAJOR REWRITE | English, no credit in sidebar, 270px sidebar, 300px inspector, themed hover, cost bar, real thumbnails |
| B-05b | NEW | All 9 dialogs as separate task (was bundled in B-05) |
| B-06 | UNCHANGED | Gemini engine has no UI |
| B-07 | UNCHANGED | Keyword processor has no UI |
| B-08 | UNCHANGED | Transcoder/Guard/CSV has no UI |
| B-09 | UPDATED | English dialog text, completion sound |
| B-10 | UPDATED | Added Test 7 (CSV warning) and Test 8 (theme verification) |

---

*AI IDE Tasks v2 — Aligned with Frontend Design v3 FINAL*
