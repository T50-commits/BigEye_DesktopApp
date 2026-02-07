# BigEye Pro — Database Design & Security Architecture
### Version 2.0 | Backend: Firebase Firestore + Cloud Run
### Author: System Architect | Date: February 2026

---

## สารบัญ (Table of Contents)

1. [สรุปฟังก์ชันจากโปรแกรมเดิม (Legacy Feature Inventory)](#1-legacy-feature-inventory)
2. [ภาพรวมสถาปัตยกรรม (Architecture Overview)](#2-architecture-overview)
3. [Firestore Schema Definition](#3-firestore-schema-definition)
4. [Security Rules](#4-security-rules)
5. [ระบบการเงินและเครดิต (Credit & Financial System)](#5-credit--financial-system)
6. [ระบบบัญชีและรายงาน (Accounting & Reporting)](#6-accounting--reporting)
7. [Reserve-Refund Protocol (Detail)](#7-reserve-refund-protocol)
8. [Slip Verification & Top-Up Flow](#8-slip-verification--top-up-flow)
9. [Anti-Cheat & Anti-Piracy](#9-anti-cheat--anti-piracy)
10. [Scalability & Concurrency](#10-scalability--concurrency)
11. [Logging & Audit Trail](#11-logging--audit-trail)
12. [Update Notification System](#12-update-notification-system)
13. [Credit Insufficiency Handling](#13-credit-insufficiency-handling)
14. [Cost Optimization Notes](#14-cost-optimization-notes)
15. [ไอเดียสำหรับการออกแบบขั้นถัดไป (Future Design Ideas)](#15-future-design-ideas)

---

## 1. Legacy Feature Inventory

จากการวิเคราะห์ `app.py`, `config.py`, และ Prompt Files ทั้งหมด ฟังก์ชันที่มีอยู่ในโปรแกรมเดิมมีดังนี้:

### 1.1 Core AI Processing
| # | Feature | รายละเอียด | ไฟล์ต้นทาง |
|---|---------|-----------|-----------|
| 1 | **Gemini AI Integration** | เรียก Google Gemini API พร้อม Safety Settings, JSON Response Mode | `app.py:865-869` |
| 2 | **Multi-Model Support** | รองรับ gemini-2.5-pro, 2.5-flash, 2.0-flash, 3-pro-preview | `app.py:1253-1258` |
| 3 | **Batch Processing** | ประมวลผลหลายไฟล์พร้อมกัน (ThreadPoolExecutor, max 8 workers) | `app.py:1642-1657` |
| 4 | **Context Caching** | สำหรับ iStock Mode เมื่อไฟล์ ≥10 → Cache Dictionary ไว้ใน Gemini ลด Token Cost | `app.py:1592-1616` |
| 5 | **Orphaned Cache Cleanup** | ลบ Cache และไฟล์ที่ค้างจาก Session ก่อน (อายุ > 1 ชม.) | `app.py:283-318` |
| 6 | **Exponential Backoff Retry** | Retry สูงสุด 3 ครั้ง, รอเพิ่มขึ้นทุกรอบ | `app.py:948-951` |
| 7 | **Dynamic Timeout** | คำนวณ Timeout ตามขนาดไฟล์ (สูงสุด 2x base) | `app.py:493-501` |

### 1.2 Keyword Processing Pipeline
| # | Feature | รายละเอียด | ไฟล์ต้นทาง |
|---|---------|-----------|-----------|
| 8 | **Stemming Deduplication** | ใช้ NLTK SnowballStemmer ตัดคำซ้ำรากศัพท์ (run/running → run) | `app.py:532-625` |
| 9 | **Irregular Word Map** | จัดการคำผิดปกติ (women→woman, children→child, better→good) | `app.py:552-561` |
| 10 | **Copyright/Blacklist Filter** | กรองคำต้องห้าม (Brands: nike, iphone, samsung + Stop words + Quality specs) | `app.py:543-549` |
| 11 | **Phrase Preservation** | รักษาวลี (2+ คำ) ไว้ก่อน แล้วเพิ่มคำเดี่ยวทีหลัง | `app.py:607-624` |
| 12 | **Phrase Explosion (Deconstruction)** | แตกวลีเป็นคำเดี่ยว ("Home Office" → "Home", "Office") สำหรับ Adobe/Hybrid | `app.py:628-709` |
| 13 | **Over-Fetch + Trim** | ขอ AI สร้าง Keywords เกินเป้า +10-15 คำ แล้วตัดให้พอดี | `app.py:811, 839` |
| 14 | **Stem Filter (Single Words)** | สำหรับ Shutterstock — เก็บคำที่สั้นที่สุดต่อ 1 stem | `app.py:712-738` |

### 1.3 Platform Modes & Prompts
| # | Feature | รายละเอียด | ไฟล์ต้นทาง |
|---|---------|-----------|-----------|
| 15 | **iStock Mode** | Dictionary-Strict — ทุก Keyword ต้องอยู่ใน Reference Dictionary เท่านั้น | `prompt_iStock.md` |
| 16 | **Hybrid Mode (Adobe)** | Phrase-First Strategy — วลี+คำเดี่ยว, Deconstruction Method | `PROMPT_HYBRID_MODE.md` |
| 17 | **Single Words Mode (Shutterstock)** | คำเดี่ยวล้วน, แตกทุกวลี (ยกเว้น "Ice cream", "Real estate") | `prompt_Single_words.md` |
| 18 | **Keyword Style Selector** | UI ให้เลือก Hybrid / Single Words (เฉพาะ Adobe & Shutterstock) | `config.py:KEYWORD_MODE_OPTIONS` |

### 1.4 Video Processing
| # | Feature | รายละเอียด | ไฟล์ต้นทาง |
|---|---------|-----------|-----------|
| 19 | **FFmpeg Proxy Creation** | บีบอัด Video เป็น 480p, CRF 28, Ultrafast preset | `app.py:1014-1100` |
| 20 | **Cross-Platform FFmpeg** | รองรับ Windows/macOS (ARM+Intel)/Linux | `app.py:1042-1071` |
| 21 | **Proxy Cleanup** | ลบไฟล์ Proxy ทั้งหมดเมื่อปิดโปรแกรม (atexit) | `app.py:33-54` |
| 22 | **Poster Timecode** | AI วิเคราะห์เฟรมที่ดีที่สุด ส่งกลับเป็น HH:MM:SS:FF | `config.py:VIDEO_INSTRUCTION_TEXT` |
| 23 | **Timecode Normalizer** | แปลง Timecode ทุกรูปแบบเป็น HH:MM:SS:FF | `app.py:504-529` |
| 24 | **Shot Speed Detection** | AI ระบุว่า Real Time / Slow Motion / Time Lapse | `config.py:VIDEO_INSTRUCTION_TEXT` |

### 1.5 CSV Export
| # | Feature | รายละเอียด | ไฟล์ต้นทาง |
|---|---------|-----------|-----------|
| 25 | **iStock CSV (Photo)** | Columns: file name, created date, description, country, brief code, title, keywords, Niche Strategy, Missing Keywords | `config.py:ISTOCK_COLS_PHOTO` |
| 26 | **iStock CSV (Video)** | Columns: file name, description, country, title, keywords, poster timecode, date created, shot speed, Missing Keywords | `config.py:ISTOCK_COLS_VIDEO` |
| 27 | **Adobe CSV** | Columns: Filename, Title, Keywords, Category, Releases | `config.py:ADOBE_CSV_COLUMNS` |
| 28 | **Shutterstock CSV** | Columns: Filename, Description, Keywords, Categories, Illustration, Mature Content, Editorial | `config.py:SHUTTERSTOCK_CSV_COLUMNS` |
| 29 | **Auto Photo/Video Split** | iStock แยก CSV เป็น 2 ไฟล์ (Photo + Video) อัตโนมัติ | `app.py:1751-1773` |
| 30 | **Filename Suffix** | ใส่ชื่อ Model + Timestamp ท้ายไฟล์ CSV | `app.py:1708-1712` |

### 1.6 File Organization & Reporting
| # | Feature | รายละเอียด | ไฟล์ต้นทาง |
|---|---------|-----------|-----------|
| 31 | **Completed Folder** | สร้างโฟลเดอร์ `Completed_[platform]_[style]_[timestamp]` | `app.py:321-346` |
| 32 | **Success/Error Reports** | สร้าง TXT Report จำแนกตาม Error Type พร้อมคำแนะนำแก้ไข | `app.py:370-469` |
| 33 | **Error Classification** | จัดหมวด Error: QUOTA, RATE_LIMIT, TIMEOUT, PERMISSION, JSON_PARSE, CONTENT_BLOCKED, NETWORK | `app.py:954-996` |
| 34 | **Notification Sound** | เล่นเสียงเมื่อเสร็จ | `app.py:1008-1011` |

### 1.7 Existing Security & Config
| # | Feature | รายละเอียด | ไฟล์ต้นทาง |
|---|---------|-----------|-----------|
| 35 | **Encrypted API Key Storage** | บันทึก API Key แบบเข้ารหัส (.enc) | `app.py:57, 74-88` |
| 36 | **Server-Side Prompts** | Prompt ทั้ง 3 โหมดดึงจาก Server (ไม่เก็บใน Client) | `app.py:94-116` |
| 37 | **Server-Side Dictionary** | Keyword Dictionary ดึงจาก Server (RAM Only) | `app.py:59-69` |
| 38 | **License Check** | ตรวจสอบ License Online ก่อนใช้งาน | `app.py:145-147` |
| 39 | **Usage Reporting** | รายงานจำนวนภาพ/วิดีโอที่ประมวลผลกลับ Server | `app.py:1803-1812` |
| 40 | **Memory Cleanup (gc.collect)** | เรียก gc.collect() หลังประมวลผลแต่ละไฟล์ | `app.py:1006` |

### 1.8 UI Features (ต้อง Port ไป PySide6)
| # | Feature | รายละเอียด |
|---|---------|-----------|
| 41 | **Folder Picker** | Cross-platform (AppleScript Mac, Tkinter Windows, Zenity Linux) |
| 42 | **Progress Bar + File Counter** | แสดงความคืบหน้าแบบ Real-time |
| 43 | **Start/Stop Controls** | หยุดงานกลางคันได้ (stop_flag) |
| 44 | **Settings Lock During Processing** | ล็อค Slider/ComboBox ระหว่างประมวลผล |
| 45 | **Completion Summary** | แสดงสรุป Photo/Video Count + Output Folder |
| 46 | **Debug: Check Active Caches** | ปุ่มตรวจสอบ Cache ที่ค้างอยู่ |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    BIGEYE PRO ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐     ┌──────────────────────────┐  │
│  │   CLIENT (Desktop)   │     │    BACKEND (Cloud Run)    │  │
│  │   PySide6 + Nuitka   │◄───►│    FastAPI + Firestore    │  │
│  │                      │HTTPS│                            │  │
│  │  ┌────────────────┐  │     │  ┌──────────────────────┐ │  │
│  │  │ Auth Module     │  │     │  │ /auth/register       │ │  │
│  │  │ Hardware ID     │  │     │  │ /auth/login          │ │  │
│  │  └────────────────┘  │     │  │ /job/reserve         │ │  │
│  │  ┌────────────────┐  │     │  │ /job/finalize        │ │  │
│  │  │ Job Manager     │  │     │  │ /credit/topup       │ │  │
│  │  │ Reserve→Process │  │     │  │ /credit/balance     │ │  │
│  │  │ →Finalize       │  │     │  │ /system/check-update│ │  │
│  │  └────────────────┘  │     │  └──────────────────────┘ │  │
│  │  ┌────────────────┐  │     │  ┌──────────────────────┐ │  │
│  │  │ Gemini Engine   │  │     │  │  Firestore DB        │ │  │
│  │  │ (Client-Side)   │──────►│  │  ┌─ users            │ │  │
│  │  │ API Key = User's│  │     │  │  ├─ jobs             │ │  │
│  │  └────────────────┘  │     │  │  ├─ transactions     │ │  │
│  │  ┌────────────────┐  │     │  │  ├─ slips            │ │  │
│  │  │ Keyword Refiner │  │     │  │  ├─ system_config   │ │  │
│  │  │ Stemming+Filter │  │     │  │  └─ audit_logs      │ │  │
│  │  └────────────────┘  │     │  └──────────────────────┘ │  │
│  │  ┌────────────────┐  │     │  ┌──────────────────────┐ │  │
│  │  │ CSV Exporter    │  │     │  │  Slip Verifier       │ │  │
│  │  │ 3 Formats       │  │     │  │  (3rd Party API)     │ │  │
│  │  └────────────────┘  │     │  └──────────────────────┘ │  │
│  └──────────────────────┘     └──────────────────────────┘  │
│                                                               │
│  KEY PRINCIPLE: "Intelligent Vending Machine"                 │
│  → Client has NO prompts/dictionary until it PAYS (reserves)  │
│  → Gemini API runs on CLIENT machine, using CLIENT's API Key  │
│  → Server only delivers config AFTER credit deduction          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Firestore Schema Definition

### 3.1 Collection: `users`

```
users/{user_id}
├── email: string (unique, indexed)
├── password_hash: string (bcrypt)
├── full_name: string
├── phone: string
├── hardware_id: string (SHA256 hash, 16 chars upper)
├── tier: string ("standard" | "premium") [default: "standard"]
├── credits: number (integer, atomic counter) [default: 0]
├── status: string ("active" | "suspended" | "banned") [default: "active"]
├── created_at: timestamp
├── last_login: timestamp
├── last_active: timestamp
├── total_topup_baht: number [default: 0]  ← สำหรับติดตามรายได้
├── total_credits_used: number [default: 0]  ← สำหรับดูสถิติ
├── app_version: string  ← เวอร์ชันล่าสุดที่ใช้
└── metadata: map
    ├── os: string ("Windows" | "macOS" | "Linux")
    ├── registration_ip: string
    └── notes: string (Admin memo)
```

**Indexes Required:**
- `email` → Unique
- `status` + `last_active` → สำหรับหา Inactive Users
- `created_at` → สำหรับรายงานการเติบโต

---

### 3.2 Collection: `jobs`

```
jobs/{job_id}
├── job_token: string (UUID v4, unique)
├── user_id: string (ref → users)
├── status: string ("RESERVED" | "PROCESSING" | "COMPLETED" | "REFUNDED" | "EXPIRED" | "FAILED")
├── mode: string ("iStock" | "Adobe" | "Shutterstock")
├── keyword_style: string | null ("Hybrid" | "Single Words" | null)
├── file_count: number (จำนวนไฟล์ที่ขอ Reserve)
├── photo_count: number [default: 0]
├── video_count: number [default: 0]
├── credit_rate: number (3 สำหรับ iStock, 2 สำหรับ Adobe/Shutterstock)
├── reserved_credits: number (= file_count × credit_rate)
├── actual_usage: number [default: 0] (= success_count × credit_rate)
├── refund_amount: number [default: 0]
├── success_count: number [default: 0]
├── failed_count: number [default: 0]
├── created_at: timestamp
├── completed_at: timestamp | null
├── expires_at: timestamp (created_at + 2 hours)
└── client_info: map
    ├── app_version: string
    ├── model_used: string (e.g. "gemini-2.5-pro")
    └── hardware_id: string
```

**Indexes Required:**
- `user_id` + `created_at` → ดู Job History
- `status` + `expires_at` → สำหรับ Scheduled Cleanup (หา RESERVED ที่หมดอายุ)
- `job_token` → Unique Lookup

**Status Flow:**
```
RESERVED → PROCESSING → COMPLETED
                      → FAILED
         → EXPIRED (auto-refund by Cloud Scheduler)
         → REFUNDED (manual/auto)
```

---

### 3.3 Collection: `transactions`

```
transactions/{tx_id}
├── user_id: string (ref → users)
├── type: string ("TOPUP" | "RESERVE" | "REFUND" | "ADJUSTMENT" | "BONUS")
├── amount: number (จำนวนเครดิต, +/-)
│   ├── TOPUP: +เครดิต
│   ├── RESERVE: -เครดิต (เมื่อจอง job)
│   ├── REFUND: +เครดิต (คืนจาก job ที่ไม่ใช้ครบ)
│   └── ADJUSTMENT: +/- (Admin แก้ไขมือ)
├── balance_after: number (ยอดคงเหลือหลัง transaction)
├── reference_id: string | null
│   ├── TOPUP → slip_id
│   ├── RESERVE → job_id
│   ├── REFUND → job_id
│   └── ADJUSTMENT → "admin_[reason]"
├── description: string (คำอธิบาย เช่น "Top-up 100 THB", "Reserve 30 credits for iStock job")
├── created_at: timestamp
└── metadata: map
    ├── baht_amount: number | null (เฉพาะ TOPUP — จำนวนเงินจริง)
    ├── slip_ref: string | null
    └── admin_by: string | null (เฉพาะ ADJUSTMENT)
```

**Indexes Required:**
- `user_id` + `created_at` → Statement / ดูรายการย้อนหลัง
- `type` + `created_at` → รายงานตามประเภท
- `created_at` → รายงานรายวัน/เดือน (สำหรับภาษี)

---

### 3.4 Collection: `slips`

```
slips/{slip_id}
├── user_id: string (ref → users)
├── status: string ("PENDING" | "VERIFIED" | "REJECTED" | "DUPLICATE")
├── image_url: string (Cloud Storage path)
├── amount_detected: number | null (จำนวนเงินที่ตรวจพบจากสลิป)
├── amount_credited: number | null (จำนวนเครดิตที่เติมให้)
├── bank_ref: string | null (เลข Ref จากสลิป)
├── verification_method: string ("AUTO_API" | "MANUAL")
├── verification_result: map | null
│   ├── provider: string (e.g. "SlipOK", "EasySlip")
│   ├── raw_response: map
│   └── confidence: number
├── reject_reason: string | null
├── created_at: timestamp
├── verified_at: timestamp | null
└── metadata: map
    ├── sender_name: string | null
    ├── receiver_account: string | null
    └── transfer_time: string | null
```

**Indexes Required:**
- `user_id` + `created_at` → ดูประวัติสลิป
- `status` + `created_at` → Admin ดู pending slips
- `bank_ref` → ป้องกัน Duplicate (ส่งสลิปซ้ำ)

---

### 3.5 Collection: `system_config` (Singleton-style)

```
system_config/app_settings
├── prompts: map
│   ├── prompt_istock: string (encrypted)
│   ├── prompt_hybrid: string (encrypted)
│   └── prompt_single: string (encrypted)
├── dictionary_url: string (URL to download dictionary)
├── dictionary_hash: string (SHA256 สำหรับ verify integrity)
├── blacklist: array<string> (คำต้องห้าม: ["nike", "adidas", "iphone", ...])
├── credit_rates: map
│   ├── istock_photo: 3
│   ├── istock_video: 3
│   ├── adobe_photo: 2
│   ├── adobe_video: 2
│   ├── shutterstock_photo: 2
│   └── shutterstock_video: 2
├── exchange_rate: number (1 baht = 4 credits)
├── app_latest_version: string (e.g. "2.0.1")
├── app_download_url: string
├── app_update_notes: string (release notes)
├── force_update_below: string | null (ต่ำกว่าเวอร์ชันนี้บังคับอัปเดต)
├── maintenance_mode: boolean [default: false]
├── maintenance_message: string
├── context_cache_threshold: number [default: 20]
├── max_concurrent_images: number [default: 5]
├── max_concurrent_videos: number [default: 2]
└── updated_at: timestamp
```

---

### 3.6 Collection: `audit_logs`

```
audit_logs/{log_id}
├── event_type: string
│   ├── "USER_REGISTER"
│   ├── "USER_LOGIN"
│   ├── "LOGIN_FAILED_DEVICE_MISMATCH"
│   ├── "LOGIN_FAILED_WRONG_PASSWORD"
│   ├── "TOPUP_SUCCESS"
│   ├── "TOPUP_REJECTED"
│   ├── "JOB_RESERVED"
│   ├── "JOB_COMPLETED"
│   ├── "JOB_FAILED"
│   ├── "JOB_EXPIRED_AUTO_REFUND"
│   ├── "CREDIT_ADJUSTMENT"
│   ├── "SUSPICIOUS_ACTIVITY"
│   └── "SYSTEM_ERROR"
├── user_id: string | null
├── details: map (ข้อมูลเพิ่มเติมตาม event)
├── ip_address: string | null
├── severity: string ("INFO" | "WARNING" | "ERROR" | "CRITICAL")
├── created_at: timestamp
└── metadata: map (ข้อมูลเสริม)
```

**Indexes Required:**
- `event_type` + `created_at` → กรอง event
- `user_id` + `created_at` → ดู activity ของ user
- `severity` + `created_at` → ดู error/critical events

---

### 3.7 Collection: `daily_reports` (ไอเดีย — Auto-Generated)

```
daily_reports/{YYYY-MM-DD}
├── date: string
├── new_users: number
├── active_users: number (unique users ที่ทำ job วันนี้)
├── total_topup_baht: number
├── total_credits_sold: number
├── total_credits_used: number
├── total_jobs: number
├── total_files_processed: number
├── revenue_breakdown: map
│   ├── istock_credits: number
│   ├── adobe_credits: number
│   └── shutterstock_credits: number
├── error_count: number
└── generated_at: timestamp
```

> **Note:** Collection นี้สร้างอัตโนมัติด้วย Cloud Scheduler (ทุกเที่ยงคืน) เพื่อให้ Admin ดูรายงานได้ทันทีโดยไม่ต้อง query หนักๆ เหมาะสำหรับใช้ยื่นภาษีและติดตามการเติบโต

---

## 4. Security Rules

### 4.1 Firestore Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // ============================================
    // HELPER FUNCTIONS
    // ============================================
    function isAuthenticated() {
      return request.auth != null;
    }

    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }

    function isAdmin() {
      // Admin UID hardcoded (เปลี่ยนเป็น Custom Claims ในอนาคต)
      return isAuthenticated() && request.auth.uid in ['ADMIN_UID_HERE'];
    }

    function isServiceAccount() {
      // Cloud Run Service Account
      return request.auth.token.email_verified == true
        && request.auth.token.email.matches('.*@.*\\.iam\\.gserviceaccount\\.com');
    }

    // ============================================
    // USERS COLLECTION
    // ============================================
    match /users/{userId} {
      // User อ่านข้อมูลตัวเองได้ (จำกัด fields)
      allow read: if isOwner(userId);

      // NEVER allow client to write credits directly
      // credits ต้องถูกเปลี่ยนผ่าน Server (Cloud Run) เท่านั้น
      allow update: if isOwner(userId)
        && !request.resource.data.diff(resource.data).affectedKeys()
            .hasAny(['credits', 'tier', 'status', 'hardware_id', 'total_topup_baht']);
      // ↑ User แก้ไขได้เฉพาะ: full_name, phone, app_version, metadata.os

      // Registration ผ่าน Server เท่านั้น
      allow create: if false; // Client CANNOT create users directly

      // Delete ไม่อนุญาต
      allow delete: if false;
    }

    // ============================================
    // JOBS COLLECTION
    // ============================================
    match /jobs/{jobId} {
      // User ดู Job ของตัวเองได้
      allow read: if isAuthenticated()
        && resource.data.user_id == request.auth.uid;

      // Client ไม่สามารถสร้าง/แก้ไข Job ได้โดยตรง
      // ต้องผ่าน API Endpoint (/job/reserve, /job/finalize) เท่านั้น
      allow create, update, delete: if false;
    }

    // ============================================
    // TRANSACTIONS COLLECTION
    // ============================================
    match /transactions/{txId} {
      // User ดูรายการของตัวเองได้ (Read-Only)
      allow read: if isAuthenticated()
        && resource.data.user_id == request.auth.uid;

      // ห้ามแก้ไข/ลบ — Immutable Ledger
      allow create, update, delete: if false;
    }

    // ============================================
    // SLIPS COLLECTION
    // ============================================
    match /slips/{slipId} {
      // User ดูสลิปของตัวเองได้
      allow read: if isAuthenticated()
        && resource.data.user_id == request.auth.uid;

      // Client ไม่สามารถแก้ไขสถานะสลิป
      allow create, update, delete: if false;
    }

    // ============================================
    // SYSTEM CONFIG — READ-ONLY (ผ่าน Server เท่านั้น)
    // ============================================
    match /system_config/{docId} {
      allow read, write: if false;
      // ↑ Client ต้องเรียกผ่าน API /job/reserve เพื่อรับ config
      // ไม่ให้อ่านตรงจาก Firestore เพราะ Prompts เป็นความลับ
    }

    // ============================================
    // AUDIT LOGS — WRITE-ONLY BY SERVER
    // ============================================
    match /audit_logs/{logId} {
      allow read: if isAdmin();
      allow write: if false; // Server writes via Admin SDK
    }

    // ============================================
    // DAILY REPORTS — ADMIN ONLY
    // ============================================
    match /daily_reports/{reportId} {
      allow read: if isAdmin();
      allow write: if false; // Generated by Cloud Scheduler
    }

    // ============================================
    // CATCH-ALL: DENY EVERYTHING ELSE
    // ============================================
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

### 4.2 Security Principles Summary

| Principle | Implementation |
|-----------|---------------|
| **Credits = Server-Only** | Client ไม่สามารถแก้ไข `credits` ได้ — ต้องผ่าน Cloud Run API เท่านั้น |
| **Immutable Transactions** | `transactions` collection เป็น append-only — ห้าม edit/delete |
| **No Direct Config Access** | Client ไม่สามารถอ่าน `system_config` จาก Firestore ตรงๆ ต้องผ่าน `/job/reserve` |
| **Hardware Binding** | 1 Account = 1 Hardware ID — ป้องกันแชร์ Account |
| **Job Token Validation** | ทุก `/job/finalize` ต้องตรวจสอบว่า `job.user_id == caller.user_id` |
| **Slip Duplicate Check** | ตรวจ `bank_ref` ซ้ำก่อนเติมเงิน |
| **AES Encrypted Payloads** | Prompts และ Dictionary ถูกเข้ารหัส AES ระหว่างส่ง Server→Client |
| **JWT Auth** | ทุก Request ต้องมี JWT Token ใน Header |

---

## 5. Credit & Financial System

### 5.1 Credit Pricing

```
┌──────────────────────────────────────────────┐
│           CREDIT PRICING TABLE                │
├──────────────────────────────────────────────┤
│  1 บาท = 4 เครดิต                            │
│                                                │
│  ┌─────────────┬────────┬──────────┐          │
│  │ Platform    │ Photo  │ Video    │          │
│  ├─────────────┼────────┼──────────┤          │
│  │ iStock      │ 3 cr.  │ 3 cr.   │          │
│  │ Adobe       │ 2 cr.  │ 2 cr.   │          │
│  │ Shutterstock│ 2 cr.  │ 2 cr.   │          │
│  └─────────────┴────────┴──────────┘          │
│                                                │
│  ตัวอย่าง:                                      │
│  เติม 100 บาท = 400 เครดิต                     │
│  ใช้ iStock 100 ภาพ = 300 เครดิต               │
│  ใช้ Adobe 100 ภาพ = 200 เครดิต                │
│  คงเหลือ (iStock): 100 เครดิต (= 25 บาท)      │
│  คงเหลือ (Adobe): 200 เครดิต (= 50 บาท)       │
└──────────────────────────────────────────────┘
```

### 5.2 Top-Up Flow (Auto)

```
User Upload Slip
      │
      ▼
POST /credit/topup (slip image + user_id)
      │
      ▼
┌─────────────────────┐
│ 1. Save slip image  │ → Cloud Storage
│    to slips/{id}    │
│    status: PENDING  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 2. Call Slip API    │ → SlipOK / EasySlip
│    (3rd Party)      │
└─────────┬───────────┘
          │
     ┌────┴────┐
     │         │
   VALID    INVALID
     │         │
     ▼         ▼
┌──────────┐  ┌──────────────┐
│ 3a.CHECK │  │ 3b. REJECT   │
│ Duplicate│  │ status:      │
│ bank_ref │  │ REJECTED     │
└────┬─────┘  │ Notify User  │
     │        └──────────────┘
  ┌──┴──┐
  │     │
 NEW  DUPE
  │     │
  ▼     ▼
┌──────────┐  ┌──────────────┐
│ 4. ADD   │  │ REJECT:      │
│ CREDITS  │  │ DUPLICATE    │
│ Atomic   │  └──────────────┘
│ Transaction│
└────┬─────┘
     │
     ▼
┌──────────────────────────┐
│ 5. Create Transaction    │
│    type: TOPUP           │
│    amount: baht × 4      │
│    Update user.credits   │
│    Update slip: VERIFIED │
└──────────────────────────┘
```

### 5.3 Supported Top-Up Amounts (Suggestion)

| เงินจริง (บาท) | เครดิตที่ได้ | เหมาะสำหรับ |
|:-:|:-:|:--|
| 50 | 200 | ทดลองใช้ (~66 ภาพ Adobe) |
| 100 | 400 | ใช้งานทั่วไป |
| 300 | 1,200 | ใช้งานหนัก |
| 500 | 2,000 | Professional |
| 1,000 | 4,000 | Power User |

---

## 6. Accounting & Reporting

### 6.1 รายงานสำหรับยื่นภาษี

ข้อมูลจาก `transactions` collection สามารถ Query ได้ทันที:

```
รายงานรายได้ (Monthly Revenue Report)
─────────────────────────────────────
Query: transactions WHERE type == "TOPUP"
       AND created_at BETWEEN [start] AND [end]

Output:
├── ยอดรวมเงินเข้า (THB): SUM(metadata.baht_amount)
├── จำนวนรายการ: COUNT
├── ค่าเฉลี่ยต่อรายการ: AVG(metadata.baht_amount)
└── รายละเอียดแยกรายวัน: GROUP BY DATE(created_at)
```

### 6.2 รายงานสำหรับ Admin Dashboard

| รายงาน | Query Strategy | ประโยชน์ |
|--------|---------------|---------|
| **Daily Active Users** | `daily_reports.active_users` | ดูการเติบโต |
| **Revenue Per Day** | `daily_reports.total_topup_baht` | รายได้ |
| **Popular Platform** | `daily_reports.revenue_breakdown` | วิเคราะห์ตลาด |
| **Churn Risk** | `users WHERE last_active < 30 days ago` | ติดตาม User ที่หายไป |
| **Credit Balance Distribution** | `users GROUP BY credit ranges` | ดูพฤติกรรมเติมเงิน |
| **Error Rate** | `daily_reports.error_count / total_jobs` | ดูสุขภาพระบบ |
| **Top Users** | `users ORDER BY total_credits_used DESC` | VIP Management |

### 6.3 Tax-Ready Export

```python
# Cloud Function ที่เรียกจาก Admin Panel
def export_monthly_revenue(year: int, month: int) -> CSV:
    """
    Export: วันที่, เลข Ref สลิป, จำนวนเงิน, ชื่อผู้โอน, สถานะ
    → พร้อมยื่น สรรพากร / ทำบัญชี
    """
```

---

## 7. Reserve-Refund Protocol (Detail)

### 7.1 Reserve Flow

```
POST /job/reserve
─────────────────
Input:
{
  "file_count": 50,
  "mode": "iStock",        // "iStock" | "Adobe" | "Shutterstock"
  "keyword_style": null,    // "Hybrid" | "Single Words" (สำหรับ Adobe/SS)
  "model": "gemini-2.5-pro",
  "app_version": "2.0.1"
}

Server Logic:
─────────────
1. Validate JWT Token → get user_id
2. Check user.status == "active"
3. Check app_version >= force_update_below (ถ้ามี)
4. Determine rate:
   - iStock → 3 credits/file
   - Adobe/Shutterstock → 2 credits/file
5. total_cost = rate × file_count
6. BEGIN FIRESTORE TRANSACTION:
   a. READ user.credits
   b. IF credits < total_cost → ABORT (HTTP 402 Payment Required)
   c. user.credits -= total_cost (ATOMIC)
   d. CREATE job document (status: "RESERVED")
   e. CREATE transaction (type: "RESERVE", amount: -total_cost)
   f. COMMIT
7. Fetch system_config (prompts, dictionary, blacklist)
8. Encrypt sensitive data with AES
9. RETURN:
   {
     "job_token": "uuid-xxx",
     "config": {
       "prompts": { encrypted },
       "dictionary_url": "https://...",
       "dictionary_hash": "sha256...",
       "blacklist": ["nike", "adidas", ...],
       "cache_threshold": 20,
       "max_concurrent_images": 5,
       "max_concurrent_videos": 2
     }
   }
```

### 7.2 Finalize Flow

```
POST /job/finalize
──────────────────
Input:
{
  "job_token": "uuid-xxx",
  "success_count": 45,
  "failed_count": 5,
  "photo_count": 40,
  "video_count": 5
}

Server Logic:
─────────────
1. Validate JWT Token → get user_id
2. Fetch job by job_token
3. VALIDATE:
   a. job.user_id == caller user_id (ป้องกันใช้ token คนอื่น)
   b. job.status == "RESERVED" or "PROCESSING"
   c. success_count + failed_count <= job.file_count
   d. success_count <= job.file_count (ป้องกันโกง claim เกิน)
4. actual_cost = success_count × job.credit_rate
5. refund = job.reserved_credits - actual_cost
6. BEGIN FIRESTORE TRANSACTION:
   a. IF refund > 0:
      - user.credits += refund
      - CREATE transaction (type: "REFUND", amount: +refund)
   b. UPDATE job:
      - status: "COMPLETED"
      - actual_usage: actual_cost
      - refund_amount: refund
      - success_count, failed_count, photo_count, video_count
      - completed_at: NOW
   c. COMMIT
7. CREATE audit_log (event: "JOB_COMPLETED")
8. RETURN: { "status": "ok", "refunded": refund, "balance": new_balance }
```

### 7.3 Expired Job Auto-Refund

```
Cloud Scheduler (ทุก 30 นาที):
─────────────────────────────
1. Query: jobs WHERE status == "RESERVED" AND expires_at < NOW
2. For each expired job:
   a. REFUND full reserved_credits back to user
   b. UPDATE job status: "EXPIRED"
   c. CREATE transaction (type: "REFUND", desc: "Auto-refund expired job")
   d. CREATE audit_log (event: "JOB_EXPIRED_AUTO_REFUND")
```

---

## 8. Slip Verification & Top-Up Flow

### 8.1 Recommended 3rd Party APIs (ต้นทุนต่ำ)

| Provider | ราคา | จุดเด่น |
|----------|------|---------|
| **SlipOK** (slipok.com) | ~0.5-1 บาท/ครั้ง | Thai-focused, API ง่าย |
| **EasySlip** | Free tier 20 ครั้ง/วัน | เหมาะ 100-200 users |
| **Manual Queue** | Free | Admin ตรวจเอง (Fallback) |

### 8.2 Recommended Flow for Solo Admin

```
Priority 1: Auto (EasySlip Free Tier)
  → 20 slips/day free
  → ถ้าเกิน → ขยับไป SlipOK

Priority 2: Semi-Auto (Fallback)
  → ถ้า API ล่ม → สลิปเข้า Queue "PENDING"
  → Admin เปิดดูสลิปจาก Admin Panel
  → กด Approve/Reject มือ
  → ระบบเติมเครดิตให้อัตโนมัติ
```

### 8.3 Anti-Fraud Checks

| Check | วิธี | ป้องกัน |
|-------|------|--------|
| **Duplicate Slip** | ตรวจ `bank_ref` ซ้ำใน `slips` collection | ส่งสลิปเก่าซ้ำ |
| **Amount Mismatch** | เทียบ amount ที่ API อ่านได้ vs amount ที่ User claim | แก้ไขสลิป |
| **Time Window** | สลิปต้องไม่เก่าเกิน 24 ชม. | ใช้สลิปเก่า |
| **Receiver Account** | ตรวจว่าโอนเข้าบัญชีที่ถูกต้อง | โอนเข้าบัญชีอื่น |
| **Rate Limit** | สูงสุด 5 slips/hour/user | Spam |

---

## 9. Anti-Cheat & Anti-Piracy

### 9.1 Protection Layers

```
Layer 1: HARDWARE BINDING
─────────────────────────
- get_hardware_id() = SHA256(WMIC UUID + CPU ID)[:16].upper()
- 1 Account = 1 Hardware ID
- เปลี่ยนเครื่อง → ต้องติดต่อ Admin

Layer 2: NUITKA COMPILATION
───────────────────────────
- Source code → .exe/.app (Native binary)
- ไม่มี .py file ให้ Decompile
- ป้องกัน Reverse Engineering ระดับหนึ่ง

Layer 3: SERVER-GATED CONTENT
─────────────────────────────
- Prompts อยู่บน Server → Client ไม่มี Logic จนกว่าจะจ่ายเงิน
- Dictionary ดาวน์โหลดมา RAM → ลบทิ้งเมื่อจบ Job
- Blacklist ส่งมาพร้อม Job Config → อยู่ใน RAM เท่านั้น

Layer 4: JOB TOKEN VALIDATION
────────────────────────────
- ทุก Job ต้องมี valid token จาก Server
- Token ผูกกับ user_id → ใช้ของคนอื่นไม่ได้
- Token มีอายุ 2 ชม. → หมดอายุ = auto-refund

Layer 5: ENCRYPTED TRANSPORT
────────────────────────────
- HTTPS + AES Encrypted Payload
- Prompts ถูกเข้ารหัส → แม้ดักจับ Traffic ก็อ่านไม่ออก

Layer 6: BEHAVIORAL MONITORING
──────────────────────────────
- ตรวจจับ Pattern ผิดปกติ:
  - success_count > file_count → BLOCK
  - finalize โดยไม่เคย reserve → BLOCK
  - เรียก API ถี่ผิดปกติ → Rate Limit
  - Hardware ID เปลี่ยนบ่อย → Flag for review
```

### 9.2 Cheat Scenarios & Countermeasures

| Scenario | วิธีโกง | ป้องกัน |
|----------|--------|--------|
| **แชร์ Account** | ส่ง Login ให้เพื่อน | Hardware ID Mismatch → HTTP 403 |
| **แก้ไข success_count** | ส่ง finalize กับ success=0 เพื่อ Refund ทั้งหมด | ✅ ได้ refund จริง แต่ไม่ได้ประโยชน์ (ไม่มี CSV) |
| **Replay Token** | ใช้ job_token ซ้ำ | Token มี status check — COMPLETED แล้วใช้ซ้ำไม่ได้ |
| **Bypass Client** | เขียน Script เรียก API ตรง | JWT + Hardware ID check ทุก Request |
| **Extract Prompts** | Decompile + Memory dump | Prompts อยู่ใน RAM ชั่วคราว + Encrypted + Nuitka binary |
| **Fake Slip** | ทำสลิปปลอม | 3rd Party Slip API ตรวจ + Duplicate check |
| **Claim มากกว่าทำจริง** | success_count > actual | Server validate: success + failed ≤ file_count |

---

## 10. Scalability & Concurrency

### 10.1 Capacity Planning

| Scale | Users | Firestore Reads/Day | Cloud Run | Cost Est. |
|-------|-------|-------------------|-----------|-----------|
| **Current** | 100-200 | ~10,000 | Min instances: 0, Max: 2 | ~$5-15/mo |
| **Growth** | 500 | ~50,000 | Min: 0, Max: 5 | ~$30-50/mo |
| **Target** | 1,000 | ~100,000 | Min: 1, Max: 10 | ~$80-150/mo |

### 10.2 Concurrency Handling

```
สถานการณ์: User A และ User B กด Reserve พร้อมกัน
──────────────────────────────────────────────
Firestore Transaction ทำงานแบบ Optimistic Locking:

1. Transaction A reads user_A.credits = 100
2. Transaction B reads user_B.credits = 200
3. Transaction A writes user_A.credits = 70 → COMMIT ✓
4. Transaction B writes user_B.credits = 140 → COMMIT ✓
→ ไม่มีปัญหา เพราะคนละ Document

สถานการณ์: User A กด Reserve 2 ครั้งพร้อมกัน (Double-Click)
──────────────────────────────────────────────────────────
1. Transaction 1 reads user_A.credits = 100
2. Transaction 2 reads user_A.credits = 100
3. Transaction 1 writes user_A.credits = 70 → COMMIT ✓
4. Transaction 2 tries to write → CONFLICT → RETRY
5. Transaction 2 re-reads user_A.credits = 70
6. Transaction 2 writes user_A.credits = 40 → COMMIT ✓
→ Firestore handles this automatically (Atomic Transaction)
```

### 10.3 Cloud Run Auto-Scaling

```yaml
# cloud-run-config
min-instances: 0          # ประหยัด: ไม่เสียเงินเมื่อไม่มีคนใช้
max-instances: 10         # รับ burst ได้
concurrency: 80           # 80 requests/instance
cpu: 1                    # 1 vCPU per instance
memory: 512Mi             # เพียงพอสำหรับ FastAPI
timeout: 60s              # Request timeout
```

---

## 11. Logging & Audit Trail

### 11.1 สิ่งที่ต้อง Log เสมอ

| Event | Severity | ข้อมูลที่บันทึก |
|-------|----------|----------------|
| User Register | INFO | email, hardware_id, ip |
| User Login | INFO | email, hardware_id, ip, success/fail |
| Device Mismatch | WARNING | email, expected_hw, actual_hw, ip |
| Top-Up Success | INFO | user_id, amount_baht, credits, slip_ref |
| Top-Up Rejected | WARNING | user_id, reason, slip_id |
| Job Reserved | INFO | user_id, job_token, mode, file_count, credits_deducted |
| Job Completed | INFO | user_id, job_token, success/fail counts, refund |
| Job Expired | WARNING | user_id, job_token, refunded_credits |
| Credit Adjustment | WARNING | admin_id, user_id, amount, reason |
| Suspicious Activity | CRITICAL | user_id, details, ip |
| System Error | ERROR | endpoint, error_msg, stack_trace |

### 11.2 Client-Side Logging

```
Client บันทึก debug_log.txt เหมือนเดิม:
- Gemini API calls (success/fail)
- File processing status
- Cache operations
- Error details with classification
→ ช่วย User ส่ง Log มาให้ Admin debug
```

---

## 12. Update Notification System

### 12.1 Flow

```
App Startup:
1. Client → GET /system/check-update
   Body: { "current_version": "2.0.0" }

2. Server checks system_config:
   - latest_version: "2.0.1"
   - force_update_below: "1.9.0"

3. Response:
   IF current < force_update_below:
     → { "action": "FORCE_UPDATE", "url": "...", "notes": "..." }
     → Client แสดง Dialog บังคับอัปเดต (ปิดไม่ได้)

   ELIF current < latest_version:
     → { "action": "OPTIONAL_UPDATE", "url": "...", "notes": "..." }
     → Client แสดง Dialog แนะนำ (ปิดได้)

   ELSE:
     → { "action": "UP_TO_DATE" }
```

---

## 13. Credit Insufficiency Handling

### 13.1 Flow เมื่อเครดิตไม่พอ

```
User เลือก 100 ภาพ, โหมด iStock (3 cr/file)
ต้องใช้: 300 credits
คงเหลือ: 200 credits

Client Logic:
──────────────
1. ก่อนกด START → Client คำนวณ:
   estimated_cost = file_count × rate
   IF estimated_cost > balance:
     → แสดง Warning Dialog:
       "เครดิตไม่เพียงพอ!
        ต้องใช้: 300 เครดิต
        คงเหลือ: 200 เครดิต
        ขาดอีก: 100 เครดิต (= 25 บาท)

        [เติมเงิน] [ทำเท่าที่มี (66 ภาพ)] [ยกเลิก]"

2. ถ้าเลือก "ทำเท่าที่มี":
   → Client คำนวณ: max_files = floor(balance / rate)
   → ส่ง reserve กับ file_count = max_files
   → User เลือก files ที่ต้องการทำก่อน (หรือ Auto: ทำตามลำดับ)

3. ถ้า Server ตอบ 402 (เครดิตไม่พอ):
   → Client แสดง Error + ปุ่ม [เติมเงิน]
```

### 13.2 Partial Processing

```python
# Client-side logic
max_affordable = user_credits // credit_rate
if max_affordable < file_count:
    # Show dialog to user
    choice = show_insufficient_credit_dialog(
        required=file_count * credit_rate,
        available=user_credits,
        max_files=max_affordable
    )
    if choice == "PARTIAL":
        file_count = max_affordable
        # User can select which files to process first
    elif choice == "TOPUP":
        show_topup_screen()
        return
    else:
        return  # Cancel
```

---

## 14. Cost Optimization Notes

### 14.1 Firebase/GCP Cost Breakdown

| Service | Free Tier | คาดการณ์ 200 Users | คาดการณ์ 1000 Users |
|---------|-----------|-------------------|---------------------|
| **Firestore Reads** | 50K/day | ~10K/day (Free) | ~100K/day (~$0.06/day) |
| **Firestore Writes** | 20K/day | ~2K/day (Free) | ~20K/day (Free) |
| **Cloud Run** | 2M req/mo | ~20K req/mo (Free) | ~200K req/mo (~$5/mo) |
| **Cloud Storage** | 5GB | ~1GB slips (Free) | ~10GB slips (~$0.26/mo) |
| **Cloud Scheduler** | 3 jobs free | 1-2 jobs (Free) | 2-3 jobs (Free) |
| **Total** | - | **~$0-5/mo** | **~$10-30/mo** |

### 14.2 Optimization Strategies

- **Cloud Run min-instances: 0** → ไม่เสียเงินเมื่อไม่มีคนใช้ (Cold start ~2s ยอมรับได้)
- **Firestore Composite Indexes** → ลด Read operations
- **daily_reports** → Pre-aggregated data → ลด Query หนักๆ
- **Slip Image Lifecycle** → ลบสลิปที่ VERIFIED/REJECTED เกิน 90 วัน
- **Client-side caching** → Cache balance, user info ใน RAM (TTL 5 min)

---

## 15. Future Design Ideas

### 15.1 ไอเดียสำหรับ Database ขั้นถัดไป

| ไอเดีย | รายละเอียด | Priority |
|--------|-----------|----------|
| **Referral System** | Collection `referrals` — ให้โบนัสเครดิตเมื่อชวนเพื่อน | Medium |
| **Credit Packages** | Collection `packages` — แพ็คเกจเติมเงินพร้อมโปรโมชั่น (เช่น เติม 500 ได้ 2,200 cr) | High |
| **Usage Analytics** | Collection `usage_stats` — เก็บ Token usage, processing time per file, model comparison | Medium |
| **Admin Panel** | Simple web dashboard (Flask/Streamlit) อ่านจาก Firestore | High |
| **Subscription Tier** | เพิ่ม tier "premium" — ได้ rate ถูกกว่า (เช่น iStock 2 cr แทน 3) | Low |
| **Webhook Notifications** | LINE Notify / Telegram Bot แจ้ง Admin เมื่อมีเติมเงิน/Error | High |
| **Rate Limiting Collection** | `rate_limits/{user_id}` — track API calls per minute/hour | Medium |
| **Announcement System** | `announcements` collection — แจ้งข่าวสาร/โปรโมชั่นใน Client | Low |
| **Dictionary Versioning** | `dictionaries/{version}` — track dictionary updates, rollback ได้ | Medium |
| **Backup Strategy** | Firestore scheduled exports to Cloud Storage (weekly) | High |

### 15.2 Admin Notification (สำหรับคนทำงานคนเดียว)

```
LINE Notify / Telegram Bot:
─────────────────────────
เมื่อมี Event สำคัญ → ส่ง Notification ให้ Admin ทันที:

🟢 "User XXX เติม 300 บาท (1,200 cr) — Balance: 1,500 cr"
🟡 "Slip PENDING — User YYY ส่งสลิป 500 บาท (รอตรวจ)"
🔴 "⚠️ User ZZZ — Device Mismatch (possible account sharing)"
🔴 "⚠️ System Error Rate > 10% in last hour"
🔵 "Daily Report: 15 active users, ฿1,500 revenue, 450 jobs"
```

---

## Appendix A: Firestore Data Model Diagram

```
users ──────────┐
  │              │
  │  1:N         │  1:N
  │              │
  ▼              ▼
jobs         transactions
  │              │
  │  1:1         │  1:1 (via reference_id)
  │              │
  ▼              ▼
(job_token)    slips

system_config (singleton)
audit_logs (append-only)
daily_reports (auto-generated)
```

## Appendix B: API Endpoint Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | None | สมัครสมาชิก |
| POST | `/auth/login` | None | Login + Hardware Check |
| GET | `/credit/balance` | JWT | ดูยอดเครดิต |
| POST | `/credit/topup` | JWT | อัปโหลดสลิป |
| GET | `/credit/history` | JWT | ดูรายการย้อนหลัง |
| POST | `/job/reserve` | JWT | จอง Job + รับ Config |
| POST | `/job/finalize` | JWT | จบ Job + Refund |
| GET | `/system/check-update` | JWT | เช็คเวอร์ชัน |
| GET | `/system/health` | None | Health Check |

---

*สิ้นสุดเอกสาร — พร้อมสำหรับการออกแบบขั้นถัดไป (Implementation)*
