# BigEye Pro — AI IDE Skill

> This skill provides project-specific context for AI coding agents working on BigEye Pro.
> It prevents common mistakes, enforces design decisions, and ensures consistency.

---

## PROJECT OVERVIEW

BigEye Pro is a **PySide6 desktop application** (Windows/macOS) that generates SEO-optimized metadata (titles, descriptions, keywords) for stock photography platforms using Google Gemini AI.

**Business model:** Pay-as-you-go credit system. Users top up credits → credits are deducted per file processed.

**Architecture:**
```
Desktop Client (PySide6 + Nuitka)  ←→  Backend API (FastAPI + Firestore)
         ↓                                        ↓
   Google Gemini API                     Firebase / Cloud Run
   (user's own key)                      (admin managed)
```

---

## TECH STACK — DO NOT DEVIATE

| Layer | Technology | Version |
|:--|:--|:--|
| Desktop UI | **PySide6** | 6.7.0 |
| AI Engine | **google-generativeai** | 0.8.0 |
| HTTP Client | **httpx** | 0.27.0 |
| Image Processing | **opencv-python-headless** + **Pillow** | 4.10 / 10.4 |
| NLP | **nltk** | 3.9.0 |
| Data Export | **pandas** | 2.2.0 |
| Secrets | **keyring** | 25.3.0 |
| Encryption | **pycryptodome** | 3.21.0 |
| Backend | **FastAPI** + **firebase-admin** | — |
| Database | **Firestore** (Native Mode) | — |
| Build | **Nuitka** (standalone .exe) | — |

**NEVER suggest:** Electron, React, Tkinter, PyQt5, Django, SQLite, PostgreSQL, MongoDB.

---

## PROJECT STRUCTURE

```
BigEye_Desktop_App/
├── client/
│   ├── main.py                          # Entry point, QApplication
│   ├── requirements.txt
│   ├── assets/
│   │   ├── icons/
│   │   ├── sounds/complete.wav
│   │   └── nltk_data/
│   ├── ui/
│   │   ├── auth_window.py               # Login/Register dialog
│   │   ├── main_window.py               # Main 3-column window
│   │   └── components/
│   │       ├── sidebar.py               # Left panel (270px)
│   │       ├── gallery.py               # Center grid (stretch)
│   │       ├── inspector.py             # Right panel (300px)
│   │       ├── credit_bar.py            # Top bar (48px)
│   │       ├── confirm_dialog.py
│   │       ├── insufficient_dialog.py
│   │       ├── export_csv_dialog.py     # Re-export with warning
│   │       ├── summary_dialog.py
│   │       ├── history_dialog.py
│   │       ├── topup_dialog.py
│   │       ├── update_dialog.py
│   │       ├── recovery_dialog.py
│   │       └── maintenance_dialog.py
│   ├── core/
│   │   ├── api_client.py                # httpx → Backend API
│   │   ├── auth_manager.py              # JWT + keyring
│   │   ├── job_manager.py               # Reserve→Process→Finalize
│   │   ├── config.py                    # Constants (NO hardcoded rates)
│   │   ├── engines/
│   │   │   ├── gemini_engine.py         # Gemini API + Context Caching
│   │   │   └── transcoder.py            # FFmpeg video proxy
│   │   ├── logic/
│   │   │   ├── keyword_processor.py     # NLTK stemming, dedup
│   │   │   └── copyright_guard.py       # Blacklist filter
│   │   ├── managers/
│   │   │   ├── queue_manager.py         # QThreadPool concurrency
│   │   │   └── journal_manager.py       # Crash recovery
│   │   └── data/
│   │       └── csv_exporter.py          # 3-format CSV export
│   ├── utils/
│   │   ├── security.py                  # Hardware ID, AES, keyring
│   │   ├── helpers.py                   # File utils
│   │   ├── video_thumb.py              # FFmpeg first frame
│   │   └── logger.py                    # ~/.bigeye/debug_log.txt
│   └── build/
│       └── build_nuitka.py
├── server/                              # FastAPI backend
└── Design_Specification/                # All design docs
```

---

## THEME & COLORS — CRITICAL

**Theme name:** Deep Navy

```
BACKGROUNDS:
  Main background:    #1A1A2E    ← NOT #1E1E1E, NOT #000000
  Surface/cards:      #16213E
  Surface alt:        #0F3460
  
BORDERS:
  Primary:            #1A3A6B
  Light:              #264773

TEXT:
  Primary:            #E8E8E8
  Secondary:          #8892A8
  Dim/disabled:       #4A5568

ACCENT (gradient):
  From:               #FF00CC    ← Magenta/Pink
  To:                 #7B2FFF    ← Purple
  ⚠️ NOT #3333FF (that was v1, now outdated)

SEMANTIC:
  Success:            #00E396
  Warning:            #FEB019
  Error:              #FF4560
  Credit/Gold:        #FFD700
  Info/Cyan:          #00B4D8
```

