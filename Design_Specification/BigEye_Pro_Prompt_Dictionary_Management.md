# BigEye Pro — Prompt & Dictionary Management Specification
### Version Control, Upload, and Delivery System
### Date: February 2026

---

## 1. Overview

Prompts (3 files) and Dictionary (1 file) are the core IP of BigEye Pro. This spec defines how they are stored, versioned, updated, and delivered to the desktop client — with rollback capability.

**Key Decisions:**
- **Storage:** Firestore (all files fit within 1MB document limit)
- **Update method:** Admin uploads .md/.txt files via Admin Dashboard
- **Version control:** Every update creates a new version, old versions kept for rollback
- **Delivery:** Encrypted via `/job/reserve` API response (existing flow)

---

## 2. File Inventory

| File | Type | Size | Format | Used By |
|:--|:--|:--|:--|:--|
| `prompt_iStock.md` | Prompt | ~6 KB | Markdown with `{placeholders}` | iStock mode |
| `PROMPT_HYBRID_MODE.md` | Prompt | ~5 KB | Markdown with `{placeholders}` | Adobe Hybrid mode |
| `prompt_Single_words.md` | Prompt | ~3 KB | Markdown with `{placeholders}` | Shutterstock Single mode |
| `Dictionary.txt` | Dictionary | ~106 KB | One keyword per line, 9,194 entries | iStock mode only |

**Total:** ~120 KB — well within Firestore 1MB document limit.

**Placeholders in prompts** (replaced at runtime by client):
```
{media_type_str}      → "image" or "video"
{keyword_count}       → e.g., 55 (target + overfetch)
{title_min}           → e.g., 53 (75% of title_limit)
{title_limit}         → e.g., 70
{desc_min}            → e.g., 150 (75% of desc_limit)
{desc_limit}          → e.g., 200
{keyword_data}        → Dictionary content (iStock only)
{video_instruction}   → Video-specific instructions (or empty)
```

---

## 3. Firestore Schema

### 3.1 Active Config (existing — minor update)

```
system_config/app_settings
├── prompts: map
│   ├── istock: string (encrypted, AES-256-CBC)
│   ├── hybrid: string (encrypted)
│   └── single: string (encrypted)
├── prompts_version: string (e.g., "v3")        ← NEW
├── prompts_updated_at: timestamp                ← NEW
├── dictionary: string (full text, one word per line)  ← CHANGED: stored directly
├── dictionary_version: string (e.g., "v2")      ← NEW
├── dictionary_updated_at: timestamp             ← NEW
├── dictionary_word_count: number (e.g., 9194)   ← NEW
├── blacklist: array<string>
├── credit_rates: map
│   └── ...
└── ...existing fields...
```

### 3.2 Version History (NEW collection)

```
prompt_versions/{version_id}
├── version: string (e.g., "v3")
├── type: string ("prompt" | "dictionary")
├── name: string ("istock" | "hybrid" | "single" | "dictionary")
├── content: string (raw text, NOT encrypted — admin-only access)
├── content_encrypted: string (AES encrypted — for quick restore)
├── word_count: number | null (dictionary only)
├── uploaded_by: string (admin identifier)
├── upload_note: string (e.g., "Added better SEO instructions for hybrid mode")
├── is_active: boolean (true = currently deployed)
├── created_at: timestamp
└── metadata: map
    ├── file_size_bytes: number
    ├── line_count: number
    └── placeholder_count: number (prompt only — count of {xxx} patterns)
```

**Example documents:**
```
prompt_versions/prompt_istock_v1    → { version: "v1", type: "prompt", name: "istock", is_active: false, ... }
prompt_versions/prompt_istock_v2    → { version: "v2", type: "prompt", name: "istock", is_active: false, ... }
prompt_versions/prompt_istock_v3    → { version: "v3", type: "prompt", name: "istock", is_active: true, ... }
prompt_versions/prompt_hybrid_v1    → { version: "v1", type: "prompt", name: "hybrid", is_active: true, ... }
prompt_versions/prompt_single_v1    → { version: "v1", type: "prompt", name: "single", is_active: true, ... }
prompt_versions/dictionary_v1       → { version: "v1", type: "dictionary", name: "dictionary", is_active: false, ... }
prompt_versions/dictionary_v2       → { version: "v2", type: "dictionary", name: "dictionary", is_active: true, ... }
```

