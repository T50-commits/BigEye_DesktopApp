# BigEye Pro — Promotion & Campaign System Specification
### Dynamic Promotions via Admin Dashboard
### Date: February 2026

---

## 1. Overview

ระบบโปรโมชั่นที่ Admin สร้าง/จัดการผ่าน Dashboard ได้ทั้งหมด ไม่ต้องแก้โค้ด รองรับหลายโปรพร้อมกัน มีเงื่อนไขซับซ้อนได้ เช่น เติมขั้นต่ำ, จำกัดเวลา, จำกัดจำนวนคน, โบนัสแบบขั้นบันได

**ตัวอย่างโปรโมชั่นที่รองรับ:**
- 🎄 "เติม 500 บาทขึ้นไป รับ 2,200 cr (ปกติ 2,000)" — ช่วงปีใหม่
- 🔥 "เติมเท่าไรก็ได้ รับ x5 (ปกติ x4)" — flash sale 24 ชม.
- 📦 "เติม 100 ได้ 400, เติม 300 ได้ 1,300, เติม 500 ได้ 2,200" — ขั้นบันได
- 🆕 "สมัครใหม่รับ 50 cr ฟรี" — welcome bonus
- 🎯 "เติมครั้งแรกรับ x6" — first purchase bonus

---

## 2. Promotion Types

| Type | ชื่อ | ตัวอย่าง | เงื่อนไข |
|:--|:--|:--|:--|
| `RATE_BOOST` | อัตราแลกเปลี่ยนพิเศษ | 1 THB = 5 cr (ปกติ 4) | ช่วงเวลา, ขั้นต่ำ |
| `TIERED_BONUS` | โบนัสขั้นบันได | เติม 100→400, 300→1,300, 500→2,200 | ยอดเติม |
| `FLAT_BONUS` | โบนัสเครดิตคงที่ | เติม 500+ รับโบนัส 200 cr | ขั้นต่ำ |
| `WELCOME_BONUS` | โบนัสสมัครใหม่ | สมัครรับ 50 cr ฟรี | user ใหม่เท่านั้น |
| `FIRST_TOPUP` | โบนัสเติมครั้งแรก | เติมครั้งแรก x6 | เติมครั้งแรกเท่านั้น |
| `USAGE_REWARD` | รางวัลตามการใช้งาน | ทำครบ 100 ไฟล์ รับ 50 cr | จำนวน job สำเร็จ |

---

## 3. Firestore Schema

### 3.1 Collection: `promotions`

