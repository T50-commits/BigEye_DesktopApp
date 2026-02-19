# BigEye Pro — คู่มือการรันระบบทั้งหมด

> อัปเดตล่าสุด: กุมภาพันธ์ 2026 (Production Deployed)

---

## สารบัญ

1. [ภาพรวมระบบ](#1-ภาพรวมระบบ)
2. [URLs Production](#2-urls-production)
3. [ข้อกำหนดเบื้องต้น (Local Dev)](#3-ข้อกำหนดเบื้องต้น-local-dev)
4. [รัน Backend API Server (Local)](#4-รัน-backend-api-server-local)
5. [รัน Admin Dashboard (Local)](#5-รัน-admin-dashboard-local)
6. [รัน Desktop Client](#6-รัน-desktop-client)
7. [Re-deploy Production](#7-re-deploy-production)
8. [ข้อมูล Login](#8-ข้อมูล-login)
9. [แก้ปัญหาที่พบบ่อย](#9-แก้ปัญหาที่พบบ่อย)

---

## 1. ภาพรวมระบบ

| ระบบ | เทคโนโลยี | สถานะ | URL |
|:--|:--|:--|:--|
| **Backend API** | FastAPI + Firestore (Cloud Run) | Production ✅ | `https://bigeye-api-671665186709.asia-southeast1.run.app` |
| **Admin Dashboard** | Next.js 14 (Netlify) | Production ✅ | `https://legendary-raindrop-bcb488.netlify.app` |
| **Desktop Client** | PySide6 + Python | Local App | รันบนเครื่อง user |

```
Desktop Client ──────┐
                      ├──► Cloud Run API ──► Firestore (asia-southeast1)
Admin Dashboard ─────┘         │
                                └──► Secret Manager (JWT, AES, Slip2Go)
```

---

## 2. URLs Production

| รายการ | URL |
|:--|:--|
| **API Base URL** | `https://bigeye-api-671665186709.asia-southeast1.run.app/api/v1` |
| **Health Check** | `https://bigeye-api-671665186709.asia-southeast1.run.app/api/v1/system/health` |
| **Admin Dashboard** | `https://legendary-raindrop-bcb488.netlify.app` |
| **GCP Project** | `bigeye-pro` (region: `asia-southeast1`) |
| **Firestore** | Firebase Console → Project `bigeye-pro` |
| **Cloud Run** | GCP Console → Cloud Run → `bigeye-api` |
| **Netlify** | `https://app.netlify.com/projects/legendary-raindrop-bcb488` |

### ทดสอบ Production API

```bash
# Health check
curl https://bigeye-api-671665186709.asia-southeast1.run.app/api/v1/system/health
# ควรได้: {"status":"ok","version":"2.0.0","environment":"production"}

# Login admin
curl -X POST https://bigeye-api-671665186709.asia-southeast1.run.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@bigeye.pro","password":"BigEye@Admin2026!","hardware_id":"ADMIN_DASHBOARD_001"}'
```

---

## 3. ข้อกำหนดเบื้องต้น (Local Dev)

```bash
# Python 3.12+
python3 --version

# Node.js 18+
node --version

# gcloud CLI (สำหรับ re-deploy)
gcloud --version
```

### โครงสร้าง Directory

```
BigEye_Desktop_App/
├── server/
│   ├── app/
│   ├── firebase-service-account.json   ← ต้องมีไฟล์นี้ (local dev เท่านั้น)
│   └── requirements.txt
├── admin-web/
│   ├── src/
│   ├── netlify.toml                    ← มี NEXT_PUBLIC_API_URL production แล้ว
│   └── package.json
├── client/
│   └── main.py
└── .venv/                              ← Python virtual environment
```

---

## 4. รัน Backend API Server (Local)

> ใช้สำหรับ development เท่านั้น — production ใช้ Cloud Run

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/server

GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json \
ADMIN_UIDS=IWg95X1Kw5jA2sqYpfyk \
JWT_SECRET=dev-secret-local \
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Environment Variables (Local)

| Variable | ค่า | หน้าที่ |
|:--|:--|:--|
| `GOOGLE_APPLICATION_CREDENTIALS` | `firebase-service-account.json` | เชื่อมต่อ Firestore |
| `ADMIN_UIDS` | `IWg95X1Kw5jA2sqYpfyk` | user ที่เป็น admin |
| `JWT_SECRET` | *(ค่าใดก็ได้สำหรับ local)* | ลงนาม JWT token |
| `SLIP2GO_SECRET_KEY` | *(จาก slip2go.com)* | ตรวจสอบสลิปโอนเงิน |

---

## 5. รัน Admin Dashboard (Local)

> ใช้สำหรับ development เท่านั้น — production ใช้ Netlify

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/admin-web

# ครั้งแรก
npm install

# รัน dev server (ชี้ไป localhost:8080)
NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1 npm run dev
```

เปิด browser: `http://localhost:3000`

---

## 6. รัน Desktop Client

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App

source .venv/bin/activate

python3 client/main.py
```

- Client ชี้ production API โดยอัตโนมัติ (`client/core/config.py`)
- ถ้าต้องการชี้ local: `BIGEYE_API_URL=http://localhost:8080/api/v1 python3 client/main.py`

---

## 7. Re-deploy Production

### Re-deploy Backend (Cloud Run)

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/server

gcloud run deploy bigeye-api \
  --source . \
  --region asia-southeast1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi --cpu 1 \
  --concurrency 20 \
  --min-instances 0 --max-instances 5 \
  --timeout 60 \
  --set-secrets "JWT_SECRET=JWT_SECRET:latest,AES_KEY=AES_KEY:latest,SLIP2GO_SECRET_KEY=SLIP2GO_SECRET_KEY:latest" \
  --set-env-vars "SLIP2GO_API_URL=https://connect.slip2go.com,SLIP2GO_RECEIVER_NAME=พงษ์เทพ,GOOGLE_CLOUD_PROJECT=bigeye-pro,ENVIRONMENT=production,ADMIN_UIDS=IWg95X1Kw5jA2sqYpfyk" \
  --project=bigeye-pro
```

### Re-deploy Admin Dashboard (Netlify)

```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/admin-web

# Build
NEXT_PUBLIC_API_URL="https://bigeye-api-671665186709.asia-southeast1.run.app/api/v1" npm run build

# Deploy ไปที่ site เดิม
npx --yes netlify-cli deploy --dir=.next --prod --site=a7e665cb-c6e3-4984-b372-e09d29dc51f7
```

### อัพเดท Secret ใน Secret Manager

```bash
# เพิ่ม version ใหม่ให้ secret (เช่น เปลี่ยน SLIP2GO_SECRET_KEY)
echo -n "NEW_SECRET_VALUE" | gcloud secrets versions add SLIP2GO_SECRET_KEY --data-file=- --project=bigeye-pro

# เพิ่ม LINE_NOTIFY_TOKEN (ถ้ายังไม่มี)
echo -n "YOUR_LINE_TOKEN" | gcloud secrets create LINE_NOTIFY_TOKEN --data-file=- --project=bigeye-pro
gcloud secrets add-iam-policy-binding LINE_NOTIFY_TOKEN \
  --member="serviceAccount:671665186709-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" --project=bigeye-pro
gcloud run services update bigeye-api --region asia-southeast1 \
  --update-secrets "LINE_NOTIFY_TOKEN=LINE_NOTIFY_TOKEN:latest" --project=bigeye-pro
```

---

## 8. ข้อมูล Login

### Admin Account (Production)

| Field | ค่า |
|:--|:--|
| Email | `admin@bigeye.pro` |
| Password | `BigEye@Admin2026!` |
| User ID | `IWg95X1Kw5jA2sqYpfyk` |
| Hardware ID | `ADMIN_DASHBOARD_001` |

### GCP / Cloud

| รายการ | ค่า |
|:--|:--|
| GCP Project | `bigeye-pro` |
| GCP Account | `cg.chithan@gmail.com` |
| Netlify Account | `cg.chithan@gmail.com` |
| Netlify Site ID | `a7e665cb-c6e3-4984-b372-e09d29dc51f7` |

### Secrets ใน Secret Manager

| Secret | หมายเหตุ |
|:--|:--|
| `JWT_SECRET` | สร้างอัตโนมัติตอน deploy (random hex 32) |
| `AES_KEY` | 64 hex chars — ต้องตรงกับ `AES_KEY_HEX` ใน `client/core/config.py` |
| `SLIP2GO_SECRET_KEY` | จาก slip2go.com dashboard |

> ⚠️ **หมายเหตุ AES_KEY:** ค่าปัจจุบันใช้ค่า default `0123456789abcdef...` ควรเปลี่ยนเป็นค่าสุ่มจริงก่อนใช้งาน production จริง และอัพเดทค่าเดียวกันใน `client/core/config.py` บรรทัด `AES_KEY_HEX`

---

## 9. แก้ปัญหาที่พบบ่อย

### ❌ API ตอบ 500 / Container crash

```bash
# ดู logs ล่าสุดจาก Cloud Run
gcloud run services logs read bigeye-api --region asia-southeast1 --project=bigeye-pro --limit 50
```

### ❌ Admin Dashboard หน้าดำ / ไม่แสดง Login Form

```bash
cd admin-web
rm -rf .next
npm run dev
# เปิด http://localhost:3000/login
# กด Cmd+Shift+R (Hard Refresh)
```

### ❌ Backend Local ไม่ start — "Address already in use"

```bash
lsof -ti:8080 | xargs kill -9
```

### ❌ Desktop Client แสดง 0 เครดิต / 401 Unauthorized

```
สาเหตุ: Token หมดอายุ (7 วัน) หรือ password ถูกเปลี่ยน
แก้ไข: กด "ออกจากระบบ" ใน client แล้ว login ใหม่
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
สาเหตุ: Query ต้องการ Composite Index
แก้ไข: คลิก URL ใน error message เพื่อสร้าง index อัตโนมัติ
       หรือไปที่ Firebase Console > Firestore > Indexes
```

### ❌ gcloud: "not logged in"

```bash
gcloud auth login
gcloud config set project bigeye-pro
```

---

## ลำดับการรัน (Local Dev)

```
1. Backend API  →  รอจนเห็น "Application startup complete"
       ↓
2. Admin Dashboard  →  รอจนเห็น "Ready in Xms"
       ↓
3. Desktop Client  →  หน้าต่างเปิดขึ้นมา
```

> ⚠️ **สำคัญ:** ต้องรัน Backend ก่อนเสมอ ทั้ง Admin Dashboard และ Desktop Client ต้องการ Backend เพื่อ login และดึงข้อมูล