**COMMON MISTAKES TO AVOID:**
- ❌ `#1E1E1E` — This is the OLD color, use `#1A1A2E`
- ❌ `#3333FF` — This is the OLD accent, use `#7B2FFF`
- ❌ `#2D2D2D` — Never existed in v3, use `#16213E`
- ❌ Black backgrounds — Always use Deep Navy tones

---

## STYLING RULES — NO QSS FILE

This project does **NOT** use a global `dark_theme.qss` file. All styles are applied **inline** on each widget via `.setStyleSheet()`.

### Ghost Buttons (default for all buttons)
```python
button.setStyleSheet("""
    QPushButton {
        background: transparent;
        border: 1px solid #1A3A6B;
        border-radius: 8px;
        padding: 7px 14px;
        color: #8892A8;
        font-weight: 500;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 #FF00CC18, stop:1 #7B2FFF18);
        border-color: #FF00CC66;
        color: #FF00CC;
    }
    QPushButton:disabled {
        color: #4A5568;
        border-color: #1A3A6B44;
    }
""")
```

### Gradient Pill Buttons (START, Sign In, Confirm)
```python
button.setStyleSheet("""
    QPushButton#startButton {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 #FF00CC, stop:1 #7B2FFF);
        border: none;
        border-radius: 22px;
        padding: 12px 30px;
        color: #FFFFFF;
        font-size: 14px;
        font-weight: 700;
    }
""")
```

### ComboBox with Hover
```python
COMBO_STYLE = """
    QComboBox { background: #16213E; border: 1px solid #1A3A6B; border-radius: 8px; padding: 10px 12px; color: #E8E8E8; }
    QComboBox QAbstractItemView { background: #16213E; border: 1px solid #1A3A6B; padding: 4px; outline: none; }
    QComboBox QAbstractItemView::item { color: #8892A8; padding: 8px 12px; border-radius: 4px; }
    QComboBox QAbstractItemView::item:hover {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #FF00CC18, stop:1 #7B2FFF18);
        color: #FF00CC;
    }
"""
```

### Info Cards (inside dialogs)
```python
card.setStyleSheet("background: #16213E; border-radius: 10px; padding: 14px;")
```

---

## UI LANGUAGE — ENGLISH ONLY

**ALL user-facing text MUST be in English.** No Thai text anywhere in the client UI.

- ✅ "Sign In", "Create Account", "Top Up", "Processing Complete"
- ❌ "เข้าสู่ระบบ", "สมัครสมาชิก", "เติมเงิน"

**Exception:** Admin Dashboard and internal documentation can be bilingual.

---

## LAYOUT RULES

```
┌─────────────────────────────────────────────────────┐
│ CreditBar (48px) — BIGEYE + credits + TopUp + user  │
├──────────┬─────────────────────────┬────────────────┤
│ Sidebar  │       Gallery           │   Inspector    │
│ (270px)  │      (stretch)          │   (300px)      │
│ fixed    │                         │   fixed        │
├──────────┴─────────────────────────┴────────────────┤
│ StatusBar (22px)                                     │
└─────────────────────────────────────────────────────┘
```

**CRITICAL LAYOUT RULES:**
1. Credit display is ONLY in CreditBar (top) — NOT in Sidebar
2. CreditBar shows credit NUMBER only — NO baht conversion displayed
3. Sidebar starts with API Key section (no credit section)
4. Gallery has cost estimate bar between grid and action bar
5. Inspector "Export CSV" button is labeled **"Re-export CSV"** (auto-save happens first)

---

## CREDIT SYSTEM

```
Reserve → Process → Finalize (with refund)

1. Client calculates cost: files × rate_per_file
2. Server reserves credits (deducts upfront)
3. Client processes files with Gemini AI
4. Server finalizes: refunds credits for failed files
```

**Rates are DYNAMIC** — fetched from server via `GET /credit/balance`, NOT hardcoded:
```python
# ❌ WRONG — hardcoded rates
CREDIT_RATES = {"iStock": 3, "Adobe": 2}

# ✅ CORRECT — from server response
rates = api.get_balance()["rates"]  # {"istock_photo": 3, "adobe_photo": 2, ...}
```

---

## CSV EXPORT FLOW

```
Job completes → CSV auto-saved immediately → SummaryDialog shows paths
                                           ↓
              User can edit metadata in Inspector
                                           ↓
              User clicks [🔄 Re-export CSV] → ExportCsvDialog (warning + checklist) → new CSV
```

- **Auto-save:** Happens automatically after job finishes. Always creates CSV.
- **Re-export:** Manual button for regenerating CSV after editing metadata.
- The button label is "🔄 Re-export CSV", NOT "💾 Export CSV"
- Re-export button is DISABLED until a job has completed