```
promotions/{promo_id}
├── name: string ("New Year 2027 Bonus")
├── code: string | null ("NEWYEAR2027") ← optional promo code
├── type: string ("RATE_BOOST" | "TIERED_BONUS" | "FLAT_BONUS" | 
│                  "WELCOME_BONUS" | "FIRST_TOPUP" | "USAGE_REWARD")
├── status: string ("DRAFT" | "ACTIVE" | "PAUSED" | "EXPIRED" | "CANCELLED")
├── priority: number [default: 0] ← higher = applied first when multiple match
│
├── conditions: map
│   ├── start_date: timestamp              ← โปรเริ่มเมื่อไร
│   ├── end_date: timestamp                ← โปรหมดเมื่อไร
│   ├── min_topup_baht: number | null      ← เติมขั้นต่ำ (null = ไม่จำกัด)
│   ├── max_topup_baht: number | null      ← เติมสูงสุดที่ใช้โปรได้
│   ├── max_redemptions: number | null     ← จำนวนครั้งทั้งหมด (null = ไม่จำกัด)
│   ├── max_per_user: number | null        ← จำนวนครั้งต่อ user (null = ไม่จำกัด)
│   ├── eligible_tiers: array | null       ← ["standard", "premium"] or null = all
│   ├── new_users_only: boolean [false]    ← เฉพาะ user ใหม่
│   ├── first_topup_only: boolean [false]  ← เฉพาะเติมครั้งแรก
│   └── require_code: boolean [false]      ← ต้องกรอก promo code
│
├── reward: map
│   ├── type: string ("BONUS_CREDITS" | "RATE_OVERRIDE" | "PERCENTAGE_BONUS")
│   │
│   │   ── BONUS_CREDITS: ให้เครดิตเพิ่มตามจำนวนคงที่
│   ├── bonus_credits: number | null       ← e.g., 200 (เติม 500 ได้ +200 cr)
│   │
│   │   ── RATE_OVERRIDE: เปลี่ยนอัตราแลกเปลี่ยนชั่วคราว
│   ├── override_rate: number | null       ← e.g., 5 (1 THB = 5 cr แทน 4)
│   │
│   │   ── PERCENTAGE_BONUS: ให้โบนัสเป็น % ของเครดิตที่ได้
│   ├── bonus_percentage: number | null    ← e.g., 10 (เพิ่ม 10%)
│   │
│   │   ── TIERED: หลายชั้น (ใช้ร่วมกับ tiers array)
│   └── tiers: array | null
│       ├── { min_baht: 100, max_baht: 299, credits: 400 }     ← เติม 100-299 ได้ 400
│       ├── { min_baht: 300, max_baht: 499, credits: 1300 }    ← เติม 300-499 ได้ 1,300
│       └── { min_baht: 500, max_baht: null, credits: 2200 }   ← เติม 500+ ได้ 2,200
│
├── display: map
│   ├── banner_text: string ("🎄 New Year Special! Top up 500 THB, get 2,200 credits!")
│   ├── banner_color: string ("#FF4560" | "#00E396" | "#FEB019")
│   ├── show_in_client: boolean [true]     ← แสดง banner ใน Desktop Client
│   └── show_in_topup: boolean [true]      ← แสดงใน TopUp Dialog
│
├── stats: map (auto-updated)
│   ├── total_redemptions: number [0]
│   ├── total_bonus_credits: number [0]    ← เครดิตโบนัสทั้งหมดที่แจกไป
│   ├── total_baht_collected: number [0]   ← เงินที่เข้ามาจากโปรนี้
│   └── unique_users: number [0]
│
├── created_at: timestamp
├── created_by: string
└── updated_at: timestamp
```

**Indexes:**
- `status` + `conditions.start_date` → หาโปรที่ active
- `status` + `conditions.end_date` → หาโปรที่หมดอายุ (scheduler)
- `code` → lookup promo code

### 3.2 Collection: `promo_redemptions` (ประวัติการใช้โปร)

```
promo_redemptions/{redemption_id}
├── promo_id: string (ref → promotions)
├── user_id: string (ref → users)
├── topup_baht: number              ← เติมเท่าไร
├── base_credits: number            ← เครดิตปกติ (ไม่มีโปร)
├── bonus_credits: number           ← เครดิตโบนัสจากโปร
├── total_credits: number           ← base + bonus
├── promo_name: string              ← snapshot ชื่อโปร
├── transaction_id: string          ← ref → transactions
├── slip_id: string | null          ← ref → slips
└── created_at: timestamp
```

**Indexes:**
- `promo_id` + `created_at` → ดูสถิติต่อโปร
- `user_id` + `promo_id` → นับจำนวนครั้งต่อ user (enforce max_per_user)

---

## 4. Promotion Engine (Backend Logic)

### 4.1 Core: find_applicable_promos()

