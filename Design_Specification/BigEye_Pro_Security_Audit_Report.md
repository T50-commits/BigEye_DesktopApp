# BigEye Pro — Security Audit Report
### ผลตรวจจากโค้ดจริง (5 routers + config + security + dependencies)
### วันที่: February 2026

---

## สรุป: พบ 23 จุดเสี่ยง

| ความรุนแรง | จำนวน |
|:-:|:-:|
| 🔴 วิกฤต (ถูกโกงได้เลย) | 5 |
| 🟠 สูง (ต้องแก้ก่อน Go-Live) | 8 |
| 🟡 กลาง (ควรแก้) | 7 |
| 🔵 ต่ำ (ปรับปรุง) | 3 |

---

# 🔴 วิกฤต — แก้ทันที

---

## 🔴 C-01: TopUp ข้าม SlipOK — Auto-Approve ทุกอัน!

**ไฟล์:** `credit.py` บรรทัด ~120-135

```python
# ❌ ปัญหาร้ายแรง: ทุกสลิปถูก VERIFIED อัตโนมัติ!
slip_data = {
    "user_id": user_id,
    "status": "VERIFIED",           # ← Auto-approve ทุกอัน!
    "verification_method": "AUTO_DEV",
    "amount_detected": req.amount,   # ← เชื่อจำนวนเงินจาก Client!
    "bank_ref": None,               # ← ไม่มี bank_ref = ไม่มี duplicate check!
}
```

**วิธีโกง:**
```
แฮคเกอร์ส่ง: POST /credit/topup {"amount": 999999}
→ ไม่ต้องส่งสลิปจริง ไม่ต้องโอนเงิน
→ ได้ 999999 × 4 = 3,999,996 เครดิตฟรี!
```

**แก้:**
```python
# ✅ ต้องเรียก SlipOK ก่อน:
slip_data = {
    "user_id": user_id,
    "status": "PENDING",            # ← รอตรวจก่อน
    "image_url": uploaded_url,
    "amount_detected": None,        # ← SlipOK เป็นคนบอกจำนวนเงิน ไม่ใช่ Client
    "bank_ref": None,
    "verification_method": "AUTO_API",
}

# เรียก SlipOK API
result = verify_with_slipok(qr_code_data)

# ตรวจ duplicate
if result["isDuplicate"]:
    slip_ref.update({"status": "DUPLICATE"})
    raise HTTPException(409, "สลิปนี้เคยใช้แล้ว")

# ตรวจผู้รับ
if result["receiver"] != "Big Eye":
    slip_ref.update({"status": "REJECTED", "reject_reason": "ผู้รับไม่ถูกต้อง"})
    raise HTTPException(400, "สลิปนี้ไม่ได้โอนเข้าบัญชี Big Eye")

# ผ่านทุกอย่าง → ใช้จำนวนเงินจาก SlipOK
verified_amount = result["amount"]  # ← จาก SlipOK ไม่ใช่จาก Client!
slip_ref.update({
    "status": "VERIFIED",
    "amount_detected": verified_amount,
    "bank_ref": result["transRef"],
})
```

---

## 🔴 C-02: Client กำหนดจำนวนเงิน Top-Up เอง

**ไฟล์:** `credit.py` บรรทัด ~120

```python
# ❌ เชื่อ amount จาก Client โดยตรง
"amount_detected": req.amount,   # ← Client ส่งมาเท่าไรก็ได้!
```

**วิธีโกง:**
```
โอนจริง 100 บาท → แต่ส่ง {"amount": 10000}
→ ได้เครดิตเสมือนโอน 10,000 บาท
```

**แก้:** จำนวนเงินต้องมาจาก SlipOK เท่านั้น ห้ามเชื่อ Client

---

## 🔴 C-03: ไม่มี Duplicate Check เลย

**ไฟล์:** `credit.py`

```python
# ❌ bank_ref เป็น None เสมอ → ไม่มีทางเช็คซ้ำ
"bank_ref": None,
```

**วิธีโกง:**
```
โอนจริง 1 ครั้ง 500 บาท
→ ส่งสลิปเดิม 100 ครั้ง
→ ได้ 100 × 2,000 = 200,000 เครดิต (ควรได้แค่ 2,000)
```

**แก้:** ต้องเก็บ bank_ref จาก SlipOK + เช็คซ้ำใน Firestore ก่อนเติม

---

## 🔴 C-04: JWT Secret + AES Key เป็นค่า Default

**ไฟล์:** `config.py`

```python
JWT_SECRET: str = "dev-secret-key-change-in-production-32chars"
AES_KEY: str = "0000000000000000000000000000000000000000000000000000000000000000"
```

