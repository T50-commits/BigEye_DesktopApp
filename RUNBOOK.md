# BigEye Pro — คู่มือการรันระบบทั้งหมด

> อัปเดตล่าสุด: กุมภาพันธ์ 2026

---

## สารบัญ

1. [ภาพรวมระบบ](#1-ภาพรวมระบบ)
2. [ข้อกำหนดเบื้องต้น](#2-ข้อกำหนดเบื้องต้น)
3. [รัน Backend API Server](#3-รัน-backend-api-server)
4. [รัน Admin Dashboard (React/Next.js)](#4-รัน-admin-dashboard-reactnextjs)
5. [รัน Desktop Client (PyQt5)](#5-รัน-desktop-client-pyqt5)
6. [รันทุกระบบพร้อมกัน (One-liner)](#6-รันทุกระบบพร้อมกัน-one-liner)
7. [ข้อมูล Login สำหรับทดสอบ](#7-ข้อมูล-login-สำหรับทดสอบ)
8. [แก้ปัญหาที่พบบ่อย](#8-แก้ปัญหาที่พบบ่อย)

---

## 1. ภาพรวมระบบ

| ระบบ | เทคโนโลยี | Port | หน้าที่ |
|:--|:--|:--|:--|
| **Backend API** | FastAPI + Firestore | `8080` | API หลักสำหรับทุก client |
| **Admin Dashboard** | Next.js 14 + TypeScript | `3000` | หน้าจัดการระบบสำหรับ admin |
| **Desktop Client** | PyQt5 + Python | — | แอปตั้งโต๊ะสำหรับผู้ใช้ทั่วไป |

```
Desktop Client ──────┐
                      ├──► Backend API (port 8080) ──► Firestore (Cloud)
Admin Dashboard ─────┘
```

---

## 2. ข้อกำหนดเบื้องต้น

### ตรวจสอบก่อนรัน

```bash
# Python 3.12+
python3 --version

# Node.js 18+
node --version

# npm 9+
npm --version
```

### โครงสร้าง Directory ที่ต้องมี

```
BigEye_Desktop_App/
├── server/
│   ├── app/
│   ├── firebase-service-account.json   ← ต้องมีไฟล์นี้
│   └── requirements.txt
├── admin-web/
│   ├── src/
│   ├── package.json
│   └── .env.local                      ← ต้องมีไฟล์นี้
├── client/
│   └── main.py
└── .venv/                              ← Python virtual environment
```

### ตรวจสอบไฟล์สำคัญ

```bash
# ตรวจสอบ Firebase service account
ls server/firebase-service-account.json

# ตรวจสอบ .env.local ของ admin-web
cat admin-web/.env.local
# ควรเห็น: NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1
```

---

## 3. รัน Backend API Server

### วิธีรัน

```bash
# จาก root directory ของ project
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/server

GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json \
ADMIN_UIDS=VIhaucFahIZj1urMzpnl \
JWT_SECRET=bigeye-admin-secret-2026 \
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### ตรวจสอบว่ารันสำเร็จ

```bash
# ควรเห็น output:
# INFO: Application startup complete.
# INFO: Uvicorn running on http://0.0.0.0:8080

# ทดสอบ API
curl http://localhost:8080/api/v1/admin/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"cg.chithan@gmail.com","password":"Admin1234!"}'
# ควรได้ token กลับมา
```

### Environment Variables ที่ใช้

| Variable | ค่า | หน้าที่ |
|:--|:--|:--|
| `GOOGLE_APPLICATION_CREDENTIALS` | `firebase-service-account.json` | เชื่อมต่อ Firestore |
| `ADMIN_UIDS` | `VIhaucFahIZj1urMzpnl` | กำหนด user ที่เป็น admin |
| `JWT_SECRET` | `bigeye-admin-secret-2026` | ลงนาม JWT token |
| `SLIP2GO_SECRET_KEY` | *(ถ้ามี)* | ตรวจสอบสลิปโอนเงิน |

---

## 4. รัน Admin Dashboard (React/Next.js)

### ติดตั้ง dependencies (ครั้งแรกเท่านั้น)

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/admin-web
npm install
```

### รัน Development Server

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/admin-web
npm run dev
```

### ตรวจสอบว่ารันสำเร็จ

```bash
# ควรเห็น:
# ▲ Next.js 14.x.x
# ✓ Ready in 1300ms
# Local: http://localhost:3000

# เปิด browser ไปที่:
open http://localhost:3000
```

### Build สำหรับ Production

```bash
cd admin-web
npm run build
# ไฟล์จะอยู่ใน .next/ หรือ out/ (static export)
```

---

## 5. รัน Desktop Client (PyQt5)

### ตรวจสอบ Virtual Environment

```bash
# ตรวจสอบว่า .venv มีอยู่
ls /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/.venv

# Activate venv
source /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/.venv/bin/activate
```

### รัน Desktop Client

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App

source .venv/bin/activate

python3 client/main.py
```

### หมายเหตุ

- Client จะเชื่อมต่อ Backend ที่ `http://localhost:8080/api/v1` โดยอัตโนมัติ
- ต้องรัน Backend ก่อนเสมอ
- ถ้า login ไม่ได้ ให้กด **"ออกจากระบบ"** แล้ว login ใหม่

---

## 6. รันทุกระบบพร้อมกัน (One-liner)

### วิธีที่ 1: แยก Terminal 3 หน้าต่าง (แนะนำ)

**Terminal 1 — Backend:**
```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/server && \
GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json \
ADMIN_UIDS=VIhaucFahIZj1urMzpnl \
JWT_SECRET=bigeye-admin-secret-2026 \
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**Terminal 2 — Admin Dashboard:**
```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/admin-web && \
npm run dev
```

**Terminal 3 — Desktop Client:**
```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App && \
source .venv/bin/activate && \
python3 client/main.py
```

### วิธีที่ 2: Script เดียว (Background processes)

```bash
#!/bin/bash
# save เป็น start_all.sh แล้วรัน: bash start_all.sh

ROOT="/Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App"

echo "🚀 Starting Backend API..."
cd "$ROOT/server"
GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json \
ADMIN_UIDS=VIhaucFahIZj1urMzpnl \
JWT_SECRET=bigeye-admin-secret-2026 \
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

sleep 3

echo "🌐 Starting Admin Dashboard..."
cd "$ROOT/admin-web"
npm run dev &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

sleep 3

echo "🖥  Starting Desktop Client..."
cd "$ROOT"
source .venv/bin/activate
python3 client/main.py &
CLIENT_PID=$!
echo "   Client PID: $CLIENT_PID"

echo ""
echo "✅ All systems started!"
echo "   Backend:   http://localhost:8080"
echo "   Dashboard: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all..."
wait
```

### หยุดทุกระบบ

```bash
# หยุด Backend (port 8080)
lsof -ti:8080 | xargs kill -9

# หยุด Admin Dashboard (port 3000)
lsof -ti:3000 | xargs kill -9

# หยุด Desktop Client
pkill -f "python3 client/main.py"
```

---

## 7. ข้อมูล Login สำหรับทดสอบ

### Admin Dashboard (`localhost:3000`)

| Field | ค่า |
|:--|:--|
| Email | `cg.chithan@gmail.com` |
| Password | `Admin1234!` |

### Desktop Client

| Field | ค่า |
|:--|:--|
| Email | `cg.chithan@gmail.com` |
| Password | `Admin1234!` |

### Test Users

| Email | Password | หมายเหตุ |
|:--|:--|:--|
| `test@bigeye.pro` | *(ดูใน Firestore)* | Test user 1 |
| `test02@bigeye.pro` | *(ดูใน Firestore)* | Test user 2 |

---

## 8. แก้ปัญหาที่พบบ่อย

### ❌ Admin Dashboard หน้าดำ / ไม่แสดง Login Form

```bash
# 1. ลบ cache แล้ว restart
cd admin-web
rm -rf .next
npm run dev

# 2. เปิด browser ที่ http://localhost:3000/login/
# 3. กด Cmd+Shift+R (Hard Refresh)
```

### ❌ Backend ไม่ start — "Address already in use"

```bash
# หยุด process ที่ใช้ port 8080
lsof -ti:8080 | xargs kill -9
# แล้วรัน backend ใหม่
```

### ❌ Desktop Client แสดง 0 เครดิต / 401 Unauthorized

```
สาเหตุ: Token หมดอายุหรือ password ถูกเปลี่ยน
แก้ไข: กด "ออกจากระบบ" ใน client แล้ว login ใหม่
```

### ❌ Backend Error: "GOOGLE_APPLICATION_CREDENTIALS not set"

```bash
# ตรวจสอบว่าไฟล์ service account มีอยู่
ls server/firebase-service-account.json

# รันพร้อม credentials
cd server
GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json python3 -m uvicorn app.main:app --port 8080
```

### ❌ npm install ล้มเหลว

```bash
cd admin-web
rm -rf node_modules package-lock.json
npm install
```

### ❌ Python venv ไม่มี / packages หาย

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
```

### ❌ Firestore Index Error (ใน backend logs)

```
สาเหตุ: Query บาง query ต้องการ Composite Index ใน Firestore
แก้ไข: คลิก URL ใน error message เพื่อสร้าง index อัตโนมัติ
       หรือไปที่ Firebase Console > Firestore > Indexes
```

---

## ลำดับการรันที่ถูกต้อง

```
1. Backend API  (รอจนเห็น "Application startup complete")
       ↓
2. Admin Dashboard  (รอจนเห็น "Ready in Xms")
       ↓
3. Desktop Client  (เปิดหน้าต่างขึ้นมา)
```

> ⚠️ **สำคัญ:** ต้องรัน Backend ก่อนเสมอ ทั้ง Admin Dashboard และ Desktop Client ต้องการ Backend เพื่อ login และดึงข้อมูล