```python
async def find_applicable_promos(
    user_id: str, 
    topup_baht: float, 
    promo_code: str | None = None
) -> list[dict]:
    """
    Find all promotions that apply to this top-up.
    Returns list sorted by priority (highest first).
    Only the BEST single promo is applied (no stacking).
    """
    now = datetime.utcnow()
    
    # 1. Query active promos
    promos = db.collection("promotions") \
        .where("status", "==", "ACTIVE") \
        .where("conditions.start_date", "<=", now) \
        .stream()
    
    applicable = []
    user = get_user(user_id)
    
    for promo in promos:
        p = promo.to_dict()
        cond = p["conditions"]
        
        # Check end date
        if cond["end_date"] and now > cond["end_date"]:
            continue
        
        # Check promo code requirement
        if cond.get("require_code") and p.get("code") != promo_code:
            continue
        
        # Check min/max top-up amount
        if cond.get("min_topup_baht") and topup_baht < cond["min_topup_baht"]:
            continue
        if cond.get("max_topup_baht") and topup_baht > cond["max_topup_baht"]:
            continue
        
        # Check max total redemptions
        if cond.get("max_redemptions"):
            if p["stats"]["total_redemptions"] >= cond["max_redemptions"]:
                continue
        
        # Check max per user
        if cond.get("max_per_user"):
            user_count = count_user_redemptions(user_id, promo.id)
            if user_count >= cond["max_per_user"]:
                continue
        
        # Check user eligibility
        if cond.get("new_users_only") and not is_new_user(user):
            continue
        if cond.get("first_topup_only") and has_previous_topup(user_id):
            continue
        if cond.get("eligible_tiers") and user["tier"] not in cond["eligible_tiers"]:
            continue
        
        # Calculate bonus
        bonus = calculate_bonus(p, topup_baht)
        applicable.append({
            "promo_id": promo.id,
            "name": p["name"],
            "bonus_credits": bonus,
            "display": p["display"],
            "priority": p.get("priority", 0),
        })
    
    # Sort by priority, then by bonus (highest first)
    applicable.sort(key=lambda x: (-x["priority"], -x["bonus_credits"]))
    return applicable


def calculate_bonus(promo: dict, topup_baht: float) -> int:
    """Calculate bonus credits for a given promo and amount."""
    reward = promo["reward"]
    base_rate = get_exchange_rate()  # e.g., 4
    base_credits = int(topup_baht * base_rate)
    
    if reward["type"] == "BONUS_CREDITS":
        return reward["bonus_credits"]
    
    elif reward["type"] == "RATE_OVERRIDE":
        new_credits = int(topup_baht * reward["override_rate"])
        return new_credits - base_credits
    
    elif reward["type"] == "PERCENTAGE_BONUS":
        return int(base_credits * reward["bonus_percentage"] / 100)
    
    elif reward["type"] == "TIERED_BONUS":
        for tier in reward["tiers"]:
            if topup_baht >= tier["min_baht"]:
                if tier.get("max_baht") is None or topup_baht <= tier["max_baht"]:
                    return tier["credits"] - base_credits
        return 0
    
    return 0
```

### 4.2 Apply Promo at Top-Up

```python
async def process_topup_with_promo(
    user_id: str, 
    topup_baht: float, 
    slip_id: str,
    promo_code: str | None = None
) -> dict:
    """Process top-up with automatic or code-based promotion."""
    
    base_rate = get_exchange_rate()
    base_credits = int(topup_baht * base_rate)
    bonus_credits = 0
    applied_promo = None
    
    # Find best promo
    promos = await find_applicable_promos(user_id, topup_baht, promo_code)
    
    if promos:
        best = promos[0]  # Highest priority
        bonus_credits = best["bonus_credits"]
        applied_promo = best
    
    total_credits = base_credits + bonus_credits
    
    # Atomic transaction
    with firestore_transaction() as txn:
        # 1. Add credits to user
        user_ref = db.collection("users").document(user_id)
        txn.update(user_ref, {"credits": Increment(total_credits)})
        
        # 2. Create transaction record
        tx_data = {
            "user_id": user_id,
            "type": "TOPUP",
            "amount": total_credits,
            "description": f"Top-up {topup_baht} THB → {total_credits} credits"
                + (f" (incl. {bonus_credits} bonus from '{applied_promo['name']}')" 
                   if applied_promo else ""),
            "metadata": {
                "baht_amount": topup_baht,
                "base_credits": base_credits,
                "bonus_credits": bonus_credits,
                "promo_id": applied_promo["promo_id"] if applied_promo else None,
            }
        }
        txn.set(db.collection("transactions").document(), tx_data)
        
        # 3. Record redemption (if promo applied)
        if applied_promo:
            txn.set(db.collection("promo_redemptions").document(), {
                "promo_id": applied_promo["promo_id"],
                "user_id": user_id,
                "topup_baht": topup_baht,
                "base_credits": base_credits,
                "bonus_credits": bonus_credits,
                "total_credits": total_credits,
                "promo_name": applied_promo["name"],
                "slip_id": slip_id,
                "created_at": SERVER_TIMESTAMP,
            })
            
            # 4. Update promo stats
            promo_ref = db.collection("promotions").document(applied_promo["promo_id"])
            txn.update(promo_ref, {
                "stats.total_redemptions": Increment(1),
                "stats.total_bonus_credits": Increment(bonus_credits),
                "stats.total_baht_collected": Increment(topup_baht),
            })
    
    # 5. LINE Notify
    notify = f"🟢 {user_id} topped up ฿{topup_baht} → {total_credits} cr"
    if applied_promo:
        notify += f" (🎁 +{bonus_credits} bonus: {applied_promo['name']})"
    send_line_notify(notify)
    
    return {
        "base_credits": base_credits,
        "bonus_credits": bonus_credits,
        "total_credits": total_credits,
        "promo_applied": applied_promo["name"] if applied_promo else None,
    }
```