**ผลกระทบ:**
- JWT Secret รู้ → ปลอม token เป็นใครก็ได้
- AES Key รู้ → ถอดรหัส prompt ได้ (prompt คือทรัพย์สินทางปัญญา)

**แก้:** เพิ่มใน `main.py`:
```python
if settings.ENVIRONMENT == "production":
    if "dev-secret" in settings.JWT_SECRET:
        raise RuntimeError("CRITICAL: Change JWT_SECRET!")
    if settings.AES_KEY == "0" * 64:
        raise RuntimeError("CRITICAL: Change AES_KEY!")
```

---

## 🔴 C-05: Admin Password เป็น "admin"

**ไฟล์:** `admin/utils/auth.py`

```python
admin_password = os.getenv("ADMIN_PASSWORD", "admin")
```

**ผลกระทบ:** ใครก็เข้า Admin Dashboard ได้ → ปรับเครดิต, อนุมัติสลิป, เปลี่ยน config

---

# 🟠 สูง — แก้ก่อน Go-Live

---

## 🟠 H-01: Job.py — field ชื่อ `client_info` ไม่ตรง SCHEMA.md

**ไฟล์:** `job.py` บรรทัด ~133

```python
# ❌ ใช้ "client_info" แทน "metadata"
"client_info": {
    "app_version": req.version,
    "model_used": req.model,
    "hardware_id": user.get("hardware_id", ""),
},
```

**SCHEMA.md กำหนด:**
```python
# ✅ ต้องใช้ "metadata"
"metadata": {
    "app_version": req.version,
    "model_used": req.model,
},
```

**ผลกระทบ:** Admin Dashboard ดึงข้อมูลจาก `metadata` ไม่เจอ → แสดง "—"

---

## 🟠 H-02: Job.py — Finalize ไม่ Lock ด้วย Transaction

**ไฟล์:** `job.py` บรรทัด ~188-230

Reserve ใช้ Firestore Transaction (ดี ✅) แต่ Finalize ใช้ `.update()` ธรรมดา:

```python
# ❌ Race condition: 2 requests พร้อมกัน → refund 2 ครั้ง
users_ref().document(user_id).update({
    "credits": firestore.Increment(refund),
})
```

**วิธีโกง:**
```
ส่ง POST /job/finalize พร้อมกัน 2 ครั้ง (race condition)
→ Request 1: refund 6 cr ✅
→ Request 2: refund 6 cr ✅ (ซ้ำ!)
→ ได้ refund 12 cr แทน 6 cr
```

**ถึงแม้มีเช็ค status COMPLETED แล้ว** แต่ 2 requests อาจเข้ามาพร้อมกันก่อนที่จะ update status

**แก้:** ใช้ Firestore Transaction เหมือน reserve:
```python
@firestore.transactional
def finalize_transaction(transaction):
    job_snap = job_ref.get(transaction=transaction)
    job_data = job_snap.to_dict()
    if job_data.get("status") in ("COMPLETED", "REFUNDED"):
        return None  # Already finalized
    
    transaction.update(job_ref, {"status": "COMPLETED", ...})
    transaction.update(user_ref, {"credits": firestore.Increment(refund)})
    return refund
```

---

## 🟠 H-03: Auth.py — ไม่มี Rate Limit สำหรับ Login

**ไฟล์:** `auth.py`

ไม่มี rate limiting → brute force ได้ไม่จำกัด

**แก้:** เพิ่ม slowapi:
```python
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest):
```

---

## 🟠 H-04: Auth.py — เช็คแค่ "banned" ไม่เช็ค "suspended"

**ไฟล์:** `auth.py` บรรทัด ~90

```python
# ❌ เช็คแค่ "banned"
if user.get("status") == "banned":
    raise HTTPException(status_code=403, detail="Account suspended")
```

**ปัญหา:** Admin ระงับบัญชี → status = "suspended" → user ยังล็อกอินได้!

**แก้:**
```python
if user.get("status") in ("banned", "suspended"):
    raise HTTPException(status_code=403, detail="Account suspended")
```

**เช็คเดียวกันใน `dependencies.py`:**
```python
# ❌ ปัจจุบัน
if user.get("status") == "banned":

# ✅ แก้เป็น
if user.get("status") in ("banned", "suspended"):
```

---

## 🟠 H-05: Auth.py — ไม่ validate input

**ไฟล์:** `auth.py`

ไม่มีการ validate:
- Password ว่าง → ผ่าน
- Email format ไม่ถูก → ผ่าน (แค่ lowercase)
- Hardware ID ว่าง → ผ่าน (สร้าง account ไม่ผูกเครื่อง)
- full_name ยาว 10,000 ตัว → ผ่าน

**แก้ใน Pydantic model:**
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=9, max_length=15)
    hardware_id: str = Field(min_length=16, max_length=128)
    os_type: str = ""
