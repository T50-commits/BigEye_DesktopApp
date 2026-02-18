# BigEye Pro — React Admin Dashboard
### Design Specification for AI IDE Implementation
### Version 1.0 — February 2026

---

## สารบัญ

1. [สรุปโปรเจค](#1-สรุปโปรเจค)
2. [สถาปัตยกรรม](#2-สถาปัตยกรรม)
3. [Admin API Endpoints (ต้องสร้างใหม่)](#3-admin-api-endpoints)
4. [Tech Stack](#4-tech-stack)
5. [Design System](#5-design-system)
6. [หน้าทั้งหมด (10 หน้า)](#6-หน้าทั้งหมด)
7. [โครงสร้างไฟล์](#7-โครงสร้างไฟล์)
8. [Deploy ด้วย Firebase Hosting](#8-deploy)
9. [ลำดับการสั่ง AI IDE](#9-ลำดับการสั่ง-ai-ide)

---

## 1. สรุปโปรเจค

### เป้าหมาย
เปลี่ยน Admin Dashboard จาก Streamlit (Python) เป็น React + Next.js เพื่อ:
- UI สวย professional ปรับแต่งได้ไม่จำกัด
- ใช้งานบนมือถือได้ (Responsive)
- มีระบบบัญชี/การเงินครบ (รายรับ/รายได้รับรู้/ภาษี)
- Deploy ฟรีบน Firebase Hosting

### สิ่งที่เปลี่ยน
```
ก่อน:
  Admin (Streamlit/Python) ──→ Firestore ตรงๆ ด้วย Admin SDK

หลัง:
  Admin (React/Browser) ──→ Backend API (FastAPI) ──→ Firestore
```

### สิ่งที่ต้องสร้างใหม่
1. **Admin API Endpoints** — เพิ่มใน `server/app/routers/admin.py`
2. **React Frontend** — โปรเจค Next.js ใหม่ใน `admin-web/`
3. **Firebase Hosting config** — `firebase.json`

### สิ่งที่ยังใช้เดิม
- Backend FastAPI (เพิ่ม admin router)
- Firestore schema เดิมทุกอย่าง
- Authentication flow (JWT)

---

## 2. สถาปัตยกรรม

```
┌─────────────────────────────────────────────────────────────┐
│                      Firebase Project                        │
│                                                              │
│  ┌──────────────────────┐    ┌───────────────────────────┐  │
│  │  Firebase Hosting     │    │  Cloud Run                │  │
│  │                       │    │                           │  │
│  │  React Admin Dashboard│    │  FastAPI Backend           │  │
│  │  bigeye-admin.web.app │    │  bigeye-api-xxx.run.app   │  │
│  │                       │    │                           │  │
│  │  Static files (HTML,  │    │  /api/v1/auth/*           │  │
│  │  JS, CSS)             │    │  /api/v1/credit/*         │  │
│  │                       │    │  /api/v1/job/*            │  │
│  │  หน้า Login            │    │  /api/v1/system/*         │  │
│  │  หน้า Dashboard        │    │  /api/v1/admin/*    ← ใหม่│  │
│  │  หน้า Users            │    │  /api/v1/admin/promo/*   │  │
│  │  หน้า Slips            │    │                           │  │
│  │  หน้า Jobs             │    │                           │  │
│  │  หน้า Finance ← ใหม่!  │    │                           │  │
│  │  หน้า Config           │    │                           │  │
│  │  หน้า Audit Logs       │    │                           │  │
│  │  หน้า Promotions       │    │                           │  │
│  └──────────┬───────────┘    └─────────────┬─────────────┘  │
│             │                               │                │
│             └───────── API Calls ───────────┘                │
│                                                              │
│                    ┌──────────────────┐                      │
│                    │    Firestore      │                      │
│                    │    (Database)     │                      │
│                    └──────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Authentication Flow สำหรับ Admin

```
1. Admin เข้า bigeye-admin.web.app
   ↓
2. หน้า Login → กรอก email + password
   ↓
3. POST /api/v1/auth/login → ได้ JWT token
   ↓
4. React เก็บ token ใน memory (ไม่ใช่ localStorage)
   ↓
5. ทุก API call → ส่ง Authorization: Bearer <token>
   ↓
6. Backend เช็ค: user_id อยู่ใน ADMIN_UIDS หรือไม่
   ↓
7. ถ้าใช่ → อนุญาต / ถ้าไม่ → 403 Forbidden
```

---

## 3. Admin API Endpoints (ต้องสร้างใหม่)

### ไฟล์: `server/app/routers/admin.py`

ทุก endpoint ใช้ `require_admin` dependency (เหมือน admin_promo.py)

### 3.1 Dashboard Stats

```
GET /api/v1/admin/dashboard/stats
Response:
{
  "active_users": 45,
  "new_users_today": 3,
  "topup_thb_today": 15000,
  "recognized_thb_today": 8750.50,
  "exchange_rate": 4,
  "jobs_today": 28,
  "errors_today": 2,
  "success_rate": 92.9,
  "pending_slips": 5,
  "stuck_jobs": 1
}
```

```
GET /api/v1/admin/dashboard/charts?days=30
Response:
{
  "revenue": [
    {"date": "2026-02-01", "topup_thb": 5000, "recognized_thb": 3200},
    ...
  ],
  "users": [
    {"date": "2026-02-01", "new_users": 3, "active_users": 15},
    ...
  ]
}
```

### 3.2 Users

```
GET    /api/v1/admin/users?search=test@email.com&page=1&limit=50
GET    /api/v1/admin/users/{uid}
GET    /api/v1/admin/users/{uid}/transactions?limit=50
GET    /api/v1/admin/users/{uid}/jobs?limit=50
POST   /api/v1/admin/users/{uid}/adjust-credits
       Body: {"amount": 500, "reason": "ชดเชย error"}
POST   /api/v1/admin/users/{uid}/suspend
POST   /api/v1/admin/users/{uid}/unsuspend
POST   /api/v1/admin/users/{uid}/reset-hardware
POST   /api/v1/admin/users/{uid}/reset-password
       Body: {"new_password": "xxxxxxxx", "reset_hardware": true}
```

### 3.3 Slips

```
GET    /api/v1/admin/slips?status=PENDING&page=1&limit=50
GET    /api/v1/admin/slips/{id}
POST   /api/v1/admin/slips/{id}/approve
       Body: {"credit_amount": 2000}
POST   /api/v1/admin/slips/{id}/reject
       Body: {"reason": "สลิปซ้ำ"}
```

### 3.4 Jobs

```
GET    /api/v1/admin/jobs?status=RESERVED&page=1&limit=50
GET    /api/v1/admin/jobs/{id}
POST   /api/v1/admin/jobs/{id}/force-refund
```

### 3.5 Finance (ใหม่!)

```
GET /api/v1/admin/finance/daily?from=2026-02-01&to=2026-02-28
Response:
{
  "days": [
    {
      "date": "2026-02-01",
      "topup_thb": 5000,           ← เงินจริงที่ลูกค้าเติม
      "topup_count": 8,            ← จำนวนครั้งเติม
      "recognized_thb": 3200.50,   ← เครดิตที่ใช้ ÷ exchange_rate
      "recognized_credits": 12802, ← เครดิตที่ใช้จริง
      "new_users": 3,
      "active_users": 15,
      "jobs_count": 28,
      "files_processed": 450
    },
    ...
  ],
  "summary": {
    "total_topup_thb": 150000,
    "total_recognized_thb": 98500,
    "total_new_users": 45,
    "total_jobs": 580,
    "total_files": 9200
  }
}
```

```
GET /api/v1/admin/finance/monthly?year=2026
Response:
{
  "months": [
    {
      "month": "2026-01",
      "topup_thb": 45000,
      "recognized_thb": 32000,
      "deferred_revenue": 13000,   ← topup - recognized (เงินที่ยังไม่ได้ใช้)
      "new_users": 28,
      "active_users": 45,
      "jobs_count": 280,
      "avg_revenue_per_user": 711
    },
    ...
  ],
  "ytd": {
    "total_topup_thb": 90000,
    "total_recognized_thb": 64000,
    "total_deferred": 26000,
    "tax_base_estimate": 64000    ← รายได้รับรู้ = ฐานภาษี
  }
}
```

```
GET /api/v1/admin/finance/export?from=2026-01-01&to=2026-12-31&format=xlsx
Response: ไฟล์ Excel download

GET /api/v1/admin/finance/export?from=2026-01-01&to=2026-12-31&format=pdf
Response: ไฟล์ PDF download
```

### 3.6 System Config

```
GET    /api/v1/admin/config
PUT    /api/v1/admin/config/version
       Body: {"app_latest_version": "2.0.1", "force_update_below": "1.9.0", ...}
PUT    /api/v1/admin/config/rates
       Body: {"credit_rates": {...}, "exchange_rate": 4}
PUT    /api/v1/admin/config/bank
       Body: {"bank_name": "กสิกร", "account_number": "xxx", "account_name": "xxx"}
PUT    /api/v1/admin/config/processing
       Body: {"context_cache_threshold": 20, "max_concurrent_images": 5, ...}
PUT    /api/v1/admin/config/maintenance
       Body: {"maintenance_mode": true, "maintenance_message": "..."}
PUT    /api/v1/admin/config/prompts/{key}
       Body: {"content": "...prompt text..."}
PUT    /api/v1/admin/config/blacklist
       Body: {"terms": ["nike", "adidas", ...]}
```

### 3.7 Audit Logs

```
GET /api/v1/admin/audit-logs?severity=WARNING&days=7&page=1&limit=100
```

### 3.8 Promotions — มีอยู่แล้ว ✅

ใช้ endpoints จาก `admin_promo.py` ที่มีอยู่ ไม่ต้องเพิ่ม

---

## 4. Tech Stack

```
Framework:    Next.js 14 (App Router)
Language:     TypeScript
Styling:      Tailwind CSS
Components:   shadcn/ui
Charts:       Recharts
Icons:        Lucide React
HTTP Client:  fetch (built-in)
State:        React Context + useState
Auth:         JWT in memory (React Context)
Font:         Geist Sans + Geist Mono (หรือ Satoshi + IBM Plex Sans Thai)
Deploy:       Firebase Hosting (Static Export)
```

### ทำไมเลือก Tech Stack นี้

| เลือก | เหตุผล |
|:--|:--|
| Next.js | SSG export ได้ → deploy บน Firebase Hosting ฟรี |
| TypeScript | ป้องกัน bug, autocomplete ดี |
| Tailwind | เขียน CSS เร็ว, responsive ง่าย |
| shadcn/ui | Component สวย, customize ได้, ไม่มี dependency เพิ่ม |
| Recharts | กราฟ interactive, dark theme ง่าย |
| Lucide | ไอคอน consistent, tree-shakeable |

---

## 5. Design System

### 5.1 Color Palette

```css
/* Background */
--bg-root:      #06080f;       /* พื้นหลังหลัก */
--bg-surface:   #0c1021;       /* Card / Panel */
--bg-elevated:  #131a2e;       /* Elevated card */
--bg-input:     #0a0e1a;       /* Input fields */
--bg-hover:     #1a2240;       /* Hover state */

/* Border */
--border:       #1c2541;
--border-hover: #2d3a5c;

/* Text */
--text-primary:   #eef2ff;
--text-secondary: #8b9cc7;
--text-muted:     #4f5d80;

/* Accent */
--accent-blue:    #4f8cff;
--accent-cyan:    #22d3ee;
--accent-green:   #34d399;
--accent-yellow:  #fbbf24;
--accent-red:     #f87171;
--accent-purple:  #a78bfa;
--accent-pink:    #f472b6;
--accent-orange:  #fb923c;

/* Semantic */
--success: #34d399;
--warning: #fbbf24;
--danger:  #f87171;
--info:    #4f8cff;
```

### 5.2 Typography

```css
/* ใช้ font ที่ดูสวยและ unique ไม่ใช่ Inter/Roboto */
--font-display: 'Satoshi', 'IBM Plex Sans Thai', sans-serif;
--font-body:    'Satoshi', 'IBM Plex Sans Thai', sans-serif;
--font-mono:    'JetBrains Mono', 'Fira Code', monospace;

/* หรือใช้ Geist */
--font-display: 'Geist', 'IBM Plex Sans Thai', sans-serif;
--font-mono:    'Geist Mono', monospace;
```

### 5.3 Spacing & Radius

```
Card padding:    24px
Card radius:     16px
Button radius:   10px
Input radius:    10px
Gap (grid):      20px
Page padding:    32px (desktop), 16px (mobile)
```

### 5.4 Component Patterns

**Metric Card:**
```
┌──────────────────────────┐
│  ○  glow blob (accent)   │
│                          │
│  👥  ACTIVE USERS         │  ← uppercase label, muted
│  45                      │  ← large bold value, accent color
│  ↑ 12% จากเมื่อวาน       │  ← sub text, green/red trend
└──────────────────────────┘
```

**Data Table:**
```
┌──────────────────────────────────────────┐
│  📋 ผู้ใช้งาน              🔍 ค้นหา...   │  ← header + search
├──────────────────────────────────────────┤
│  Email    Name    Credits  Status  ⋯     │  ← sticky header
│  ─────────────────────────────────────── │
│  a@b.c    นาย ก    500     ● active      │  ← row hover highlight
│  c@d.e    นาย ข    1200    ● active      │
│  e@f.g    นาย ค    0       ● suspended   │  ← red badge
├──────────────────────────────────────────┤
│  ← 1 2 3 4 5 →           50/page        │  ← pagination
└──────────────────────────────────────────┘
```

**Finance Card (ใหม่!):**
```
┌──────────────────────────────────────────────────────┐
│  💰 สรุปรายได้เดือน กุมภาพันธ์ 2026                   │
├──────────────────────────────────────────────────────┤
│                                                      │
│   รายรับ (เติมเงิน)     รายได้รับรู้        ส่วนต่าง   │
│   ฿150,000              ฿98,500           ฿51,500   │
│   ████████████████       ███████████       ████████  │
│   green                  cyan              yellow    │
│                                                      │
│   ───────────── กราฟรายวัน ─────────────              │
│   ▁▃▅▇█▅▃▁▃▅▇█▅▃▁▃▅▇█▅▃▁▃▅▇█▅                     │
│                                                      │
│   [📊 Export Excel]  [📄 Export PDF]                  │
└──────────────────────────────────────────────────────┘
```

### 5.5 Responsive Breakpoints

```
Desktop:  > 1024px  → Sidebar + Content
Tablet:   768-1024  → Collapsible sidebar
Mobile:   < 768px   → Bottom nav or hamburger menu

Metric cards:  4 cols → 2 cols → 1 col
Charts:        2 cols → 1 col
Tables:        Horizontal scroll on mobile
```

---

## 6. หน้าทั้งหมด (10 หน้า)

### Page 0: Login

```
Route: /login

Layout:
- Centered card บนพื้นหลัง gradient mesh
- Logo "BigEye Pro Admin"
- Email + Password inputs
- Login button
- Error message

API:
POST /api/v1/auth/login
→ เก็บ token + user_id ใน AuthContext
→ เช็ค user_id ∈ ADMIN_UIDS (backend ทำ)
→ redirect ไป /dashboard
```

### Page 1: Dashboard (หน้าหลัก)

```
Route: /dashboard

Sections:
1. Header: "แดชบอร์ด" + เวลาไทย + ปุ่มรีเฟรช
2. Metric Cards (4 ช่อง):
   - ผู้ใช้งาน (active_users) — สีน้ำเงิน
   - สมัครใหม่วันนี้ (new_users_today) — สีม่วง
   - รายรับเติมเงิน (topup_thb_today) — สีเขียว
   - รายได้รับรู้ (recognized_thb_today) — สี cyan
3. Job Stats (3 ช่อง):
   - งานทั้งหมด — สีเหลือง
   - งานผิดพลาด — สีแดง
   - อัตราสำเร็จ — สีเขียว/เหลือง/แดง ตาม %
4. Alert Cards:
   - สลิปรอตรวจ (pending_slips) — สีส้ม + ลิงก์ไปหน้า Slips
   - งานค้าง (stuck_jobs) — สีแดง + ลิงก์ไปหน้า Jobs
   - หรือ "ระบบปกติ" สีเขียว
5. Charts (2 ช่อง):
   - รายได้ 30 วัน (Area chart, สีเขียว)
   - ผู้ใช้ใหม่ 30 วัน (Bar chart, สีม่วง)

API:
GET /api/v1/admin/dashboard/stats
GET /api/v1/admin/dashboard/charts?days=30
```

### Page 2: Users (ผู้ใช้งาน)

```
Route: /users

Sections:
1. Search bar + filter
2. Users table:
   - Columns: Avatar, Email, Name, Credits, Status, Last Login
   - Click row → slide-in detail panel (หรือ modal)
3. User Detail Panel:
   - ข้อมูลส่วนตัว: email, name, phone, hardware_id, tier
   - สถิติ: credits, total_topup, total_used, created_at, last_login
   - Actions (4 ปุ่ม):
     a. ปรับเครดิต (input amount + reason → POST adjust-credits)
     b. ระงับ/เปิดบัญชี (POST suspend / unsuspend)
     c. รีเซ็ต Hardware ID (POST reset-hardware)
     d. รีเซ็ตรหัสผ่าน (input new_password → POST reset-password)
   - Tabs:
     a. ประวัติเครดิต (transactions)
     b. ประวัติงาน (jobs)

API:
GET  /api/v1/admin/users?search=xxx
GET  /api/v1/admin/users/{uid}
GET  /api/v1/admin/users/{uid}/transactions
GET  /api/v1/admin/users/{uid}/jobs
POST /api/v1/admin/users/{uid}/adjust-credits
POST /api/v1/admin/users/{uid}/suspend
POST /api/v1/admin/users/{uid}/unsuspend
POST /api/v1/admin/users/{uid}/reset-hardware
POST /api/v1/admin/users/{uid}/reset-password
```

### Page 3: Slips (สลิปเติมเงิน)

```
Route: /slips

Sections:
1. Status filter: PENDING | VERIFIED | REJECTED | ALL
2. Slips table:
   - Columns: Date, User, Amount, Bank Ref, Status
   - Badge สี: PENDING=เหลือง, VERIFIED=เขียว, REJECTED=แดง
3. Slip Detail Panel (click row):
   - แสดงรูปสลิป (ถ้ามี)
   - ข้อมูล: user, amount, bank_ref, sender, receiver
   - Verification result จาก Slip2Go
   - Actions (ถ้า PENDING):
     a. อนุมัติ (input credit_amount → POST approve)
     b. ปฏิเสธ (input reason → POST reject)

API:
GET  /api/v1/admin/slips?status=PENDING
GET  /api/v1/admin/slips/{id}
POST /api/v1/admin/slips/{id}/approve
POST /api/v1/admin/slips/{id}/reject
```

### Page 4: Jobs (ตรวจสอบงาน)

```
Route: /jobs

Sections:
1. Status filter: ALL | RESERVED | COMPLETED | EXPIRED | FAILED
2. Jobs table:
   - Columns: Token, User, Mode, Files, Status, Created
3. Job Detail Panel (click row):
   - เครดิต: reserved / used / refunded
   - ไฟล์: success / failed
   - Metadata: model, version, hardware_id
   - Action (ถ้า RESERVED): "คืนเครดิต" → POST force-refund

API:
GET  /api/v1/admin/jobs?status=xxx
GET  /api/v1/admin/jobs/{id}
POST /api/v1/admin/jobs/{id}/force-refund
```

### Page 5: Finance — หน้าใหม่!

```
Route: /finance

นี่คือหน้าสำคัญที่ Streamlit ไม่มี — ระบบบัญชีการเงิน

Sections:
1. Date Range Picker: วันที่เริ่ม - วันที่สิ้นสุด
2. Summary Cards (4 ช่อง):
   - รายรับ (เงินเติม): ฿150,000 — สีเขียว
   - รายได้รับรู้ (เครดิตใช้): ฿98,500 — สี cyan
   - รายรับรอรับรู้ (ส่วนต่าง): ฿51,500 — สีเหลือง
   - ฐานภาษีโดยประมาณ: ฿98,500 — สีม่วง
3. Revenue Chart:
   - Dual line: เส้นรายรับ (เขียว) + เส้นรายได้รับรู้ (cyan)
   - Area fill ใต้เส้น
4. Daily Breakdown Table:
   - วันที่ | รายรับ | รายได้รับรู้ | จำนวนเติม | จำนวนงาน | ผู้ใช้ใหม่
   - Row click → expand แสดงรายละเอียด
5. Monthly Summary Table:
   - เดือน | รายรับ | รายได้รับรู้ | ส่วนต่าง | งาน | ผู้ใช้
   - สรุปรวมทั้งปี (YTD)
6. Export Buttons:
   - 📊 Export Excel — ส่งให้นักบัญชี
   - 📄 Export PDF — เก็บเป็นหลักฐาน

คำอธิบายเรื่อง "รายรับ" vs "รายได้รับรู้":
- รายรับ (topup_thb): เงินจริงที่ลูกค้าโอนเข้ามา
  คำนวณจาก: slips ที่ status=VERIFIED → sum(amount_detected)

- รายได้รับรู้ (recognized_thb): เครดิตที่ลูกค้าใช้จริง แปลงกลับเป็นบาท
  คำนวณจาก: jobs ที่ status=COMPLETED → sum(actual_usage) ÷ exchange_rate

- ส่วนต่าง (deferred_revenue): เงินที่ลูกค้าเติมแล้วแต่ยังไม่ใช้
  = topup_thb - recognized_thb
  (ตามหลักบัญชี ยังไม่นับเป็นรายได้จนกว่าจะใช้)

- ฐานภาษี: ใช้ "รายได้รับรู้" เป็นตัวตั้ง (ปรึกษานักบัญชีเพิ่มเติม)

API:
GET /api/v1/admin/finance/daily?from=xxx&to=xxx
GET /api/v1/admin/finance/monthly?year=2026
GET /api/v1/admin/finance/export?from=xxx&to=xxx&format=xlsx
```

### Page 6: System Config (ตั้งค่าระบบ)

```
Route: /settings

Sections (แบ่งเป็น tabs หรือ accordion):
1. เวอร์ชันแอป: latest_version, force_update_below, download_url, notes
2. อัตราเครดิต: istock photo/video, adobe photo/video, exchange_rate
3. บัญชีธนาคาร: bank_name, account_number, account_name
4. การประมวลผล: cache_threshold, max_images, max_videos
5. โหมดปิดปรับปรุง: toggle + message
6. พรอมต์: แสดงชื่อ + ขนาด + ปุ่มแก้ไข
7. คำต้องห้าม: แสดง tag chips + เพิ่ม/ลบ

API:
GET /api/v1/admin/config
PUT /api/v1/admin/config/version
PUT /api/v1/admin/config/rates
PUT /api/v1/admin/config/bank
PUT /api/v1/admin/config/processing
PUT /api/v1/admin/config/maintenance
PUT /api/v1/admin/config/prompts/{key}
PUT /api/v1/admin/config/blacklist
```

### Page 7: Audit Logs (บันทึกระบบ)

```
Route: /audit-logs

Sections:
1. Filters: severity dropdown + days input + search
2. Log entries list:
   - Severity dot (สี) + timestamp + event label + user email
   - Click → expand แสดง JSON details
   - Severity colors: INFO=น้ำเงิน, WARNING=เหลือง, ERROR=แดง

API:
GET /api/v1/admin/audit-logs?severity=WARNING&days=7
```

### Page 8: Promotions (โปรโมชั่น)

```
Route: /promotions

Sections:
1. Status filter + "สร้างใหม่" button
2. Promo cards/table:
   - Name, Code, Type, Status badge, Stats
   - Actions: Activate/Pause/Cancel/Clone/Edit
3. Create/Edit form (modal):
   - Name, Code, Type, Priority
   - Conditions: dates, min/max topup, max redemptions
   - Reward: bonus credits / override rate / percentage
   - Display: banner text, color, show flags
4. Stats panel:
   - Redemption count, bonus credits given, revenue, unique users
   - Redemption log table

API: (มีอยู่แล้ว)
POST   /api/v1/admin/promo/create
PUT    /api/v1/admin/promo/{id}
GET    /api/v1/admin/promo/list
GET    /api/v1/admin/promo/{id}
POST   /api/v1/admin/promo/{id}/activate
POST   /api/v1/admin/promo/{id}/pause
POST   /api/v1/admin/promo/{id}/cancel
POST   /api/v1/admin/promo/{id}/clone
GET    /api/v1/admin/promo/{id}/stats
```

### Page 9: Profile (ข้อมูลส่วนตัว — optional)

```
Route: /profile

แสดงข้อมูล admin ที่ login อยู่
- Email, name
- เปลี่ยนรหัสผ่าน
- Logout
```

---

## 7. โครงสร้างไฟล์

```
admin-web/
├── public/
│   └── favicon.ico
├── src/
│   ├── app/
│   │   ├── layout.tsx              ← Root layout + AuthProvider
│   │   ├── page.tsx                ← Redirect to /dashboard
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── users/
│   │   │   └── page.tsx
│   │   ├── slips/
│   │   │   └── page.tsx
│   │   ├── jobs/
│   │   │   └── page.tsx
│   │   ├── finance/
│   │   │   └── page.tsx
│   │   ├── settings/
│   │   │   └── page.tsx
│   │   ├── audit-logs/
│   │   │   └── page.tsx
│   │   └── promotions/
│   │       └── page.tsx
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx         ← Navigation sidebar
│   │   │   ├── MobileNav.tsx       ← Bottom nav for mobile
│   │   │   ├── Header.tsx          ← Page header + clock
│   │   │   └── AppShell.tsx        ← Sidebar + Content wrapper
│   │   ├── ui/                     ← shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── table.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── select.tsx
│   │   │   └── ...
│   │   ├── dashboard/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── AlertCard.tsx
│   │   │   ├── RevenueChart.tsx
│   │   │   └── UserGrowthChart.tsx
│   │   ├── finance/
│   │   │   ├── SummaryCards.tsx
│   │   │   ├── RevenueCompareChart.tsx
│   │   │   ├── DailyTable.tsx
│   │   │   ├── MonthlyTable.tsx
│   │   │   └── ExportButtons.tsx
│   │   ├── users/
│   │   │   ├── UsersTable.tsx
│   │   │   ├── UserDetail.tsx
│   │   │   ├── AdjustCreditsForm.tsx
│   │   │   └── ResetPasswordForm.tsx
│   │   ├── slips/
│   │   │   ├── SlipsTable.tsx
│   │   │   └── SlipReview.tsx
│   │   ├── jobs/
│   │   │   ├── JobsTable.tsx
│   │   │   └── JobDetail.tsx
│   │   └── shared/
│   │       ├── StatusBadge.tsx
│   │       ├── UserAvatar.tsx
│   │       ├── DateRangePicker.tsx
│   │       ├── Pagination.tsx
│   │       └── LoadingSpinner.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                  ← API client (fetch wrapper)
│   │   ├── auth.ts                 ← Auth context + JWT management
│   │   ├── types.ts                ← TypeScript interfaces
│   │   ├── utils.ts                ← Formatting, date helpers
│   │   └── constants.ts            ← Colors, config
│   │
│   └── styles/
│       └── globals.css             ← Tailwind + custom CSS vars
│
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── firebase.json                   ← Firebase Hosting config
```

---

## 8. Deploy

### Firebase Hosting Setup

```bash
# 1. Install Firebase CLI
npm install -g firebase-tools

# 2. Login
firebase login

# 3. Init hosting
firebase init hosting

# 4. Build Next.js as static export
npm run build

# 5. Deploy
firebase deploy --only hosting
```

### next.config.js (Static Export)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',        // Static HTML export
  trailingSlash: true,     // Required for Firebase Hosting
  images: {
    unoptimized: true,     // No image optimization for static
  },
}
module.exports = nextConfig
```

### firebase.json

```json
{
  "hosting": {
    "public": "out",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

### Environment Variables

```bash
# admin-web/.env.local (development)
NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1

# admin-web/.env.production
NEXT_PUBLIC_API_URL=https://bigeye-api-xxx.run.app/api/v1
```

---

## 9. ลำดับการสั่ง AI IDE

### Phase 1: Backend — Admin API (สั่ง 3 prompts)

```
Prompt 1:
"สร้างไฟล์ server/app/routers/admin.py
ที่มี endpoints ตามนี้:
- GET /admin/dashboard/stats
- GET /admin/dashboard/charts
- GET /admin/users (search, pagination)
- GET /admin/users/{uid}
- GET /admin/users/{uid}/transactions
- GET /admin/users/{uid}/jobs
- POST /admin/users/{uid}/adjust-credits
- POST /admin/users/{uid}/suspend
- POST /admin/users/{uid}/unsuspend
- POST /admin/users/{uid}/reset-hardware
- POST /admin/users/{uid}/reset-password

ทุก endpoint ต้องใช้ require_admin dependency เหมือน admin_promo.py
อ้างอิง field names จาก SCHEMA.md"

Prompt 2:
"เพิ่ม endpoints ใน server/app/routers/admin.py:
- GET /admin/slips (filter by status)
- GET /admin/slips/{id}
- POST /admin/slips/{id}/approve
- POST /admin/slips/{id}/reject
- GET /admin/jobs (filter by status)
- GET /admin/jobs/{id}
- POST /admin/jobs/{id}/force-refund
- GET /admin/config
- PUT /admin/config/version
- PUT /admin/config/rates
- PUT /admin/config/bank
- PUT /admin/config/processing
- PUT /admin/config/maintenance
- PUT /admin/config/prompts/{key}
- PUT /admin/config/blacklist
- GET /admin/audit-logs

Logic ย้ายมาจาก Streamlit pages — ดูตัวอย่างใน
admin/pages/3_Slips.py (approve_slip, reject_slip)
admin/pages/4_Jobs.py (force_refund_job)"

Prompt 3:
"เพิ่ม Finance endpoints ใน server/app/routers/admin.py:
- GET /admin/finance/daily?from=xxx&to=xxx
  คำนวณ:
  - topup_thb: sum slips VERIFIED ในช่วงวันที่
  - recognized_thb: sum jobs COMPLETED actual_usage ÷ exchange_rate
  - จำนวนเติม, งาน, ผู้ใช้ใหม่
- GET /admin/finance/monthly?year=2026
  สรุปรายเดือน + YTD
- GET /admin/finance/export?format=xlsx
  สร้างไฟล์ Excel ด้วย openpyxl ส่งกลับ

อย่าลืม register admin router ใน main.py:
app.include_router(admin.router, prefix=PREFIX)"
```

### Phase 2: React Frontend — Setup + Layout (สั่ง 2 prompts)

```
Prompt 4:
"สร้างโปรเจค Next.js ใน admin-web/:
npx create-next-app@latest admin-web --typescript --tailwind --app --src-dir

ติดตั้ง: shadcn/ui, recharts, lucide-react
สร้าง: design system (globals.css, colors, fonts)
สร้าง: AppShell (Sidebar + MobileNav + Content area)
สร้าง: AuthContext + Login page
สร้าง: API client (lib/api.ts)

Sidebar menu:
📊 แดชบอร์ด  /dashboard
👥 ผู้ใช้งาน  /users
🧾 สลิปเติมเงิน /slips
⚙️ ตรวจสอบงาน /jobs
💰 การเงิน   /finance
🔧 ตั้งค่า    /settings
📋 บันทึกระบบ /audit-logs
🎁 โปรโมชั่น  /promotions

ใช้สี dark theme ตาม Design Spec:
--bg-root: #06080f, --bg-surface: #0c1021"

Prompt 5:
"สร้าง shared components:
- MetricCard.tsx (icon, label, value, color, sub, trend)
- AlertCard.tsx (icon, title, desc, style, action)
- StatusBadge.tsx (active/pending/rejected/...)
- UserAvatar.tsx (initials + gradient)
- DataTable.tsx (generic sortable table)
- Pagination.tsx
- DateRangePicker.tsx
- LoadingSpinner.tsx

ทุก component ต้อง responsive (ใช้งานบนมือถือได้)"
```

### Phase 3: React Frontend — Pages (สั่ง 5 prompts)

```
Prompt 6:
"สร้างหน้า Dashboard (/dashboard):
- เรียก GET /admin/dashboard/stats
- แสดง MetricCards 4 + 3 ช่อง
- AlertCards (pending slips, stuck jobs)
- Revenue chart (Recharts Area) + User Growth chart (Recharts Bar)
- Dark theme, responsive"

Prompt 7:
"สร้างหน้า Users (/users) + Slips (/slips) + Jobs (/jobs):
- Users: search, table, detail panel, actions (adjust/suspend/reset)
- Slips: filter, table, review panel, approve/reject
- Jobs: filter, table, detail, force refund
- ทุกหน้าใช้ DataTable + StatusBadge"

Prompt 8:
"สร้างหน้า Finance (/finance) — สำคัญมาก:
- DateRangePicker
- Summary cards: รายรับ, รายได้รับรู้, ส่วนต่าง, ฐานภาษี
- Dual line chart: topup vs recognized
- Daily table + Monthly table
- Export buttons (Excel, PDF)
- อธิบายแต่ละตัวเลขด้วย tooltip"

Prompt 9:
"สร้างหน้า Settings (/settings):
- แบ่งเป็น tabs: Version, Rates, Bank, Processing, Maintenance, Prompts, Blacklist
- ทุก section มีฟอร์ม + save button
- Maintenance toggle สีแดง/เขียว
- Blacklist แสดงเป็น chips"

Prompt 10:
"สร้างหน้า Audit Logs (/audit-logs) + Promotions (/promotions):
- Audit Logs: severity filter, expandable entries, JSON details
- Promotions: CRUD + status actions + stats
- Promotions ใช้ API จาก admin_promo.py ที่มีอยู่แล้ว"
```

### Phase 4: Testing + Deploy (สั่ง 2 prompts)

```
Prompt 11:
"ทดสอบระบบทั้งหมด:
1. Run backend: uvicorn app.main:app --port 8080
2. Run frontend: cd admin-web && npm run dev
3. ทดสอบ login → dashboard → users → slips → jobs → finance → settings
4. ทดสอบบนมือถือ (responsive)
5. แก้ bug ที่พบ"

Prompt 12:
"Deploy:
1. Backend → Cloud Run (ถ้ายังไม่ได้ deploy)
2. Frontend → Firebase Hosting:
   cd admin-web
   npm run build
   firebase deploy --only hosting
3. ตั้ง NEXT_PUBLIC_API_URL ให้ชี้ไป Cloud Run"
```

---

## สรุป

| หัวข้อ | รายละเอียด |
|:--|:--|
| หน้าทั้งหมด | 10 หน้า (เพิ่ม Finance ใหม่) |
| Admin API ใหม่ | ~30 endpoints ใน admin.py |
| Tech | Next.js + TypeScript + Tailwind + shadcn/ui |
| Deploy | Firebase Hosting (ฟรี) |
| Responsive | Desktop + Tablet + Mobile |
| จำนวน Prompts | 12 prompts ทีละขั้น |
| ระยะเวลาโดยประมาณ | 2-3 วัน (สั่ง AI IDE ทีละ prompt) |