### 4.3 Auto-Expire Promotions (Cloud Scheduler)

```python
# Runs every hour via Cloud Scheduler
async def expire_promotions():
    """Auto-expire promotions past end_date."""
    now = datetime.utcnow()
    expired = db.collection("promotions") \
        .where("status", "==", "ACTIVE") \
        .where("conditions.end_date", "<", now) \
        .stream()
    
    for promo in expired:
        promo.reference.update({
            "status": "EXPIRED",
            "updated_at": SERVER_TIMESTAMP,
        })
        send_line_notify(f"⏰ Promo expired: {promo.to_dict()['name']}")
```

---

## 5. Admin Dashboard UI

### 5.1 Promotions Page (NEW page)

```
┌──────────────────────────────────────────────────────────────────────┐
│  🎁 PROMOTIONS                                        [+ Create New] │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ACTIVE PROMOTIONS                                                   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 🟢 New Year 2027 Bonus                          [Edit] [Pause] │  │
│  │    Type: TIERED_BONUS                                          │  │
│  │    Period: Dec 31 – Jan 2                                      │  │
│  │    Tiers: 100→400, 300→1,300, 500→2,200                       │  │
│  │    Used: 45 times | Bonus given: 8,500 cr | Revenue: ฿12,300  │  │
│  │    ████████████░░ 45/100 redemptions                           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 🟢 First Top-Up x6                              [Edit] [Pause] │  │
│  │    Type: FIRST_TOPUP (RATE_OVERRIDE: 6)                        │  │
│  │    Period: Always active (no end date)                         │  │
│  │    Condition: First top-up only                                │  │
│  │    Used: 120 times | Bonus given: 24,000 cr                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  DRAFT / PAUSED                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ ⏸️  Valentine's Day Special (PAUSED)        [Resume] [Delete]  │  │
│  │ 📝 Songkran Flash Sale (DRAFT)             [Activate] [Edit]  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  EXPIRED                                                             │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ ⬜ Christmas 2026 (EXPIRED Dec 26)                [Clone]      │  │
│  │    Final stats: 89 uses, ฿35,000 revenue, 7,200 bonus cr      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Create / Edit Promotion

```
┌──────────────────────────────────────────────────────────────────────┐
│  CREATE PROMOTION                                                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  BASIC INFO                                                          │
│  Name: [New Year 2027 Bonus________________]                        │
│  Promo Code (optional): [NEWYEAR2027_______] □ Require code to use  │
│  Priority: [10] (higher = preferred when multiple promos match)      │
│                                                                       │
│  TYPE                                                                │
│  ○ Rate Boost (change exchange rate)                                 │
│  ○ Flat Bonus (fixed bonus credits)                                  │
│  ● Tiered Bonus (different bonus per amount)                         │
│  ○ Welcome Bonus (new users)                                         │
│  ○ First Top-Up Bonus                                                │
│  ○ Usage Reward                                                      │
│                                                                       │
│  TIERS (for Tiered Bonus)                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Min THB │ Max THB │ Total Credits │ Bonus vs Normal │ Remove  │   │
│  │ [100  ] │ [299  ] │ [400       ] │ +0 (same)       │  [✕]    │   │
│  │ [300  ] │ [499  ] │ [1300      ] │ +100 bonus      │  [✕]    │   │
│  │ [500  ] │ [—    ] │ [2200      ] │ +200 bonus      │  [✕]    │   │
│  │                               [+ Add Tier]                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  CONDITIONS                                                          │
│  Start: [2026-12-31 00:00]  End: [2027-01-02 23:59]                │
│  Min top-up: [100] THB    Max top-up: [—] THB                       │
│  Max total redemptions: [100] (leave empty = unlimited)              │
│  Max per user: [3]                                                    │
│  □ New users only    □ First top-up only                             │
│  Eligible tiers: [☑ standard] [☑ premium]                           │
│                                                                       │
│  CLIENT DISPLAY                                                      │
│  Banner text: [🎄 New Year Special! Top up 500+, get 2,200 cr!___]  │
│  Banner color: [🔴 Red] [🟢 Green] [🟡 Amber] [🔵 Blue]            │
│  ☑ Show banner in client    ☑ Show in TopUp dialog                  │
│                                                                       │
│  PREVIEW                                                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 🎄 New Year Special! Top up 500+, get 2,200 cr!             │   │
│  │                                                               │   │
│  │ If user tops up 500 THB:                                     │   │
│  │   Normal:  500 × 4 = 2,000 credits                          │   │
│  │   With promo:         2,200 credits                          │   │
│  │   Bonus:              +200 credits (10% more)                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  [Save as Draft]  [Activate Now]  [Cancel]                           │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.3 Promotion Stats