```

---

## 🟠 H-06: Job.py — ไม่ validate mode

**ไฟล์:** `job.py`

Client ส่ง mode อะไรก็ได้:
```python
# ❌ ไม่มี validation
req.mode  # อาจเป็น "FreeMode" → rate = istock rate (default)
```

**แก้:**
```python
class ReserveJobRequest(BaseModel):
    mode: Literal["iStock", "Adobe", "Shutterstock"]
    file_count: int = Field(ge=1, le=500)
```

---

## 🟠 H-07: CORS เปิด * ทุก Origin

**ไฟล์:** `main.py`

```python
allow_origins=["*"]  # ← ใครก็เรียก API ได้
```

---

## 🟠 H-08: System.py — Cleanup/Report ไม่มี Auth

**ไฟล์:** `system.py`

```python
# ❌ ไม่มี authentication → ใครก็เรียกได้
@router.post("/cleanup-expired-jobs")
async def cleanup_expired_jobs():

@router.post("/generate-daily-report")
async def generate_daily_report():
```

**วิธีโกง:**
```
POST /api/v1/system/cleanup-expired-jobs
→ trigger job expiry + refund โดยไม่ต้อง login
```

**แก้:** เพิ่ม API key check หรือ Cloud Scheduler header check:
```python
async def verify_scheduler_or_admin(request: Request):
    """Allow only Cloud Scheduler or admin."""
    # Cloud Scheduler sends X-CloudScheduler header
    if request.headers.get("X-CloudScheduler") == "true":
        return True
    # Or check admin token
    # ...
    raise HTTPException(403, "Not authorized")
```

---

# 🟡 กลาง — ควรแก้

---

## 🟡 M-01: Job.py — prompts key ไม่ตรง SCHEMA.md

**ไฟล์:** `job.py` บรรทัด ~160

```python
# ❌ ใช้ key สั้น
prompts.get("istock", "")
prompts.get("single", "")
prompts.get("hybrid", "")
```

**SCHEMA.md กำหนด:**
```python
# ✅ ต้องมี prefix
prompts.get("prompt_istock", "")
prompts.get("prompt_single", "")
prompts.get("prompt_hybrid", "")
```

**หมายเหตุ:** ต้องตัดสินใจว่าจะใช้ key แบบไหน แล้วทำให้ Backend + Admin Dashboard + SCHEMA.md ตรงกันทั้งหมด

---

## 🟡 M-02: Credit.py — History ไม่มี limit ที่ Firestore

```python
# ❌ ดึงทุก transaction ก่อน แล้ว sort ใน Python
docs = list(
    transactions_ref()
    .where("user_id", "==", user_id)
    .stream()  # ← ดึงทั้งหมด!
)
docs = docs[:limit]  # ← ตัดทีหลัง
```

ถ้า user มี 10,000 transactions → ดึง 10,000 docs → ช้ามาก

**แก้:** เพิ่ม `.limit(limit)` ที่ Firestore query

---

## 🟡 M-03: Job.py — dictionary ส่งเป็น string ไม่ใช่ URL

```python
# ❌ ส่ง dictionary content ทั้งก้อน
dictionary = sys_config.get("dictionary", "")
```

**SCHEMA.md กำหนด:**
```
dictionary_url: string  ← URL ให้ Client โหลดเอง
dictionary_hash: string ← hash สำหรับ cache
```

ถ้า dictionary ใหญ่ 1MB → ทุก reserve ส่ง 1MB → ช้าโดยไม่จำเป็น

---

## 🟡 M-04: Finalize — refund ใช้ Increment แต่ไม่ได้ balance จริง

```python
users_ref().document(user_id).update({
    "credits": firestore.Increment(refund),
})
# แล้วอ่าน balance ใหม่
user_doc = users_ref().document(user_id).get()
new_balance = user_doc.to_dict().get("credits", 0)
```

Race condition: ระหว่าง Increment กับ .get() อาจมี transaction อื่นเข้ามา

---

## 🟡 M-05: Daily Report — topup baht อ่านจาก metadata

```python
# ❌ อ่านจาก metadata.baht_amount ซึ่งอาจยังไม่ได้ set
total_topup_baht = sum(
    t.to_dict().get("metadata", {}).get("baht_amount", 0) 
    for t in topups
)
```

จาก Bug Report ก่อนหน้า: Transaction ที่สร้างจาก 3_Slips.py ใช้ `amount_thb` ไม่ใช่ `metadata.baht_amount` → ค่าเป็น 0 เสมอ

---

## 🟡 M-06: check-update ไม่ต้องใช้ Auth

```python
# ✅ ถูกต้องที่ไม่ต้อง auth (เพราะต้องเช็คก่อน login)
# แต่ ❌ ต้องมี rate limit ป้องกัน DDoS
@router.post("/check-update")
async def check_update(req: CheckUpdateRequest):
```

---

## 🟡 M-07: openapi.json ยังเปิดอยู่ใน production

```python
# ❌ ปิดแค่ /docs แต่ยังเข้า /openapi.json ได้
docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
# ต้องเพิ่ม:
openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
```

---

# 🔵 ต่ำ — ปรับปรุง

---

## 🔵 L-01: Job reserve ไม่ log hardware_id ใน audit

ถ้า user ปลอม hardware_id → ไม่มีทางติดตาม

## 🔵 L-02: Admin promo endpoints ไม่มี audit log

สร้าง/แก้/ลบ promo ไม่บันทึก audit → ไม่รู้ว่าใครเปลี่ยนอะไร

## 🔵 L-03: Error messages บอกข้อมูลเยอะเกิน

```python
detail=f"Cannot activate promo with status '{data.get('status')}'"
# → บอก status จริงให้แฮคเกอร์
```

---

# ลำดับการแก้ (Priority Order)

```
┌─────────────────────────────────────────────────────────┐
│ อันดับ 1: แก้ C-01, C-02, C-03 (TopUp โกงได้)          │
│ → ต่อ SlipOK API + Duplicate Check + ห้ามเชื่อ Client  │
│                                                         │
│ อันดับ 2: แก้ C-04, C-05 (Secrets + Admin Password)    │
│ → เปลี่ยน JWT Secret, AES Key, Admin Password          │
│                                                         │
│ อันดับ 3: แก้ H-02 (Double Finalize)                   │
│ → ใช้ Firestore Transaction ใน finalize                 │
│                                                         │
│ อันดับ 4: แก้ H-03, H-04, H-05, H-06 (Auth + Input)   │
│ → Rate limit, เช็ค suspended, validate input            │
│                                                         │
│ อันดับ 5: แก้ H-07, H-08 (CORS + System Auth)         │
│ → จำกัด CORS, ป้องกัน system endpoints                  │
│                                                         │
│ อันดับ 6: แก้ M-01 ถึง M-07 + Field name mismatches   │
│ → ใช้ SCHEMA.md เป็นหลัก                                │
└─────────────────────────────────────────────────────────┘
```

---

# Prompt สั่ง AI IDE ทีละขั้น

## Prompt 1 (สำคัญที่สุด):
```
แก้ server/app/routers/credit.py:
1. ลบ auto-approve ออก — ห้ามตั้ง status = "VERIFIED" ทันที
2. ต่อ SlipOK API (POST /api/verify-slip/qr-code/info)
   - ส่ง QR code data ไป SlipOK
   - ใช้ amount จาก SlipOK response ไม่ใช่จาก Client
   - เช็ค isDuplicate จาก SlipOK