**Indexes:**
- `name` + `created_at` DESC → version history per prompt
- `is_active` + `name` → find current active version

### 3.3 Security Rules (add to existing)

```javascript
match /prompt_versions/{versionId} {
  // Admin read-only via Admin Dashboard (using Admin SDK, bypasses rules)
  // No client access at all
  allow read, write: if false;
}
```

---

## 4. Upload Flow (Admin Dashboard)

### 4.1 Admin Dashboard UI — Prompts Page

```
┌──────────────────────────────────────────────────────────────┐
│  PROMPTS & DICTIONARY MANAGEMENT                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─ iStock Prompt ──────────────────────────────────────────┐│
│  │ Active: v3 (uploaded 2026-02-07 14:30)                   ││
│  │ Size: 6,362 bytes | Placeholders: 8 found ✅              ││
│  │                                                           ││
│  │ [📤 Upload New Version]  [👁 Preview Current]  [History ▼]││
│  │                                                           ││
│  │ Version History:                                          ││
│  │   v3 ● ACTIVE  2026-02-07  "Better niche analysis"       ││
│  │   v2           2026-01-20  "Added hierarchy rule"         ││
│  │   v1           2026-01-01  "Initial version"              ││
│  │                           [🔄 Rollback to v2]            ││
│  └───────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─ Hybrid Prompt ──────────────────────────────────────────┐│
│  │ Active: v1 (uploaded 2026-01-01)                         ││
│  │ [📤 Upload New Version]  [👁 Preview Current]  [History ▼]││
│  └───────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─ Single Words Prompt ────────────────────────────────────┐│
│  │ Active: v1 (uploaded 2026-01-01)                         ││
│  │ [📤 Upload New Version]  [👁 Preview Current]  [History ▼]││
│  └───────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─ Dictionary ─────────────────────────────────────────────┐│
│  │ Active: v2 (uploaded 2026-02-05)                         ││
│  │ Words: 9,194 | Size: 105 KB                              ││
│  │                                                           ││
│  │ [📤 Upload New Version]  [🔍 Search Words]  [History ▼]  ││
│  │                                                           ││
│  │ Quick Actions:                                            ││
│  │ [+ Add Word: ________]  [- Remove Word: ________]        ││
│  └───────────────────────────────────────────────────────────┘│
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Upload New Version Flow

```
Admin clicks [📤 Upload New Version] for iStock prompt:

Step 1: File Upload
┌──────────────────────────────────┐
│ Upload New iStock Prompt          │
│                                   │
│ [Drop .md file here]             │
│  or click to browse               │
│                                   │
│ Note: [_________________________] │
│ (e.g., "Improved keyword rules") │
│                                   │
│ [Upload & Validate]              │
└──────────────────────────────────┘

Step 2: Validation (automatic)
┌──────────────────────────────────┐
│ ✅ Validation Results             │
│                                   │
│ File: prompt_iStock_v4.md         │
│ Size: 6,580 bytes                 │
│ Lines: 95                         │
│                                   │
│ Placeholders found:               │
│   ✅ {media_type_str}             │
│   ✅ {keyword_count}              │
│   ✅ {title_min}                  │
│   ✅ {title_limit}                │
│   ✅ {desc_min} (if applicable)   │
│   ✅ {desc_limit}                 │
│   ✅ {keyword_data}               │
│   ✅ {video_instruction}          │
│                                   │
│ ⚠️ New placeholder found:         │
│   {new_thing} — is this intended? │
│                                   │
│ [Deploy as v4]  [Cancel]          │
└──────────────────────────────────┘

