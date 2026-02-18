# BigEye Pro — Firestore Schema Reference
### ⚠️ AI IDE: อ่านไฟล์นี้ก่อนเขียนโค้ดที่เกี่ยวกับ Firestore ทุกครั้ง
### ห้ามเดาชื่อ field เอง — ใช้เฉพาะชื่อที่อยู่ในไฟล์นี้เท่านั้น

---

## กฎ

1. ทุก field ใช้ **snake_case** — ห้าม camelCase
2. ชื่อ field ต้อง **ตรงตัว** — `hardware_id` ไม่ใช่ `device_id`
3. Nested field ใช้ **dot notation** — `credit_rates.istock_photo`
4. Enum values เป็น **UPPERCASE** — `"COMPLETED"` ไม่ใช่ `"completed"`

---

## users (doc ID = auto)

| Field | Type | Note |
|:--|:--|:--|
| `email` | string | unique, indexed |
| `password_hash` | string | bcrypt |
| `full_name` | string | ❌ ไม่ใช่ `name`, `username` |
| `phone` | string | ❌ ไม่ใช่ `phone_number` |
| `hardware_id` | string | ❌ ไม่ใช่ `device_id` |
| `tier` | string | `"standard"` / `"premium"` |
| `credits` | number | ❌ ไม่ใช่ `credit`, `balance` |
| `status` | string | `"active"` / `"suspended"` / `"banned"` |
| `created_at` | timestamp | ❌ ไม่ใช่ `createdAt` |
| `last_login` | timestamp | |
| `last_active` | timestamp | |
| `total_topup_baht` | number | ❌ ไม่ใช่ `total_topup` |
| `total_credits_used` | number | |
| `app_version` | string | |
| `metadata.os` | string | |
| `metadata.registration_ip` | string | |
| `metadata.notes` | string | |

---

## jobs (doc ID = job_token)

| Field | Type | Note |
|:--|:--|:--|
| `job_token` | string | UUID v4 |
| `user_id` | string | ❌ ไม่ใช่ `uid` |
| `status` | string | `"RESERVED"` / `"PROCESSING"` / `"COMPLETED"` / `"REFUNDED"` / `"EXPIRED"` / `"FAILED"` |
| `mode` | string | `"iStock"` / `"Adobe"` / `"Shutterstock"` (ตัวพิมพ์ต้องตรง) |
| `keyword_style` | string/null | `"Hybrid"` / `"Single Words"` / `null` |
| `file_count` | number | |
| `photo_count` | number | |
| `video_count` | number | |
| `photo_rate` | number | อัตราเครดิต/รูป |
| `video_rate` | number | อัตราเครดิต/วิดีโอ |
| `credit_rate` | number | backward compat (เท่ากับ photo_rate) |
| `reserved_credits` | number | ❌ ไม่ใช่ `total_cost` |
| `actual_usage` | number | ❌ ไม่ใช่ `used_credits` |
| `refund_amount` | number | ❌ ไม่ใช่ `refunded` |
| `success_count` | number | ❌ ไม่ใช่ `successful`, `completed` |
| `failed_count` | number | ❌ ไม่ใช่ `failed`, `errors` |
| `created_at` | timestamp | |
| `completed_at` | timestamp/null | |
| `expires_at` | timestamp | |
| `metadata.app_version` | string | ❌ ไม่ใช่ `client_info.app_version` |
| `metadata.model_used` | string | ❌ ไม่ใช่ `model`, `client_info.model_used` |
| `metadata.hardware_id` | string | |

---

## transactions (doc ID = auto)

| Field | Type | Note |
|:--|:--|:--|
| `user_id` | string | |
| `type` | string | `"TOPUP"` / `"RESERVE"` / `"REFUND"` / `"ADJUSTMENT"` / `"BONUS"` |
| `amount` | number | + หรือ - |
| `balance_after` | number | |
| `reference_id` | string/null | ❌ ไม่ใช่ `slip_id`, `job_id` |
| `description` | string | |
| `created_at` | timestamp | |
| `metadata.baht_amount` | number/null | เฉพาะ TOPUP ❌ ไม่ใช่ `amount_thb` |
| `metadata.slip_ref` | string/null | |
| `metadata.base_credits` | number/null | เฉพาะ TOPUP |
| `metadata.bonus_credits` | number/null | เฉพาะ TOPUP (มีโปร) |
| `metadata.promo_id` | string/null | เฉพาะ TOPUP (มีโปร) |