3. เพิ่ม Duplicate Check เอง
   - เช็ค bank_ref ซ้ำใน Firestore slips collection
4. เช็ค receiver ว่าโอนเข้า "Big Eye" จริง
5. เก็บ bank_ref จาก SlipOK ลง Firestore

อ้างอิง: SCHEMA.md (slips collection) + SKILL.md
```

## Prompt 2:
```
แก้ server/app/config.py + main.py:
1. เพิ่ม production check — raise error ถ้า JWT_SECRET หรือ AES_KEY เป็น default
2. แก้ admin/utils/auth.py — ถ้าไม่ตั้ง ADMIN_PASSWORD ห้ามเข้า dashboard
```

## Prompt 3:
```
แก้ server/app/routers/job.py:
1. finalize ต้องใช้ Firestore Transaction (เหมือน reserve)
   ป้องกัน double refund race condition
2. เปลี่ยน "client_info" เป็น "metadata" ตาม SCHEMA.md
3. เพิ่ม input validation: mode ต้องเป็น Literal["iStock", "Adobe", "Shutterstock"]
```

## Prompt 4:
```
แก้ server/app/routers/auth.py + dependencies.py:
1. เช็ค "suspended" ด้วย ไม่ใช่แค่ "banned"
2. เพิ่ม input validation: email EmailStr, password min 8, hardware_id min 16
3. เพิ่ม rate limiting: login 5/min, register 3/min
```

## Prompt 5:
```
แก้ server/app/main.py:
1. CORS: production ใช้ origins จำกัด, development ใช้ *
2. ปิด openapi_url ใน production
3. เพิ่ม rate limiting middleware (slowapi)
```

## Prompt 6:
```
แก้ server/app/routers/system.py:
1. cleanup-expired-jobs + generate-daily-report ต้องมี auth
   ใช้ Cloud Scheduler header check หรือ admin token
2. expire-promotions ต้องมี auth เช่นกัน
```
