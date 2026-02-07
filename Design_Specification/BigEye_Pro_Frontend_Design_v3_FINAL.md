# BigEye Pro — Frontend Design Specification v3.0 (FINAL)
### Desktop Edition | PySide6 + Firebase Backend
### Date: February 2026 | Status: FINAL — Ready for AI IDE
### Changelog: v2→v3: English UI, sidebar credit removed, hover effects, CSV warning, color unification

---

## 1. Project Overview

Build a professional desktop app for generating metadata (Title, Description, Keywords) for stock photos/videos using Google Gemini AI.

**Architecture:** Client-Server (Pay-per-use Credit System)
- Client = PySide6 Desktop → AI processing runs client-side (user's own API key)
- Server = FastAPI + Firestore → manages Users, Credits, Prompts, Security
- Security: Client has no prompts/logic until credits are paid → Server sends encrypted config

**Target Users:** Thai stock photographers/videographers, 100–1,000 users
**UI Language:** English throughout (all labels, buttons, messages, dialogs)

---

## 2. Tech Stack

| Layer | Technology | Notes |
|:--|:--|:--|
| Language | Python 3.10+ | — |
| UI Framework | PySide6 (Qt 6) | QThread worker pattern, no UI freeze |
| AI | google-generativeai | Client-side, user's API key |
| HTTP Client | httpx | Sync client to backend API |
| Video | FFmpeg (subprocess) | Proxy creation 480p |
| Image | Pillow | Thumbnail, resize |
| Keyword | NLTK (SnowballStemmer) | Pre-bundled data, no runtime download |
| CSV | pandas | 3 platform formats |
| Security | keyring, PyCryptodome | API key storage, AES decrypt |
| Compilation | Nuitka (Standalone, Onefile) | Source protection |

---

## 3. Application Flow

```
[App Launch]
    │
    ├─ Has saved JWT token? ──No──→ [Auth Window] ──success──→ [Main Window]
    │                                    │
    │                                  cancel → [Exit]
    │
    └─ Yes (token valid) ───────────────→ [Main Window]
                                              │
                                   ┌──────────┼──────────┐
                                   │          │          │
                            [Check Update] [Recover] [Cleanup]
                                   │      Journal   Orphaned
                                   │                 Caches
                                   ▼
                            [Ready to Work]
```

### Startup Sequence:
1. Load QSS theme
2. Check saved JWT token in keyring
3. If no token → show AuthWindow (Login/Register)
4. If token → verify expiry → if expired → AuthWindow
5. Enter MainWindow
6. Parallel on startup:
   - `POST /system/check-update` → show UpdateDialog if needed
   - `JournalManager.recover_on_startup()` → show RecoveryDialog if found
   - `GeminiEngine.cleanup_orphaned_caches()` → delete stale caches
   - `GET /credit/balance` → update Top Bar

---

## 4. Design System

### 4.1 Color Palette (Deep Navy Theme)

```
BACKGROUNDS:
  Primary:         #1A1A2E    (main window background)
  Surface:         #16213E    (panels, inputs, cards)
  Surface Alt:     #0F3460    (elevated elements)

BORDERS:
  Default:         #1A3A6B
  Light:           #264773
  Focus/Active:    #FF00CC    (accent)

TEXT:
  Primary:         #E8E8E8
  Secondary:       #8892A8
  Dim/Disabled:    #4A5568

ACCENT (Gradient):
  Start:           #FF00CC    (magenta)
  End:             #7B2FFF    (purple)
  Usage:           Primary buttons, START button, active states, logo

SEMANTIC:
  Success:         #00E396    (green — completed, balance OK)
  Warning:         #FEB019    (amber — processing, caution)
  Error:           #FF4560    (red — failed, stop)
  Credit:          #FFD700    (gold — balance display)
  Info/Export:     #00B4D8    (cyan — Export CSV button)
```

### 4.2 Typography

```
Primary Font:     "Segoe UI" (Windows), fallback sans-serif
Sizes:
  Default body:   13px
  Labels:         11px
  Section titles: 10px uppercase, letter-spacing 1.2
  Top bar credit: 14px bold
  Logo:           22px weight 900, gradient text
  START button:   14px bold, letter-spacing 1
Weights:
  Normal:         400 (body text)
  Medium:         500 (labels, secondary buttons)
  Bold:           600-700 (values, primary buttons)
  Black:          900 (logo only)
```

### 4.3 Component Styles

**Input Fields (QLineEdit, QTextEdit, QComboBox):**
```css
background: #16213E;
border: 1px solid #1A3A6B;
border-radius: 8px;
padding: 10px 12px;
color: #E8E8E8;
/* Focus state: */
border-color: #FF00CC;
```

**Ghost Buttons (Save, Clear, Open Folder, Debug Log, Export CSV):**
```css
/* DEFAULT state: */
background: transparent;
border: 1px solid #1A3A6B;
border-radius: 8px;
padding: 7px 14px;
color: #8892A8;
font-size: 12px;
font-weight: 500;

/* HOVER state (IMPORTANT — themed hover): */
background: linear-gradient(135deg, #FF00CC18, #7B2FFF18);
border-color: #FF00CC66;
color: #FF00CC;
transform: translateY(-1px);
box-shadow: 0 4px 12px #FF00CC15;
transition: all 0.2s ease;
```

**Pill Button (START, Sign In, Create Account, dialog confirms):**
```css
background: linear-gradient(135deg, #FF00CC, #7B2FFF);
border: none;
border-radius: 22px;
padding: 11px 24px;
color: #FFFFFF;
font-weight: 700;
font-size: 13px;
letter-spacing: 0.5px;
```

**Chip Buttons (Top Up, Refresh, History, Logout in Top Bar):**
```css
background: transparent;
border: 1px solid #1A3A6B;
border-radius: 6px;
padding: 4px 10px;
color: #8892A8;
font-size: 11px;
/* Top Up special: */
background: #FFD70015;
color: #FFD700;
border-color: #FFD70033;
```

**Section Dividers (sidebar headings):**
```
[────── SECTION TITLE ──────]
Rendered as: horizontal line — text — horizontal line
Font: 10px uppercase, color #8892A8, letter-spacing 1.2
Line: 1px solid #1A3A6B
```

---

## 5. Screen Specifications

### 5.1 Auth Window — `ui/auth_window.py`

**Window:** 400 × auto, centered, dark background (#1A1A2E), rounded 20px, shadow
**Not resizable, frameless optional**

**Layout:**
```
┌────────────────────────────────────┐
│                                    │
│         BIGEYE PRO                 │  ← gradient text 30px, weight 900
│    STOCK METADATA GENERATOR        │  ← dim text 11px
│                                    │
│  ┌───────────┬───────────┐         │
│  │  SIGN IN  │ REGISTER  │         │  ← tab selector
│  └───────────┴───────────┘         │
│                                    │
│  (form fields below)               │
│                                    │
│  [     Sign In / Register    ]     │  ← gradient pill button
│                                    │
└────────────────────────────────────┘
```

**Sign In Tab:**
| Field | Type | Placeholder |
|:--|:--|:--|
| Email | QLineEdit | "Email" |
| Password | QLineEdit (password mode) | "Password" |
| Button | QPushButton (gradient pill) | "Sign In" |

**Register Tab:**
| Field | Type | Validation |
|:--|:--|:--|
| Full Name | QLineEdit | 2-100 chars |
| Email | QLineEdit | Valid email format |
| Phone Number | QLineEdit | 9-15 digits only |
| Password | QLineEdit (password mode) | Min 8 chars |
| Confirm Password | QLineEdit (password mode) | Must match |
| Button | QPushButton (gradient pill) | "Create Account" |

**Tab Selector Style:**
- Active: background `#FF00CC15`, text color `#FF00CC`
- Inactive: transparent, text color `#4A5568`
- Border: 1px solid `#1A3A6B`, rounded 10px

**Error Messages (English):**
| HTTP Code | Message |
|:-:|:--|
| 401 | "Incorrect email or password" |
| 403 | "Device mismatch — this account is bound to another device.\nPlease contact admin." |
| 409 | "This email is already registered" |
| 429 | "Too many attempts, please wait" |
| Network | "Cannot connect to server. Please check your internet." |

**Behavior:**
- API calls run in QThread (show spinner on button during call)
- On success: save JWT to keyring → `self.accept()` → MainWindow opens
- Hardware ID: call `get_hardware_id()` automatically, never shown to user
- Decorative: subtle gradient blur circles behind form (ambient glow)

---

### 5.2 Main Window — `ui/main_window.py`

**Size:** 1400 × 800 default, minimum 1200 × 700
**Title:** `"BigEye Pro"`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ TOP BAR (48px)                                                       │
├────────────┬────────────────────────────────────────┬───────────────┤
│  SIDEBAR   │          CENTER STAGE                   │  INSPECTOR    │
│  270px     │          (stretch)                      │  300px        │
│  fixed     │                                         │  fixed        │
├────────────┴────────────────────────────────────────┴───────────────┤
│ STATUS BAR (22px)                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

**Keyboard Shortcuts:**
| Shortcut | Action |
|:--|:--|
| Ctrl+O | Open Folder |
| Ctrl+Enter | Start / Stop Processing |
| Ctrl+S | Export CSV |
| Ctrl+R | Refresh Credit Balance |
| Ctrl+T | Open Top-Up Dialog |
| Ctrl+H | Open Credit History |
| Escape | Stop Processing (with confirmation) |

---

### 5.3 Top Bar — `ui/components/credit_bar.py`

**Height:** 48px, full width
**Background:** `linear-gradient(90deg, #16213E, #1A1A2E)`
**Border bottom:** 1px solid `#1A3A6B`

```
┌─────────────────────────────────────────────────────────────────────┐
│ BIGEYE  │ 💰 1,200 credits  [Top Up] [↻] [History]    Somchai J. [Logout] │
└─────────────────────────────────────────────────────────────────────┘
```

**Elements (left to right):**
1. **"BIGEYE"** — 14px weight 800, gradient text, letter-spacing 2
2. **Vertical divider** — 1px × 20px, color `#1A3A6B`
3. **💰 1,200** — gold (#FFD700), 14px bold (credit number only, NO baht conversion)
4. **"credits"** — dim text (#4A5568), 11px
5. **[Top Up]** — chip button, gold tint background (`#FFD70015`), gold text
6. **[↻]** — chip button, refresh balance
7. **[History]** — chip button, opens HistoryDialog
8. **Spacer** (flex: 1)
9. **"Somchai J."** — secondary text (#8892A8), 12px
10. **[Logout]** — chip button, dim color

**Behavior:**
- Auto-refresh balance every 5 minutes via QTimer
- Low credit (< 50): balance text turns `#FF4560` (error red)
- Refresh calls `GET /credit/balance`
- Logout: confirm → clear keyring → show AuthWindow

**IMPORTANT: Credit display lives ONLY in Top Bar. Do NOT duplicate in Sidebar.**

---

### 5.4 Left Sidebar — `ui/components/sidebar.py`

**Width:** Fixed 270px
**Padding:** 16px horizontal, 14px vertical
**Scroll:** QScrollArea for overflow
**Separator:** No credit section — starts directly with API Key

```
┌──────────────────────────────┐
│ ────── API KEY ──────        │
│                              │
│ [________________________]   │  ← password mode input
│ [💾 Save]    [🗑 Clear]      │  ← ghost buttons WITH hover effect
│                              │
│ ────── AI SETTINGS ──────    │
│                              │
│ Model                        │
│ [gemini-2.5-pro          ▼]  │
│                              │
│ Platform                     │
│ [iStock (3 cr/file)      ▼]  │
│                              │
│ Keyword Style                │  ← HIDDEN when Platform = iStock
│ [Hybrid (Phrase & Single) ▼] │
│                              │
│ ────── METADATA ──────       │
│                              │
│ Keywords           [──●] 45  │  ← slider + value display synced
│ Title Length        [──●] 70  │
│ Description         [──●] 200│
│                              │
│                              │
│ [📋 Debug Log]               │  ← bottom, ghost button
└──────────────────────────────┘
```

**API Key Section:**
- Input: QLineEdit, password mode, placeholder "Google Gemini API Key"
- Save button: ghost style with **themed hover** (gradient background + accent border)
  - Action: `keyring.set_password("BigEyePro", "gemini_api_key", key)`
- Clear button: ghost style with **themed hover** (same hover as Save)
  - Action: `keyring.delete_password(...)` + clear input
- On startup: auto-load from keyring if exists

**AI Settings:**
- **Model** QComboBox: `gemini-2.5-pro` (default), `gemini-2.5-flash`, `gemini-2.0-flash`
- **Platform** QComboBox: `iStock (3 cr/file)`, `Adobe & Shutterstock (2 cr/file)`
- **Keyword Style** QComboBox: `Hybrid (Phrase & Single)`, `Single Words`
  - **Visibility:** SHOW only when Platform = "Adobe & Shutterstock", HIDE when iStock

**Metadata Sliders:**
| Setting | Min | Max | Default | Step |
|:--|:-:|:-:|:-:|:-:|
| Keywords | 10 | 50 | 45 | 1 |
| Title Length | 50 | 200 | 70 | 5 |
| Description | 100 | 500 | 200 | 10 |

- Implementation: QSlider + value label (synced)
- Slider track: 4px, background `#1A3A6B`, filled portion gradient
- Slider handle: 14px circle, color `#FF00CC`, glow shadow
- **Lock ALL** controls during processing (setEnabled(False))

**Debug Log:** ghost button → opens `~/.bigeye/debug_log.txt` with system default

---

### 5.5 Center Stage — `ui/components/gallery.py`

```
┌──────────────────────────────────────────────────────┐
│ TOOLBAR                                              │
│ [📂 Open Folder] [/Users/.../stock_photos ] 📸9 🎬3  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  GALLERY GRID (real image thumbnails)                │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│  │ img  │ │ img  │ │ img  │ │ vid▶ │               │
│  │  ✓   │ │  ✓   │ │  ⟳  │ │  ✕   │               │
│  │name  │ │name  │ │name  │ │name  │               │
│  └──────┘ └──────┘ └──────┘ └──────┘               │
│  ...                                                 │
│                                                      │
├──────────────────────────────────────────────────────┤
│ COST BAR                                             │
│ 📁 12 files  ≈ 36 credits  (iStock × 3)  ✓ Sufficient│
├──────────────────────────────────────────────────────┤
│ ACTION BAR                                           │
│ Processing 3/12      [████████░░░░] 25%              │
│               [ START ]                              │
└──────────────────────────────────────────────────────┘
```

**Toolbar:**
- [📂 Open Folder] ghost button → `QFileDialog.getExistingDirectory()`
- Path display: read-only text, `#16213E` background, dim text
- Stats: `📸9 🎬3` (auto-counted from folder scan)

**Gallery Grid:**
- QListWidget in IconMode
- **Thumbnail size: 130 × 130 px**, border-radius 10px
- **Real image thumbnails** loaded from actual files (async via QThread)
- Grid spacing: 10px
- Selection: single click → populate Inspector

**Thumbnail Design:**
```
┌──────────────────┐
│ [actual image]   │  ← objectFit: cover, fills entire thumbnail
│                  │
│            [VID] │  ← type badge bottom-right: "IMG" cyan / "VID" purple
│  filename.jpg    │  ← bottom gradient overlay with filename
└──────────────────┘
```

**Video thumbnails:** Show first frame + play button ▶ overlay (circle with triangle)

**Status Overlays:**
| Status | Border | Overlay |
|:--|:--|:--|
| Pending | none | Type badge only (IMG/VID) |
| Processing | 2px solid `#FEB019` | Dark overlay + spinner circle (animated rotation) + "Processing" text |
| Completed | none (or accent if selected) | Green circle ✓ badge top-right, shadow glow |
| Error | none | Red circle ✕ badge top-right, image dimmed + desaturated |

**Selected state:** 2px solid `#FF00CC` + outer glow shadow `0 0 20px #FF00CC33`

**Cost Estimate Bar:**
- Background: `#16213E88`
- Shows: `📁 {count} files · ≈ {cost} credits · ({platform} × {rate}) · ✓ Sufficient` or `✕ Insufficient` (red)
- Recalculates on: folder change, platform change

**Action Bar:**
- Progress: text label + horizontal bar (gradient fill) + percentage
- START button: gradient pill, 220px wide, 14px bold, letter-spacing 1
- STOP button: replaces START during processing, same shape, solid `#FF4560`

**START Button Flow:**
1. Validate: folder? files? API key?
2. Calculate: `estimated_cost = file_count × rate`
3. Compare with balance → Sufficient: ConfirmDialog / Insufficient: InsufficientDialog
4. On confirm → `POST /job/reserve` → get config → BEGIN PROCESSING
5. On complete/stop → `POST /job/finalize` → SummaryDialog

---

### 5.6 Right Inspector — `ui/components/inspector.py`

**Width:** Fixed 300px

```
┌──────────────────────────────┐
│ ┌──────────────────────────┐ │
│ │   (real image preview)   │ │  ← 190px height, objectFit: cover
│ │                    ✓Done │ │  ← status badge on image
│ └──────────────────────────┘ │
│                              │
│ IMG_001.jpg                  │  ← filename bold
│ 📷 Photo  Tokens: 1,234/567 │  ← type + token info
│                              │
│ Title                        │
│ [________________________]   │  ← QLineEdit, editable
│                              │
│ Description                  │
│ [________________________]   │  ← QTextEdit, 3 rows, editable
│ [________________________]   │
│                              │
│ Keywords (43)                │
│ [________________________]   │  ← QTextEdit, 5 rows, comma-separated
│ [________________________]   │
│ [________________________]   │
│                              │
│ [     💾 Export CSV      ]   │  ← ghost button with blue tint + hover
└──────────────────────────────┘
```

**Preview Image:**
- Height: 190px, border-radius 10px, border 1px `#1A3A6B`
- Shows **actual image** from file (scaled to fit)
- Video files: show first frame + ▶ play overlay
- Status badge: "✓ Done" (green) or "Error" (red) top-right corner

**File Info:**
- Filename: bold 12px
- Type: "📷 Photo" or "🎬 Video"
- Token info: "Tokens: {input} / {output}" — visible only after processing

**Edit Fields (visible only when status = completed):**
- Title: QLineEdit, editable, 12px
- Description: QTextEdit, 3 rows, editable, 12px
- Keywords: QTextEdit, 5 rows, comma-separated, 11px, line-height 1.5
- Edits auto-save to in-memory dict on focus-out

**Other States:**
- Processing → show "Processing..." text (amber)
- Error → show error message in red box: `⚠️ [ERROR_TYPE] message`
- Pending → show "Pending" text (dim)

**Export CSV Button:**
- Ghost style with **blue tint** (background `#00B4D812`, color `#00B4D8`, border `#00B4D833`)
- **Themed hover effect** same as other ghost buttons
- On click → opens **ExportCsvDialog** (NOT direct export)

**IMPORTANT: NO warning banner in Inspector. Warning lives ONLY in ExportCsvDialog.**

---

## 6. Dialogs

### 6.1 Confirm Processing Dialog — `ui/components/confirm_dialog.py`

```
┌────────────────────────────────────┐
│ Confirm Processing                 │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ Files     12 (9 photos, 3 vid)│ │
│ │ Model     gemini-2.5-pro      │ │
│ │ Platform  iStock              │ │
│ └────────────────────────────────┘ │
│ ┌────────────────────────────────┐ │
│ │ Cost          36 credits      │ │  ← gold
│ │ After deduction  1,164 credits│ │
│ └────────────────────────────────┘ │
│                                    │
│ [   Start   ]  [   Cancel   ]     │
└────────────────────────────────────┘
```
- Width: 400px
- Start → calls `POST /job/reserve` then begins processing
- Cancel → closes dialog

### 6.2 Insufficient Credit Dialog — `ui/components/insufficient_dialog.py`

```
┌──────────────────────────────────────┐
│ ⚠️ Insufficient Credits              │
│                                      │
│ Required:   300 credits              │
│ Available:  200 credits              │
│ Shortfall:  100 credits              │
│                                      │
│ [   Top Up   ]                       │  ← opens TopUpDialog
│ [   Process 66 files (partial)   ]   │  ← max affordable
│ [   Cancel   ]                       │
└──────────────────────────────────────┘
```

### 6.3 Export CSV Dialog — `ui/components/export_csv_dialog.py`

**This is the ONLY place where the review warning appears.**

```
┌──────────────────────────────────────────┐
│ 💾 Export CSV                             │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ ⚠️ Please Review Before Uploading    │ │
│ │                                      │ │
│ │ AI-generated metadata may contain    │ │
│ │ errors or inaccuracies. We strongly  │ │
│ │ recommend reviewing all titles,      │ │
│ │ descriptions, and keywords before    │ │
│ │ submitting to stock platforms to     │ │
│ │ ensure the best acceptance rates     │ │
│ │ and avoid potential rejections.      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ QUICK CHECKLIST                      │ │
│ │                                      │ │
│ │ □ Titles accurately describe the     │ │
│ │   content                            │ │
│ │ □ Descriptions are relevant and      │ │
│ │   detailed                           │ │
│ │ □ Keywords don't contain             │ │
│ │   trademarked terms                  │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ [  Export CSV  ]     [  Cancel  ]        │
└──────────────────────────────────────────┘
```

**Specs:**
- Width: 440px
- Warning box: amber gradient background (`#FEB01912` → `#FEB01906`), border `#FEB01933`, border-radius 12px
- Warning icon: ⚠️ large (28px)
- Warning title: "Please Review Before Uploading" — 13px bold, amber color
- Warning body: 12px, secondary text, line-height 1.6
- Checklist: 3 items (NO video timecode item), checkbox style with border
- Export button: gradient pill
- Cancel button: ghost
- On export: show file save dialog → save CSV → show success toast

**Checklist items (exactly 3):**
1. Titles accurately describe the content
2. Descriptions are relevant and detailed
3. Keywords don't contain trademarked terms

### 6.4 Job Summary Dialog — `ui/components/summary_dialog.py`

```
┌──────────────────────────────────────────┐
│ ✅ Processing Complete                    │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ RESULTS                              │ │
│ │ Successful     9 files (green)       │ │
│ │ Failed         1 file (red)          │ │
│ │ Breakdown      📸 8 photos · 🎬 2 vid│ │
│ └──────────────────────────────────────┘ │
│ ┌──────────────────────────────────────┐ │
│ │ CREDITS                              │ │
│ │ Charged        30 cr                 │ │
│ │ Refunded       +3 cr (green)         │ │
│ │ Net cost       27 cr                 │ │
│ │ ─────────────────────                │ │
│ │ Balance        1,173 credits (gold)  │ │
│ └──────────────────────────────────────┘ │
│ ┌──────────────────────────────────────┐ │
│ │ CSV FILES                            │ │
│ │ ✅ iStock_Photos_gemini-2.5_...csv   │ │
│ │ ✅ iStock_Videos_gemini-2.5_...csv   │ │
│ └──────────────────────────────────────┘ │
│ ┌──────────────────────────────────────┐ │
│ │ 💡 Remember to review all metadata   │ │
│ │ before uploading. AI results may need│ │
│ │ manual adjustments for best rates.   │ │
│ └──────────────────────────────────────┘ │
│                                          │
│            [  Close  ]                   │
└──────────────────────────────────────────┘
```

- Small reminder at bottom (not the full warning, just a brief 💡 note)
- Info cards with dark surface background

### 6.5 Credit History Dialog — `ui/components/history_dialog.py`

```
┌────────────────────────────────────────────────┐
│ 📜 Credit History                               │
│                                                │
│ Date         Transaction          Amount       │
│ ───────────────────────────────────────────── │
│ 07/02 14:42  Refund 5 failed      +15 (green) │
│ 07/02 14:35  iStock 50 files      -150 (red)  │
│ 07/02 14:30  Top-up 100 THB       +400 (green)│
│ ...                                            │
│                                                │
│ Balance: 1,200 credits                         │
│                                                │
│               [  Close  ]                      │
└────────────────────────────────────────────────┘
```

- Width: 520px
- Scrollable QTableWidget
- Color: positive = green, negative = red
- Balance bar: gradient subtle background

### 6.6 Top-Up Dialog — `ui/components/topup_dialog.py`

```
┌────────────────────────────────────────┐
│ 🪙 Top Up Credits                      │
│                                        │
│ ┌────────────────────────────────────┐ │
│ │ TRANSFER TO                        │ │
│ │ 🏦 Kasikornbank xxx-x-xxxxx-x     │ │
│ │ Account: XXXXX XXXXX              │ │
│ │ Rate: 1 THB = 4 Credits (gold)    │ │
│ └────────────────────────────────────┘ │
│                                        │
│ ┌────────────────────────────────────┐ │
│ │  📎 Drop payment slip here         │ │  ← dashed border drop zone
│ │     or click to browse             │ │
│ └────────────────────────────────────┘ │
│                                        │
│ Amount: [_____] THB                    │
│                                        │
│ [        Submit Slip        ]          │
│                                        │
│ Status:                                │
│ ⏳ Verifying...                        │
│ ✅ 400 credits added!                  │
│ ❌ Invalid slip                        │
│                                        │
│              [  Close  ]               │
└────────────────────────────────────────┘
```

- Width: 460px
- Drag-drop area: dashed border `#264773`, rounded 12px

### 6.7 Update Dialog — `ui/components/update_dialog.py`

**OPTIONAL (dismissible):**
```
┌──────────────────────────────┐
│ 🆕 Update Available          │
│ Version: 2.0.1               │
│ "Bug fixes..."               │
│ [Update Now]  [Skip]         │
└──────────────────────────────┘
```

**FORCE (modal, no close):**
```
┌──────────────────────────────┐
│ ⚠️ Update Required           │
│ Current: 1.0.0 → New: 2.0.0 │
│ [Download Update]            │
└──────────────────────────────┘
```

### 6.8 Recovery Dialog — `ui/components/recovery_dialog.py`

```
┌─────────────────────────────────────┐
│ ⚠️ Unfinished Job Found             │
│                                     │
│ Job: iStock, 100 files              │
│ Completed: 50 (48 ok, 2 failed)    │
│ Credits reserved: 300               │
│                                     │
│ Refunding unused credits: 156       │
│                                     │
│           [  OK  ]                  │
└─────────────────────────────────────┘
```

### 6.9 Maintenance Dialog

```
┌────────────────────────────────────┐
│ 🔧 Server Maintenance              │
│                                    │
│ The server is temporarily          │
│ unavailable for maintenance.       │
│ Please try again later.            │
│                                    │
│          [  OK  ]                  │
└────────────────────────────────────┘
```

---

## 7. State & Lock Rules

### 7.1 UI States

| State | Sidebar | Gallery | Inspector | Top Bar |
|:--|:--|:--|:--|:--|
| **IDLE** | All enabled | Open folder + browse | Browse + edit | Active |
| **PROCESSING** | All LOCKED | No open folder, view only | View only | Refresh disabled |
| **COMPLETED** | All enabled | Browse | Edit + Export | Active |

### 7.2 Lock During Processing

DISABLE:
- All dropdowns (Model, Platform, Keyword Style)
- All sliders
- API Key Save/Clear
- Open Folder button
- START (becomes STOP)
- Logout button

KEEP ENABLED:
- STOP button
- Gallery click (view results so far)
- Inspector viewing (read-only)

### 7.3 In-Memory Results

```python
self.results: Dict[str, dict] = {
    "IMG_001.jpg": {
        "title": "...", "description": "...", "keywords": [...],
        "category": "...", "token_input": 1234, "token_output": 567,
        "processing_time": 3.2, "status": "success"
    },
    "IMG_002.jpg": {
        "error": "[RATE_LIMIT] Too many requests",
        "error_type": "RATE_LIMIT", "status": "error"
    }
}
```

NO JSON sidecar files. Results stored in memory only until CSV export.

---

## 8. Functional Logic (Summary)

### 8.1 Job Flow
Reserve credits → Decrypt config → Download dictionary → Init blacklist → Create cache → Process files → Post-process keywords → Finalize → Generate CSV → Cleanup

### 8.2 Video Processing
FFmpeg proxy 480p (NOT contact sheet). Upload entire proxy clip to Gemini.

### 8.3 Keyword Pipeline
iStock: clean → dedup → blacklist → trim
Hybrid: phrases first → explode → stem dedup → blacklist → trim
Single: stem dedup (shortest) → blacklist → trim

### 8.4 CSV Export
iStock → 2 CSVs (photos + videos auto-split)
Adobe & Shutterstock → 2 CSVs (one each format)
Filename: `{Platform}_{Type}_{model}_{timestamp}.csv`

### 8.5 Crash Recovery
`~/.bigeye/recovery.json` → on startup → finalize → refund → delete

---

## 9. File Structure

```
client/
├── main.py
├── requirements.txt
├── assets/
│   ├── icons/app_icon.png, app_icon.ico, spinner.gif
│   ├── sounds/complete.wav
│   ├── nltk_data/stemmers/snowball_data/
│   └── styles/dark_theme.qss
├── ui/
│   ├── auth_window.py
│   ├── main_window.py
│   └── components/
│       ├── sidebar.py
│       ├── gallery.py
│       ├── inspector.py
│       ├── credit_bar.py          (Top Bar)
│       ├── topup_dialog.py
│       ├── update_dialog.py
│       ├── recovery_dialog.py
│       ├── summary_dialog.py
│       ├── confirm_dialog.py
│       ├── insufficient_dialog.py
│       ├── history_dialog.py
│       ├── maintenance_dialog.py
│       └── export_csv_dialog.py   (with warning + checklist)
├── core/
│   ├── api_client.py
│   ├── auth_manager.py
│   ├── job_manager.py
│   ├── config.py
│   ├── engines/gemini_engine.py, transcoder.py
│   ├── logic/keyword_processor.py, copyright_guard.py
│   ├── managers/queue_manager.py, journal_manager.py
│   └── data/csv_exporter.py
├── utils/security.py, helpers.py, logger.py
└── build/build_nuitka.py
```

---

## 10. QSS Theme (dark_theme.qss)

```css
/* Main */
QMainWindow, QWidget {
  background: #1A1A2E;
  color: #E8E8E8;
  font: 13px "Segoe UI";
}

/* Inputs */
QLineEdit, QTextEdit, QComboBox, QSpinBox {
  background: #16213E;
  border: 1px solid #1A3A6B;
  border-radius: 8px;
  padding: 10px 12px;
  color: #E8E8E8;
}
QLineEdit:focus, QTextEdit:focus {
  border-color: #FF00CC;
}

/* Ghost Buttons */
QPushButton {
  background: transparent;
  border: 1px solid #1A3A6B;
  border-radius: 8px;
  padding: 7px 14px;
  color: #8892A8;
  font-weight: 500;
}
QPushButton:hover {
  background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #FF00CC18, stop:1 #7B2FFF18);
  border-color: #FF00CC66;
  color: #FF00CC;
}
QPushButton:disabled {
  color: #4A5568;
  border-color: #1A3A6B44;
}

/* Gradient Pill Buttons */
QPushButton#startButton, QPushButton#confirmButton {
  background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #FF00CC, stop:1 #7B2FFF);
  border: none;
  border-radius: 22px;
  padding: 12px 30px;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 700;
}
QPushButton#stopButton {
  background: #FF4560;
  border: none;
  border-radius: 22px;
  padding: 12px 30px;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 700;
}

/* Export CSV */
QPushButton#exportButton {
  background: #00B4D812;
  border: 1px solid #00B4D833;
  color: #00B4D8;
}
QPushButton#exportButton:hover {
  background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #FF00CC18, stop:1 #7B2FFF18);
  border-color: #FF00CC66;
  color: #FF00CC;
}

/* Progress Bar */
QProgressBar {
  border: none;
  border-radius: 3px;
  background: #16213E;
  height: 6px;
}
QProgressBar::chunk {
  background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #FF00CC, stop:1 #7B2FFF);
  border-radius: 3px;
}

/* Slider */
QSlider::groove:horizontal {
  height: 4px;
  background: #1A3A6B;
  border-radius: 2px;
}
QSlider::handle:horizontal {
  background: #FF00CC;
  width: 14px;
  height: 14px;
  margin: -5px 0;
  border-radius: 7px;
}

/* Scrollbar */
QScrollBar:vertical {
  background: transparent;
  width: 6px;
}
QScrollBar::handle:vertical {
  background: #1A3A6B;
  border-radius: 3px;
  min-height: 30px;
}

/* Credit Label */
QLabel#creditLabel {
  font-size: 14px;
  font-weight: 700;
  color: #FFD700;
}
```

---

## 11. Nuitka Build

```python
nuitka_args = [
    "--standalone", "--onefile",
    "--enable-plugin=pyside6",
    "--include-data-dir=assets=assets",
    "--include-package=nltk",
    "--include-data-dir=assets/nltk_data=nltk_data",
    "--windows-icon-from-ico=assets/icons/app_icon.ico",
    "--windows-product-name=BigEye Pro",
    "--windows-file-version=2.0.0",
    "--output-dir=dist",
    "--output-filename=BigEyePro"
]
```

Assets loaded via `get_asset_path()` checking `sys._MEIPASS` → `sys.executable` dir → `__file__` dir.

---

## 12. Interactive Prototype Reference

An interactive React prototype (BigEye_Pro_v4.jsx) is available showing the exact layout, colors, hover effects, and dialog flows. Use it as visual reference when implementing the PySide6 version.

---

*Frontend Design Specification v3.0 FINAL — Ready for AI IDE implementation*
*All changes from prototype review sessions incorporated*
