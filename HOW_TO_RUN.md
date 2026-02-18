# BigEye Pro — วิธีรันทุกระบบเพื่อทดสอบ

## ข้อกำหนดเบื้องต้น

- Python 3.12+
- ไฟล์ `server/.env` ที่มี `GOOGLE_APPLICATION_CREDENTIALS` ชี้ไปที่ Firebase service account JSON
- ไฟล์ `server/firebase-service-account.json`

---

## 1. Server (FastAPI) — Port 8080

```bash
cd server
export $(cat .env | xargs) && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

> ⚠️ ต้องรันบน port **8080** เพราะ Client ตั้งค่า API_BASE_URL เป็น `http://localhost:8080/api/v1`

### ติดตั้ง dependencies (ครั้งแรก)
```bash
cd server
pip install -r requirements.txt
```

---

## 2. Admin Dashboard (Streamlit) — Port 8501

```bash
cd admin
ADMIN_PASSWORD=bigeye2026 \
GOOGLE_APPLICATION_CREDENTIALS=/path/to/server/firebase-service-account.json \
streamlit run app.py --server.port 8501
```

> แก้ `/path/to/server/firebase-service-account.json` ให้เป็น absolute path จริงของเครื่อง
> เช่น `/Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/server/firebase-service-account.json`

**รหัสผ่าน Admin:** `bigeye2026` (หรือค่าที่ตั้งใน `ADMIN_PASSWORD`)

### ติดตั้ง dependencies (ครั้งแรก)
```bash
cd admin
pip install -r requirements.txt
```

---

## 3. Client (PySide6 Desktop App)

```bash
cd client
python3 main.py
```

> ⚠️ ต้องรัน Server (ข้อ 1) ก่อน ไม่งั้น Client จะเชื่อมต่อไม่ได้

### ติดตั้ง dependencies (ครั้งแรก)
```bash
cd client
pip install -r requirements.txt
```

---

## รันทั้ง 3 ระบบพร้อมกัน (เปิด 3 Terminal)

### Terminal 1 — Server
```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/server
export $(cat .env | xargs) && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Terminal 2 — Admin
```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/admin
ADMIN_PASSWORD=bigeye2026 \
GOOGLE_APPLICATION_CREDENTIALS=/Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/server/firebase-service-account.json \
streamlit run app.py --server.port 8501
```

### Terminal 3 — Client
```bash
cd /Users/pongtepchithan/Desktop/iStockMetaData_Database/BigEye_Desktop_App/client
python3 main.py
```

---

## URLs

| ระบบ | URL |
|------|-----|
| Server API | http://localhost:8080 |
| Server Docs (dev only) | http://localhost:8080/docs |
| Admin Dashboard | http://localhost:8501 |
| Client | Desktop app (PySide6 window) |

---

## หยุดระบบ

กด `Ctrl+C` ในแต่ละ Terminal เพื่อหยุดแต่ละระบบ