---

## slips (doc ID = auto)

| Field | Type | Note |
|:--|:--|:--|
| `user_id` | string | ❌ ไม่ใช่ `uid` |
| `status` | string | `"PENDING"` / `"VERIFIED"` / `"REJECTED"` / `"DUPLICATE"` |
| `image_url` | string | ❌ ไม่ใช่ `slip_base64`, `slip_image` |
| `amount_detected` | number/null | ❌ ไม่ใช่ `amount` |
| `amount_credited` | number/null | ❌ ไม่ใช่ `credit_amount` |
| `bank_ref` | string/null | ❌ ไม่ใช่ `reference` |
| `verification_method` | string | `"AUTO_API"` (Slip2Go) / `"AUTO_DEV"` (dev only) / `"MANUAL"` |
| `verification_result.provider` | string | `"Slip2Go"` |
| `verification_result.raw_response` | map | Slip2Go full response |
| `verification_result.confidence` | number | `1.0` for Slip2Go |
| `reject_reason` | string/null | |
| `created_at` | timestamp | |
| `verified_at` | timestamp/null | |
| `metadata.sender_name` | string/null | จาก Slip2Go `sender.displayName` |
| `metadata.receiver_account` | string/null | จาก Slip2Go `receiver.account.value` |

---

## system_config/app_settings (SINGLE document)

| Field | Type | Note |
|:--|:--|:--|
| `prompts.istock` | string | ❌ ไม่ใช่ `prompts.prompt_istock` |
| `prompts.hybrid` | string | ❌ ไม่ใช่ `prompts.prompt_hybrid` |
| `prompts.single` | string | ❌ ไม่ใช่ `prompts.prompt_single` |
| `dictionary` | string | เนื้อหา dictionary ทั้งหมด ❌ ไม่ใช่ `dictionary_url` |
| `dictionary_word_count` | number | |
| `dictionary_version` | string | |
| `dictionary_updated_at` | timestamp | |
| `blacklist` | array\<string\> | |
| `credit_rates.istock_photo` | number | ❌ ไม่ใช่ `iStock_photo` |
| `credit_rates.istock_video` | number | |
| `credit_rates.adobe_photo` | number | |
| `credit_rates.adobe_video` | number | |
| `credit_rates.shutterstock_photo` | number | |
| `credit_rates.shutterstock_video` | number | |
| `exchange_rate` | number | |
| `app_latest_version` | string | ❌ ไม่ใช่ `latest_version` |
| `app_download_url` | string | |
| `app_update_notes` | string | |
| `force_update_below` | string/null | |
| `maintenance_mode` | boolean | |
| `maintenance_message` | string | |
| `context_cache_threshold` | number | |
| `max_concurrent_images` | number | |
| `max_concurrent_videos` | number | |
| `prompts_version` | string | |
| `prompts_updated_at` | timestamp | |
| `updated_at` | timestamp | |

---

## audit_logs (doc ID = auto)

| Field | Type | Note |
|:--|:--|:--|
| `event_type` | string | ❌ ไม่ใช่ `event`, `action`, `type` |
| `severity` | string | `"INFO"` / `"WARNING"` / `"ERROR"` / `"CRITICAL"` |
| `user_id` | string | |
| `details` | map | |
| `created_at` | timestamp | ❌ ไม่ใช่ `timestamp` |

**event_type values (ที่ Server เขียนจริง):**
`USER_REGISTER`, `LOGIN_FAILED_DEVICE_MISMATCH`,
`LOGIN_FAILED_WRONG_PASSWORD`, `TOPUP_SUCCESS`,
`JOB_RESERVED`, `JOB_COMPLETED`, `JOB_EXPIRED_AUTO_REFUND`

---

## promotions (doc ID = auto)