```
┌──────────────────────────────────────────────────────────────────────┐
│  📊 PROMO STATS: New Year 2027 Bonus                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                            │
│  │  45  │  │ 8,500│  │฿12.3K│  │  38  │                            │
│  │ Uses │  │Bonus │  │Revenue│  │Unique│                            │
│  │      │  │  cr  │  │      │  │Users │                            │
│  └──────┘  └──────┘  └──────┘  └──────┘                            │
│                                                                       │
│  REDEMPTION LOG                                                      │
│  Date        User          Top-up    Base    Bonus   Total           │
│  ──────────────────────────────────────────────────────────          │
│  Jan 1 14:30 john@...      500 THB   2,000   +200   2,200           │
│  Jan 1 10:15 jane@...      300 THB   1,200   +100   1,300           │
│  Dec 31 23:50 bob@...      100 THB     400     +0     400           │
│                                                                       │
│  [Export to CSV]                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Client-Side Integration

### 6.1 API Response Updates

```json
// GET /credit/balance (UPDATED — add active promos)
{
  "credits": 1200,
  "rates": { "istock_photo": 3, ... },
  "exchange_rate": 4,
  "active_promos": [
    {
      "promo_id": "newyear2027",
      "name": "New Year 2027 Bonus",
      "banner_text": "🎄 New Year Special! Top up 500+, get 2,200 cr!",
      "banner_color": "#FF4560",
      "type": "TIERED_BONUS",
      "tiers": [
        { "min_baht": 100, "credits": 400 },
        { "min_baht": 300, "credits": 1300 },
        { "min_baht": 500, "credits": 2200 }
      ],
      "ends_at": "2027-01-02T23:59:00Z"
    }
  ]
}
```

### 6.2 Client Top Bar — Promo Banner

```
ถ้ามี active promo ที่ show_in_client = true:

┌─────────────────────────────────────────────────────────────────────┐
│ 🎄 New Year Special! Top up 500+, get 2,200 cr!  [Top Up Now] [✕]  │
├─────────────────────────────────────────────────────────────────────┤
│ BIGEYE │ 💰 1,200 credits  [Top Up] [↻] [History]    Somchai [Logout] │
└─────────────────────────────────────────────────────────────────────┘

- Banner แสดงเหนือ credit bar
- สี background ตาม banner_color
- [✕] ปิด banner ได้ (ซ่อนถึง session ถัดไป)
- [Top Up Now] → เปิด TopUp Dialog
```

### 6.3 TopUp Dialog — Promo Display

```
┌────────────────────────────────────────────┐
│ 🪙 Top Up Credits                          │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │ 🎄 NEW YEAR SPECIAL (ends Jan 2)      │ │
│ │                                        │ │
│ │  Top up 100 THB → 400 credits         │ │
│ │  Top up 300 THB → 1,300 credits ★     │ │
│ │  Top up 500 THB → 2,200 credits ★★    │ │
│ │                                        │ │
│ │  ★ = includes bonus credits            │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ Bank details...                            │
│ [Drop slip here]                           │
│ Amount: [500] THB                          │
│                                            │
│ You will receive: 2,200 credits            │
│ (2,000 base + 200 bonus 🎁)               │
│                                            │
│ Promo Code: [NEWYEAR2027___] [Apply]       │
│                                            │
│ [Submit Slip]                              │
└────────────────────────────────────────────┘
```

### 6.4 Credit History — Show Bonus

```
Date         Transaction                    Amount
──────────────────────────────────────────────────
01/01 14:30  Top-up 500 THB (🎁 +200)      +2,200
07/02 14:35  iStock 50 files               -150
```

---

## 7. Backend API Endpoints

```
# Admin endpoints
POST /api/v1/admin/promo/create
  Body: { name, type, conditions, reward, display }
  Response: { promo_id, status: "DRAFT" }