Step 3: Deployment
  1. Read file content
  2. Validate placeholders
  3. Encrypt content with AES-256-CBC
  4. Save to prompt_versions/{prompt_istock_v4}
     - is_active: true
  5. Update previous active version: is_active → false
  6. Update system_config/app_settings:
     - prompts.istock = encrypted content
     - prompts_version = "v4"
     - prompts_updated_at = now
  7. Log to audit_logs: PROMPT_UPDATED
  8. LINE Notify: "📝 iStock prompt updated to v4 by admin"
```

### 4.3 Rollback Flow

```
Admin clicks [🔄 Rollback to v2]:

┌──────────────────────────────────┐
│ ⚠️ Confirm Rollback               │
│                                   │
│ Rolling back iStock prompt:       │
│   Current: v3 → Restore: v2      │
│                                   │
│ v2 note: "Added hierarchy rule"  │
│ v2 date: 2026-01-20              │
│                                   │
│ [Confirm Rollback]  [Cancel]      │
└──────────────────────────────────┘

Steps:
  1. Load prompt_versions/prompt_istock_v2
  2. Set v2: is_active → true
  3. Set v3: is_active → false
  4. Update system_config/app_settings:
     - prompts.istock = v2's encrypted content
     - prompts_version = "v2 (rollback from v3)"
     - prompts_updated_at = now
  5. Log: PROMPT_ROLLBACK
  6. LINE Notify: "🔄 iStock prompt rolled back v3→v2"
```

### 4.4 Dictionary Upload Flow

```
Upload New Dictionary:

Step 1: Upload .txt file (one word per line)

Step 2: Validation
┌──────────────────────────────────┐
│ ✅ Dictionary Validation          │
│                                   │
│ File: Dictionary_v3.txt           │
│ Total words: 9,250                │
│ Size: 108 KB (< 1MB limit ✅)    │
│                                   │
│ Changes from current (v2):        │
│   + 62 new words added            │
│   - 6 words removed               │
│   = 9,194 → 9,250 (+56)          │
│                                   │
│ New words preview:                │
│   "Cryptocurrency", "Blockchain", │
│   "Electric Vehicle", ...          │
│                                   │
│ Removed words:                    │
│   "Floppy Disk", "Pager", ...     │
│                                   │
│ [Deploy as v3]  [Cancel]          │
└──────────────────────────────────┘

Step 3: Deploy
  1. Store full text in system_config/app_settings.dictionary
  2. Update dictionary_version, dictionary_updated_at, dictionary_word_count
  3. Save to prompt_versions/dictionary_v3
  4. Mark previous: is_active → false
  5. Log + Notify
```

### 4.5 Dictionary Quick Edit

```
[+ Add Word]: Admin types "Cryptocurrency" → append to dictionary, bump version
[- Remove Word]: Admin types "Floppy Disk" → remove from dictionary, bump version
[🔍 Search]: Search for a word in the dictionary
```

These create **micro-versions** (e.g., v2.1, v2.2) to avoid cluttering major versions.

---

## 5. Delivery to Client (Existing Flow — No Change)

The existing `/job/reserve` flow already handles this:

```
Client                              Server
  │                                   │
  │  POST /job/reserve                │
  │  {file_count, mode, ...}          │
  │──────────────────────────────────►│
  │                                   │  1. Deduct credits
  │                                   │  2. Read system_config/app_settings
  │                                   │  3. Package response:
  │                                   │
  │  Response:                        │
  │  {                                │
  │    job_token: "...",              │
  │    config: {                      │
  │      prompt: "<AES encrypted>",   │  ← Active prompt for selected mode
  │      dictionary: "<raw text>",    │  ← Only for iStock mode
  │      blacklist: [...],            │
  │      cache_threshold: 20,         │
  │      max_concurrent_images: 5,    │
  │      max_concurrent_videos: 2     │
  │    }                              │
  │  }                                │
  │◄──────────────────────────────────│
  │                                   │
  │  Client decrypts prompt           │
  │  Client stores dictionary in RAM  │
  │  Client starts processing         │