| Field | Type | Note |
|:--|:--|:--|
| `name` | string | |
| `code` | string/null | |
| `type` | string | `"RATE_BOOST"` / `"TIERED_BONUS"` / `"FLAT_BONUS"` / `"WELCOME_BONUS"` / `"FIRST_TOPUP"` / `"USAGE_REWARD"` |
| `status` | string | `"DRAFT"` / `"ACTIVE"` / `"PAUSED"` / `"EXPIRED"` / `"CANCELLED"` |
| `priority` | number | |
| `conditions.start_date` | timestamp | |
| `conditions.end_date` | timestamp | |
| `conditions.min_topup_baht` | number/null | |
| `conditions.max_topup_baht` | number/null | |
| `conditions.max_redemptions` | number/null | |
| `conditions.max_per_user` | number/null | |
| `conditions.new_users_only` | boolean | |
| `conditions.first_topup_only` | boolean | |
| `conditions.require_code` | boolean | |
| `reward.type` | string | `"BONUS_CREDITS"` / `"RATE_OVERRIDE"` / `"PERCENTAGE_BONUS"` / `"TIERED_BONUS"` |
| `reward.bonus_credits` | number/null | |
| `reward.override_rate` | number/null | |
| `reward.bonus_percentage` | number/null | |
| `reward.tiers` | array/null | `[{min_baht, max_baht, credits}]` |
| `display.banner_text` | string | |
| `display.banner_color` | string | |
| `display.show_in_client` | boolean | |
| `display.show_in_topup` | boolean | |
| `stats.total_redemptions` | number | |
| `stats.total_bonus_credits` | number | |
| `stats.total_baht_collected` | number | |
| `stats.unique_users` | number | |
| `created_at` | timestamp | |
| `created_by` | string | |
| `updated_at` | timestamp | |

---

---

# PART 2: API Response Reference (สำหรับ Client)

### ⚠️ Client ต้องใช้ key ตามนี้เท่านั้นเมื่ออ่าน response จาก Backend API

---

## POST /api/v1/auth/register → Response

