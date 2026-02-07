# BigEye Pro — Admin Dashboard Design
### Lightweight Web Dashboard for Solo Admin
### Date: February 2026

---

## 1. Overview

Simple web dashboard for the admin (single person) to manage users, credits, slips, and monitor system health. Built as a separate lightweight app — NOT part of the main desktop client.

**Tech:** Streamlit (fastest to build, sufficient for 1 admin)
**Alternative:** Flask + Jinja2 (if Streamlit is too limited later)
**Auth:** Simple password login (environment variable) — single admin only
**Data:** Reads/writes directly to Firestore via firebase-admin SDK

---

## 2. Pages

### 2.1 Dashboard (Home)

```
┌─────────────────────────────────────────────────────────┐
│  BIGEYE PRO — Admin Dashboard                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  TODAY'S STATS                                          │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│  │  12  │ │  5   │ │ ฿800 │ │ 124  │ │  2   │        │
│  │Active│ │ New  │ │Revenue│ │ Jobs │ │Errors│        │
│  │Users │ │Users │ │      │ │      │ │      │        │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘        │
│                                                         │
│  REVENUE (Last 30 Days)                                │
│  [Line chart: daily revenue in THB]                    │
│                                                         │
│  USER GROWTH (Last 30 Days)                            │
│  [Bar chart: new registrations per day]                │
│                                                         │
│  PENDING ACTIONS                                        │
│  ⚠️ 3 slips awaiting manual review                     │
│  ⚠️ 1 job expired (auto-refunded)                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Data source: `daily_reports` collection + real-time queries

### 2.2 Users

```
┌─────────────────────────────────────────────────────────┐
│  USERS                                    [Search: ___] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Email          Name       Credits  Status  Last Active │
│  ─────────────────────────────────────────────────────  │
│  john@...       John D.    1,200   active   2h ago     │
│  jane@...       Jane S.      45   active   1d ago     │
│  test@...       Test U.       0   suspended 30d ago    │
│                                                         │
│  [Click row → User Detail Panel]                       │
│                                                         │
│  USER DETAIL:                                           │
│  ┌───────────────────────────────────────────────────┐ │
│  │ john@example.com                                   │ │
│  │ Name: John Doe   Phone: 0812345678                │ │
│  │ Hardware ID: A1B2C3D4E5F6G7H8                     │ │
│  │ Credits: 1,200   Total Top-up: ฿3,000             │ │
│  │ Status: active   Tier: standard                    │ │
│  │ Registered: 2026-01-15  Last Login: 2h ago        │ │
│  │ App Version: 2.0.0  OS: Windows                    │ │
│  │                                                     │ │
│  │ ACTIONS:                                            │ │
│  │ [Adjust Credits: +/-___] [Apply]                   │ │
│  │ [Suspend] [Reset Hardware ID] [View Jobs]          │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

Functions:
- Search by email/name
- View user details
- **Adjust credits** (+ or −) with reason → creates ADJUSTMENT transaction
- **Suspend/Unsuspend** user
- **Reset hardware ID** (for device change requests)
- View user's job history

### 2.3 Slips (Top-Up Management)