```

**No change needed** — the client always gets the latest active prompt/dictionary from `system_config/app_settings` each time it reserves a job.

---

## 6. Backend API Additions

### 6.1 New Endpoints (Admin only)

Add to backend `routers/admin.py`:

```
POST /api/v1/admin/prompt/upload
  Auth: Admin JWT
  Body: { name: "istock"|"hybrid"|"single", content: string, note: string }
  Action: Validate → Encrypt → Save version → Update system_config
  Response: { version: "v4", status: "deployed" }

POST /api/v1/admin/prompt/rollback
  Auth: Admin JWT
  Body: { name: "istock", target_version: "v2" }
  Action: Load target → Update system_config → Swap is_active flags
  Response: { version: "v2", status: "rolled_back" }

GET /api/v1/admin/prompt/history
  Auth: Admin JWT
  Query: ?name=istock
  Response: [{ version, created_at, note, is_active, file_size_bytes }, ...]

POST /api/v1/admin/dictionary/upload
  Auth: Admin JWT
  Body: { content: string, note: string }
  Action: Validate size < 900KB → Save → Update system_config
  Response: { version: "v3", word_count: 9250 }

POST /api/v1/admin/dictionary/rollback
  Auth: Admin JWT
  Body: { target_version: "v1" }

GET /api/v1/admin/dictionary/history
  Auth: Admin JWT

POST /api/v1/admin/dictionary/add-word
  Auth: Admin JWT
  Body: { word: "Cryptocurrency" }

POST /api/v1/admin/dictionary/remove-word
  Auth: Admin JWT
  Body: { word: "Floppy Disk" }
```

### 6.2 Validation Logic

```python
# Prompt validation
REQUIRED_PLACEHOLDERS = {
    "istock": ["{media_type_str}", "{keyword_count}", "{title_min}", 
               "{title_limit}", "{desc_limit}", "{keyword_data}", 
               "{video_instruction}"],
    "hybrid": ["{media_type_str}", "{keyword_count}", "{title_min}", 
               "{title_limit}", "{desc_min}", "{desc_limit}", 
               "{video_instruction}"],
    "single": ["{media_type_str}", "{keyword_count}", "{title_min}", 
               "{title_limit}", "{desc_min}", "{desc_limit}", 
               "{video_instruction}"],
}

def validate_prompt(name: str, content: str) -> dict:
    required = REQUIRED_PLACEHOLDERS[name]
    found = [p for p in required if p in content]
    missing = [p for p in required if p not in content]
    extra = re.findall(r'\{(\w+)\}', content)
    extra = [f"{{{p}}}" for p in extra if f"{{{p}}}" not in required]
    return {
        "valid": len(missing) == 0,
        "found": found,
        "missing": missing,
        "extra_placeholders": extra,
        "size_bytes": len(content.encode('utf-8')),
        "line_count": content.count('\n') + 1,
    }

# Dictionary validation
def validate_dictionary(content: str) -> dict:
    words = [w.strip() for w in content.strip().split('\n') if w.strip()]
    size_bytes = len(content.encode('utf-8'))
    return {
        "valid": size_bytes < 900_000,  # 900KB safety margin
        "word_count": len(words),
        "size_bytes": size_bytes,
        "duplicates": len(words) - len(set(w.lower() for w in words)),
    }
```

---

## 7. Retention Policy

| Item | Keep | Auto-cleanup |
|:--|:--|:--|
| Active version | Forever | — |
| Previous versions | Last 10 per prompt | Cloud Scheduler monthly |
| Dictionary versions | Last 5 | Cloud Scheduler monthly |
| Audit logs (PROMPT_UPDATED) | 1 year | Cloud Scheduler monthly |

---

## 8. Admin Dashboard Integration

Add to `admin/pages/5_System_Config.py` (update existing page):

```python
# Streamlit page structure
st.header("Prompts & Dictionary")