```json
{
    "token": "eyJ...",
    "user_id": "abc123",
    "full_name": "Test User",
    "email": "test@test.com",
    "credits": 0
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `full_name` | `name`, `username`, `fullName` |
| `credits` | `credit`, `balance` |

---

## POST /api/v1/auth/login → Response

```json
{
    "token": "eyJ...",
    "user_id": "abc123",
    "full_name": "Test User",
    "email": "test@test.com",
    "credits": 500
}
```

---

## GET /api/v1/credit/balance → Response

```json
{
    "credits": 500,
    "credit_rates": {
        "istock_photo": 3,
        "istock_video": 3,
        "adobe_photo": 2,
        "adobe_video": 2,
        "shutterstock_photo": 2,
        "shutterstock_video": 2
    },
    "exchange_rate": 4,
    "active_promos": [
        {
            "name": "โปรปีใหม่",
            "type": "TIERED_BONUS",
            "display": {
                "banner_text": "🎄 เติม 500+ รับ 2,200 cr!",
                "banner_color": "#FF4560",
                "show_in_client": true,
                "show_in_topup": true
            },
            "conditions": {
                "min_topup_baht": 100,
                "end_date": "2026-02-28T23:59:59Z"
            },
            "reward": {
                "type": "TIERED_BONUS",
                "tiers": [
                    {"min_baht": 100, "max_baht": 299, "credits": 400},
                    {"min_baht": 300, "max_baht": 499, "credits": 1300},
                    {"min_baht": 500, "max_baht": null, "credits": 2200}
                ]
            }
        }
    ]
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `credits` | `credit`, `balance`, `credit_balance` |
| `credit_rates.istock_photo` | `rates.iStock`, `rates.istock`, `istock_rate` |
| `exchange_rate` | `exchangeRate`, `rate` |
| `active_promos` | `promotions`, `promos`, `promo_list` |

---

## POST /api/v1/credit/topup → Request

```json
{
    "slip": "data:image/jpeg;base64,...",
    "amount": 500,
    "promo_code": "NEWYEAR2027"
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `slip` | `slip_image`, `image`, `slip_base64` |
| `amount` | `amount_thb`, `baht` |
| `promo_code` | `promoCode`, `code` |

---

## GET /api/v1/credit/history → Response

```json
{
    "transactions": [
        {
            "date": "2026-02-08 17:00",
            "description": "Top-up 500 THB → 2000 credits",
            "amount": 2000,
            "type": "TOPUP"
        }
    ],
    "balance": 2500
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `transactions` | `history`, `records`, `items` |
| `date` | `created_at`, `timestamp` |
| `amount` | `credits`, `value` |
| `balance` | `remaining`, `credits_remaining` |

---

## POST /api/v1/job/reserve → Request

```json
{
    "file_count": 7,
    "photo_count": 5,
    "video_count": 2,
    "mode": "iStock",
    "keyword_style": null,
    "model": "gemini-2.5-flash",
    "version": "2.0.0"
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `file_count` | `fileCount`, `files`, `total_files` |
| `mode` | `platform`, `platform_name` |
| `keyword_style` | `keywordStyle`, `style` |

---

## POST /api/v1/job/reserve → Response

```json
{
    "job_token": "550e8400-e29b-41d4-a716-446655440000",
    "reserved_credits": 21,
    "photo_rate": 3,
    "video_rate": 3,
    "config": "encrypted_hex_string...",
    "dictionary": "keyword1\nkeyword2\n...",
    "blacklist": ["nike", "adidas", "iphone"],
    "concurrency": {"image": 5, "video": 2},
    "cache_threshold": 20
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `job_token` | `token`, `jobToken`, `job_id` |
| `reserved_credits` | `cost`, `total_cost`, `credits_reserved` |
| `config` | `config.prompt`, `prompt` (config เป็น encrypted string ไม่ใช่ object) |
| `dictionary` | `dictionary_url`, `dict_url` |
| `blacklist` | `blocked_words`, `banned_words` |
| `concurrency` | `max_concurrent_images` (ใช้ `concurrency.image` แทน) |

---

## POST /api/v1/job/finalize → Request

```json
{
    "job_token": "550e8400-...",
    "success": 5,
    "failed": 2,
    "photos": 4,
    "videos": 3
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `job_token` | `token`, `job_id` |
| `success` | `success_count`, `successful`, `completed`, `done` |
| `failed` | `failed_count`, `errors`, `error_count` |
| `photos` | `photo_count` |
| `videos` | `video_count` |

---

## POST /api/v1/job/finalize → Response

```json
{
    "refunded": 6,
    "balance": 485
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `refunded` | `refund_amount`, `refund` |
| `balance` | `credits_remaining`, `remaining` |

---

## POST /api/v1/system/check-update → Response

```json
{
    "update_available": true,
    "version": "2.0.1",
    "force": false,
    "download_url": "https://...",
    "notes": "Bug fixes and improvements",
    "maintenance": false,
    "maintenance_message": ""
}
```

| Key | ❌ ห้ามใช้ |
|:--|:--|
| `version` | `latest_version`, `new_version`, `app_version` |
| `force` | `force_update`, `forceUpdate`, `is_force` |
| `download_url` | `downloadUrl`, `url` |
| `notes` | `release_notes`, `changelog` |

---

## Error Response (ทุก endpoint)

```json
{
    "detail": "Insufficient credits"
}
```

**HTTP Status Codes:**
| Code | ความหมาย | Client ต้องจัดการ |
|:--|:--|:--|
| 401 | Token หมดอายุ / ไม่ถูกต้อง | → กลับหน้า Login |
| 402 | เครดิตไม่พอ | → แสดง InsufficientDialog |
| 403 | บัญชีถูกระงับ | → แสดง error + Logout |
| 409 | ข้อมูลซ้ำ (email/slip) | → แสดง error message |
| 426 | ต้องอัพเดทแอป | → แสดง UpdateDialog (บังคับ) |
| 429 | Rate limit | → รอ แล้วลองใหม่ |
| 503 | Maintenance mode | → แสดง MaintenanceDialog |

---

## promo_redemptions (doc ID = auto)

| Field | Type | Note |
|:--|:--|:--|
| `promo_id` | string | |
| `user_id` | string | |
| `topup_baht` | number | |
| `base_credits` | number | |
| `bonus_credits` | number | |
| `total_credits` | number | |
| `promo_name` | string | |
| `slip_id` | string/null | |
| `created_at` | timestamp | |