---

## CONCURRENCY PATTERNS

Use **QThread + QThreadPool + QRunnable** for async work. NEVER use `asyncio` in the PySide6 client.

```python
# ✅ CORRECT — QThreadPool for parallel file processing
pool = QThreadPool()
pool.setMaxThreadCount(5)  # images
# Separate semaphore for videos (max 2)

# ✅ CORRECT — QThread for single async operations
class ApiWorker(QThread):
    result = Signal(dict)
    def run(self):
        data = api.get_balance()
        self.result.emit(data)

# ❌ WRONG — Never use asyncio in PySide6
async def fetch_balance():  # This will break the event loop
```

---

## SIGNAL/SLOT PATTERNS

Components communicate via Qt Signals, NOT direct method calls:

```python
# ✅ CORRECT
self.sidebar.platform_changed.connect(self._on_platform_changed)
self.gallery.file_selected.connect(self.inspector.show_file)

# ❌ WRONG — tight coupling
self.gallery.inspector = self.inspector  # Don't pass references
```

---

## FILE PROCESSING PIPELINE

```
For each file:
1. Read image/video → encode base64 (or create video proxy via FFmpeg)
2. Fill prompt template: replace {media_type_str}, {keyword_count}, etc.
3. Send to Gemini API (with Context Cache if ≥20 files)
4. Parse JSON response → extract title, description, keywords
5. Post-process keywords:
   - iStock: filter against Dictionary (only dictionary words allowed)
   - Adobe/Shutterstock: NLTK stemming dedup (no both "run" and "running")
6. Copyright guard: remove blacklisted terms
7. Store result in memory dict
8. Update gallery thumbnail status overlay
9. Update journal (crash recovery)
```

---

## COMMON PITFALLS — AI IDE MUST AVOID

### 1. Style not applying
**Problem:** `setObjectName("startButton")` set but no QSS loaded.
**Solution:** Always use inline `.setStyleSheet()` with `#objectName` selector.

### 2. QComboBox dropdown invisible
**Problem:** Default dark theme makes dropdown items invisible.
**Solution:** Apply `COMBO_STYLE` with explicit hover colors.

### 3. QLineEdit for Title
**Problem:** Titles are 60-200 chars, QLineEdit shows only 1 line.
**Solution:** Use `QTextEdit` with `setFixedHeight(56)` for ~2 lines.

### 4. Blocking the UI thread
**Problem:** API calls or Gemini processing on main thread freezes UI.
**Solution:** Always use QThread/QThreadPool for network/AI operations.

### 5. Hardcoded credit rates
**Problem:** Rates change via Admin Dashboard, hardcoded values become stale.
**Solution:** Always read rates from `GET /credit/balance` response.

### 6. Thai text in UI
**Problem:** Some error messages or labels still in Thai from legacy code.
**Solution:** ALL client-facing text must be English. Check every string.

### 7. Wrong gradient colors
**Problem:** Using old accent `#3333FF` instead of current `#7B2FFF`.
**Solution:** Always use `#FF00CC → #7B2FFF` for gradients.

---

## API ENDPOINTS REFERENCE

```
Auth:
  POST /auth/register    — { email, password, name, phone, hardware_id }
  POST /auth/login       — { email, password, hardware_id }

Credits:
  GET  /credit/balance   — Returns { credits, rates, exchange_rate, active_promos }
  POST /credit/topup     — { slip_base64, amount, promo_code? }
  GET  /credit/history   — ?limit=50

Jobs:
  POST /job/reserve      — { file_count, mode, keyword_style, model, version }
                           Returns { job_token, config: { prompt(encrypted), dictionary, blacklist, ... } }
  POST /job/finalize     — { job_token, success, failed, photos, videos }

System:
  GET  /system/check-update   — { current_version }
  GET  /system/health
```

**Error codes:** 401=Auth, 402=InsufficientCredits, 403=Forbidden, 409=Conflict, 426=UpdateRequired, 429=RateLimit, 503=Maintenance

---

## TESTING CHECKLIST

When implementing or modifying any feature, verify:

- [ ] Deep Navy theme correct (`#1A1A2E` background, not black)
- [ ] All text in English
- [ ] Ghost buttons have themed hover effect
- [ ] Gradient pill buttons render correctly (not system default)
- [ ] ComboBox dropdowns have visible hover highlight
- [ ] Credit only in Top Bar (not in Sidebar)
- [ ] No blocking calls on main thread
- [ ] Signals used for component communication
- [ ] Credit rates read from server (not hardcoded)
- [ ] Error messages are user-friendly English

---

*BigEye Pro Custom Skill — v1.0*
*Last updated: February 2026*