PUT /api/v1/admin/promo/{promo_id}
  Body: { ...updated fields }

POST /api/v1/admin/promo/{promo_id}/activate
POST /api/v1/admin/promo/{promo_id}/pause
POST /api/v1/admin/promo/{promo_id}/cancel
POST /api/v1/admin/promo/{promo_id}/clone
  → Creates new DRAFT with same settings

GET /api/v1/admin/promo/list
  Query: ?status=ACTIVE
  Response: [{ promo with stats }, ...]

GET /api/v1/admin/promo/{promo_id}/stats
  Response: { stats, redemption_log }

GET /api/v1/admin/promo/{promo_id}/redemptions
  Query: ?limit=50
  Response: [{ user, amount, bonus, date }, ...]

# Client endpoints (existing — updated)
GET /api/v1/credit/balance → now includes active_promos array
POST /api/v1/credit/topup → now checks promos, applies best match
  Body: { slip_base64, amount, promo_code? }
  Response: { base_credits, bonus_credits, total_credits, promo_applied }
```

---

## 8. Stacking Rules

```
⚠️ NO STACKING — ใช้ได้ครั้งละ 1 โปรเท่านั้น

เมื่อมีหลายโปร active พร้อมกัน:
  1. Filter เฉพาะโปรที่ user มีสิทธิ์
  2. Sort by priority (DESC), then by bonus_credits (DESC)
  3. ใช้โปรแรก (ดีที่สุด) เท่านั้น

ตัวอย่าง:
  - Active: "New Year Tiered" (priority 10) + "First Topup x6" (priority 5)
  - User เติมครั้งแรก 500 THB
  - "New Year Tiered" → 2,200 cr (bonus 200)
  - "First Topup x6" → 3,000 cr (bonus 1,000)
  - ระบบเลือก "New Year Tiered" เพราะ priority สูงกว่า
  
  ถ้าอยากให้ First Topup ชนะ → ตั้ง priority สูงกว่า
```

---

## 9. Cloud Scheduler Jobs

```bash
# Expire promotions (every hour)
gcloud scheduler jobs create http bigeye-expire-promos \
  --schedule "0 * * * *" \
  --uri "${SERVICE_URL}/api/v1/system/expire-promotions" \
  --http-method POST
```

---

## 10. AI IDE Task

```
## [Task A-13] Promotion System (NEW)

TASK: Implement full promotion engine.

NEW COLLECTIONS: promotions, promo_redemptions

NEW FILES:
  backend/app/routers/admin_promo.py — CRUD + activate/pause/cancel/clone
  backend/app/services/promo_engine.py — find_applicable_promos, calculate_bonus
  backend/app/models/promo.py — Pydantic models

MODIFY:
  backend/app/routers/credit.py:
    - GET /balance → add active_promos to response
    - POST /topup → integrate promo_engine, apply best promo

CLIENT CHANGES:
  - credit_bar.py → show promo banner if active_promos present
  - topup_dialog.py → display promo tiers/bonus, promo code input
  - history_dialog.py → show bonus tag on promo top-ups

ACCEPTANCE CRITERIA:
✅ Admin creates tiered promo → user tops up 500 → gets 2,200 cr (not 2,000)
✅ Promo with code: only applies when correct code entered
✅ Max per user enforced (user can't use same promo more than N times)
✅ Multiple active promos: highest priority wins
✅ Auto-expire past end_date
✅ Clone expired promo → new draft with same settings
✅ Stats track redemptions, bonus given, revenue
✅ Client shows banner + promo details in TopUp dialog
```

---

*Promotion & Campaign System Specification — Complete*
*Integrates with: Database Design, Pricing Management, Admin Dashboard, Frontend Design v3*