```
┌─────────────────────────────────────────────────────────┐
│  SLIPS                          Filter: [PENDING ▼]     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Date        User         Amount   Status   Action      │
│  ─────────────────────────────────────────────────────  │
│  07/02 14:30 john@...     100 THB  PENDING  [Review]   │
│  07/02 09:15 jane@...     300 THB  VERIFIED  —         │
│  06/02 16:00 test@...     50 THB   REJECTED  —         │
│                                                         │
│  SLIP REVIEW:                                           │
│  ┌───────────────────────────────────────────────────┐ │
│  │ [Slip Image Preview]                               │ │
│  │                                                     │ │
│  │ User: john@example.com                             │ │
│  │ Amount detected: 100 THB (auto)                    │ │
│  │ Bank ref: 20260207143012345                        │ │
│  │ Submitted: 07/02/2026 14:30                        │ │
│  │                                                     │ │
│  │ Credit amount: [400] (auto-calculated)             │ │
│  │ [✅ Approve]  [❌ Reject: ___reason___]             │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

Functions:
- Filter by status (PENDING / VERIFIED / REJECTED / ALL)
- View slip image
- **Approve** → add credits to user, update slip status, create transaction
- **Reject** with reason
- Flag duplicate slips

### 2.4 Jobs Monitor

```
┌─────────────────────────────────────────────────────────┐
│  JOBS                            Filter: [RESERVED ▼]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Token     User      Mode    Files  Status   Created    │
│  ─────────────────────────────────────────────────────  │
│  a1b2...   john@...  iStock   50   COMPLETED  2h ago   │
│  c3d4...   jane@...  Adobe    20   RESERVED   30m ago  │
│  e5f6...   john@...  iStock  100   EXPIRED    2d ago   │
│                                                         │
│  JOB DETAIL:                                            │
│  Reserved: 150 cr | Used: 135 cr | Refunded: 15 cr     │
│  Success: 45 | Failed: 5                                │
│  Model: gemini-2.5-pro | Version: 2.0.0                │
│                                                         │
│  [Force Refund] (for stuck RESERVED jobs)               │
└─────────────────────────────────────────────────────────┘
```

Functions:
- Filter by status
- View job details
- **Force refund** stuck RESERVED jobs manually

### 2.5 System Config

```
┌─────────────────────────────────────────────────────────┐
│  SYSTEM CONFIGURATION                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  APP VERSION                                            │
│  Latest version: [2.0.1___]                            │
│  Force update below: [1.9.0___]                        │
│  Download URL: [https://...___]                        │
│  Release notes: [_______________]                      │
│  [Save]                                                 │
│                                                         │
│  CREDIT RATES                                           │
│  iStock: [3] cr/file                                   │
│  Adobe:  [2] cr/file                                   │
│  Shutterstock: [2] cr/file                             │
│  Exchange rate: 1 THB = [4] credits                    │
│  [Save]                                                 │
│                                                         │
│  PROCESSING                                             │
│  Cache threshold: [20] files                           │
│  Max concurrent images: [5]                            │
│  Max concurrent videos: [2]                            │
│  [Save]                                                 │
│                                                         │
│  MAINTENANCE                                            │
│  [🔴 Enable Maintenance Mode]                          │
│  Message: [_______________]                            │
│                                                         │
│  PROMPTS (Encrypted — view only first 100 chars)       │
│  iStock: "You are a professional stock..."             │
│  Hybrid: "You are a professional stock..."             │
│  Single: "You are a professional stock..."             │
│  [Update Prompts] → upload new prompt text             │
│                                                         │
│  BLACKLIST                                              │
│  Current: 45 terms                                     │
│  [View All] [Add Term: ___] [Remove Term: ___]         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.6 Audit Logs

```
┌─────────────────────────────────────────────────────────┐
│  AUDIT LOGS                     Filter: [WARNING+ ▼]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Time         Event                  User     Severity  │
│  ─────────────────────────────────────────────────────  │
│  14:42:03     JOB_COMPLETED          john@..  INFO     │
│  14:35:12     DEVICE_MISMATCH        test@..  WARNING  │
│  14:30:00     TOPUP_SUCCESS          john@..  INFO     │
│  09:00:00     SYSTEM_ERROR           —        ERROR    │
│                                                         │
│  [Expand row for full details JSON]                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. File Structure

```
admin/
├── app.py                    # Streamlit main app
├── requirements.txt          # streamlit, firebase-admin, plotly
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Users.py
│   ├── 3_Slips.py
│   ├── 4_Jobs.py
│   ├── 5_System_Config.py
│   └── 6_Audit_Logs.py
├── utils/
│   ├── firestore_client.py   # Firebase admin SDK wrapper
│   ├── auth.py               # Simple password check
│   └── charts.py             # Plotly chart helpers
├── .env                      # ADMIN_PASSWORD, FIREBASE_CREDENTIALS_PATH
└── Dockerfile                # For Cloud Run deployment
```

---

## 4. Deployment

Option A: **Cloud Run** (same project as backend API)
- Dockerfile with Streamlit
- Separate service: `admin-dashboard`
- Restrict access via Cloud IAP or simple password

Option B: **Local only**
- Run `streamlit run app.py` on admin's machine
- Connect to Firestore via service account key

Recommended: Start with **Option B** (local), migrate to Cloud Run when needed.

---

## 5. Notifications (LINE Notify)

Since admin is solo, add LINE Notify for real-time alerts:

```python
# utils/notifications.py
def notify_line(message: str):
    """Send LINE Notify to admin's phone"""
    requests.post("https://notify-api.line.me/api/notify",
        headers={"Authorization": f"Bearer {LINE_TOKEN}"},
        data={"message": message})
```

**Trigger events:**
| Event | Message |
|:--|:--|
| New top-up | "🟢 User john@... topped up 300 THB (+1,200 cr)" |
| Slip pending | "🟡 Slip pending manual review from jane@..." |
| Device mismatch | "🔴 Device mismatch: test@... (possible sharing)" |
| High error rate | "🔴 Error rate >10% in last hour" |
| Daily summary | "🔵 Daily: 15 active, ฿1,500 revenue, 450 jobs" |

---

*Admin Dashboard Design — Ready for implementation after main app is complete*