for name in ["istock", "hybrid", "single"]:
    with st.expander(f"{'iStock' if name == 'istock' else name.title()} Prompt"):
        # Show active version info
        active = get_active_version(name)
        st.info(f"Active: {active['version']} | Updated: {active['created_at']}")
        
        # Upload
        uploaded = st.file_uploader(f"Upload new {name} prompt", type=["md", "txt"])
        note = st.text_input(f"Version note for {name}")
        if st.button(f"Deploy {name}") and uploaded:
            content = uploaded.read().decode('utf-8')
            result = validate_prompt(name, content)
            if result['valid']:
                deploy_prompt(name, content, note)
                st.success(f"Deployed as {result['new_version']}")
            else:
                st.error(f"Missing placeholders: {result['missing']}")
        
        # History + Rollback
        history = get_prompt_history(name)
        for v in history:
            col1, col2, col3 = st.columns([2, 4, 2])
            col1.write(v['version'] + (" ● ACTIVE" if v['is_active'] else ""))
            col2.write(v['upload_note'])
            if not v['is_active']:
                if col3.button(f"Rollback to {v['version']}", key=f"rb_{name}_{v['version']}"):
                    rollback_prompt(name, v['version'])
                    st.rerun()

# Dictionary section
with st.expander("Dictionary"):
    active_dict = get_active_dictionary()
    st.info(f"Active: {active_dict['version']} | Words: {active_dict['word_count']}")
    
    # Upload
    uploaded_dict = st.file_uploader("Upload new dictionary", type=["txt"])
    if st.button("Deploy Dictionary") and uploaded_dict:
        content = uploaded_dict.read().decode('utf-8')
        result = validate_dictionary(content)
        if result['valid']:
            deploy_dictionary(content, note)
        else:
            st.error(f"File too large: {result['size_bytes']} bytes")
    
    # Quick add/remove
    col1, col2 = st.columns(2)
    add_word = col1.text_input("Add word")
    if col1.button("+ Add") and add_word:
        add_word_to_dictionary(add_word)
    
    remove_word = col2.text_input("Remove word")
    if col2.button("- Remove") and remove_word:
        remove_word_from_dictionary(remove_word)
    
    # Search
    search = st.text_input("Search dictionary")
    if search:
        matches = search_dictionary(search)
        st.write(f"Found {len(matches)} matches: {', '.join(matches[:20])}")
```

---

## 9. AI IDE Task (NEW)

Add this task to the implementation pipeline:

```
## [Task A-11] Prompt & Dictionary Management API (NEW)

TASK: Add admin endpoints for prompt/dictionary version management.

FILES:
  backend/app/routers/admin.py
  backend/app/models/admin.py

NEW COLLECTION: prompt_versions (see schema in spec)

ENDPOINTS:
  POST /api/v1/admin/prompt/upload — validate + encrypt + deploy
  POST /api/v1/admin/prompt/rollback — restore previous version
  GET  /api/v1/admin/prompt/history — version list per prompt
  POST /api/v1/admin/dictionary/upload — validate size + deploy
  POST /api/v1/admin/dictionary/rollback
  GET  /api/v1/admin/dictionary/history
  POST /api/v1/admin/dictionary/add-word — quick add
  POST /api/v1/admin/dictionary/remove-word — quick remove

All endpoints require admin JWT authentication.
Validation: check required placeholders per prompt type.
Every change: save to prompt_versions + update system_config + audit_log.

ACCEPTANCE CRITERIA:
✅ Upload new iStock prompt → encrypts → deploys → old version kept
✅ Rollback to v1 → system_config updated → next job gets v1
✅ Dictionary upload validates size < 900KB
✅ Add/remove word creates micro-version
✅ History returns all versions sorted by date
```

---

*Prompt & Dictionary Management Specification — Complete*
*Integrates with: Database Design, Admin Dashboard, AI IDE Tasks*
