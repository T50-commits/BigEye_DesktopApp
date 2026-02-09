# BigEye Pro Admin — Frontend Redesign Specification

## สำหรับ AI IDE (Cursor / Windsurf / Claude Code)

> **เป้าหมาย:** ปรับปรุง Frontend ของ Admin Dashboard ที่ใช้ Streamlit ทั้งหมด ให้สวยงาม อ่านง่าย ใช้งานง่าย
> โดยยังคงใช้ Streamlit เป็น framework หลัก + Firestore เป็น backend เหมือนเดิม
> ออกแบบธีมใหม่ทั้งหมดเป็น **Dark Theme** พร้อม custom CSS injection

---

## 1. ภาพรวมโปรเจกต์

### 1.1 โปรเจกต์คืออะไร
BigEye Pro Admin คือ **Admin Dashboard** สำหรับจัดการระบบ BigEye Pro ซึ่งเป็นแอปพลิเคชัน desktop ที่ให้บริการดาวน์โหลดรูปภาพ/วิดีโอจาก stock image providers (iStock, Adobe Stock, Shutterstock) ผ่านระบบเครดิต

### 1.2 Tech Stack
- **Frontend:** Streamlit (Python) — multi-page app
- **Backend/DB:** Google Cloud Firestore
- **Charts:** Plotly (ผ่าน `st.plotly_chart`)
- **Deployment:** Streamlit Cloud หรือ VM

### 1.3 โครงสร้างไฟล์
```
project/
├── app.py                          # Entry point (Streamlit multipage)
├── pages/
│   ├── 1_Dashboard.py              # หน้าแดชบอร์ด
│   ├── 2_Users.py                  # จัดการผู้ใช้
│   ├── 3_Slips.py                  # สลิปเติมเงิน
│   ├── 4_Jobs.py                   # ตรวจสอบงาน
│   ├── 5_System_Config.py          # ตั้งค่าระบบ
│   ├── 6_Audit_Logs.py             # บันทึกระบบ
│   └── 7_Promotions.py             # โปรโมชั่น
├── utils/
│   ├── firestore_client.py         # Firestore references
│   ├── charts.py                   # Plotly chart functions
│   └── theme.py                    # CSS injection (inject_css)
└── .streamlit/
    └── config.toml                 # Streamlit config
```

---

## 2. Design System — ธีมและ UI ที่ต้องใช้ทั่วทั้งโปรเจกต์

### 2.1 สีหลัก (Dark Theme)
ใส่ใน `utils/theme.py` เป็น CSS variables inject ผ่าน `st.markdown(..., unsafe_allow_html=True)`

```css
:root {
  --bg-primary: #080c16;       /* พื้นหลังหลัก */
  --bg-secondary: #0f1629;     /* พื้นหลัง sidebar / cards */
  --bg-card: #1a2035;          /* พื้นหลัง card */
  --bg-card-hover: #1e2642;    /* hover state */
  --bg-input: #0f1629;         /* input fields */
  --border: #1e293b;           /* เส้นขอบ */
  --border-light: #334155;     /* เส้นขอบ hover */
  --text-primary: #f1f5f9;     /* ตัวหนังสือหลัก */
  --text-secondary: #94a3b8;   /* ตัวหนังสือรอง */
  --text-muted: #64748b;       /* ตัวหนังสือจาง */
  --accent-blue: #3b82f6;
  --accent-cyan: #06b6d4;
  --accent-green: #10b981;
  --accent-yellow: #f59e0b;
  --accent-red: #ef4444;
  --accent-purple: #8b5cf6;
  --accent-pink: #ec4899;
  --accent-orange: #f97316;
}
```

### 2.2 Fonts
```css
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:wght@400;500;600;700;800&display=swap');

body { font-family: 'DM Sans', 'IBM Plex Sans Thai', sans-serif; }
code, .mono { font-family: 'JetBrains Mono', monospace; }
```

### 2.3 Streamlit Config (`.streamlit/config.toml`)
```toml
[theme]
primaryColor = "#3b82f6"
backgroundColor = "#080c16"
secondaryBackgroundColor = "#0f1629"
textColor = "#f1f5f9"
font = "sans serif"

[server]
headless = true
```

### 2.4 inject_css() — สิ่งที่ต้อง Override ใน Streamlit
ไฟล์ `utils/theme.py` ต้อง inject CSS ที่ override ธีมเริ่มต้นของ Streamlit ทั้งหมด:

```python
import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    /* ซ่อน Streamlit default elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Override sidebar */
    [data-testid="stSidebar"] {
        background: #0f1629;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] .css-1d391kg { padding-top: 1rem; }

    /* Override main area */
    .main .block-container {
        padding: 2rem;
        max-width: 1400px;
    }

    /* Override dataframe */
    [data-testid="stDataFrame"] {
        background: #1a2035;
        border: 1px solid #1e293b;
        border-radius: 14px;
        overflow: hidden;
    }

    /* Override buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: #3b82f6;
        border-color: #3b82f6;
    }
    .stButton > button[kind="primary"]:hover {
        background: #2563eb;
        box-shadow: 0 0 20px rgba(59,130,246,0.15);
    }

    /* Override inputs */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea textarea {
        background: #0f1629 !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
        color: #f1f5f9 !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f6 !important;
    }

    /* Override tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: 1px solid #1e293b;
        border-radius: 8px;
        color: #94a3b8;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: #3b82f6 !important;
        border-color: #3b82f6 !important;
        color: white !important;
    }

    /* Override expander */
    .streamlit-expanderHeader {
        background: #1a2035;
        border: 1px solid #1e293b;
        border-radius: 10px;
    }

    /* Override divider */
    hr { border-color: #1e293b !important; }

    /* Override metric */
    [data-testid="stMetric"] {
        background: #1a2035;
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
```

---

## 3. Component Library — HTML Components ที่ต้องสร้าง

### 3.1 Metric Card
ใช้แทน `st.metric()` เดิม — สร้างเป็น function ใน `utils/components.py`

```python
def metric_card(icon: str, label: str, value: str, color: str, sub: str = "", trend: str = "") -> str:
    """
    Render metric card ที่มี:
    - glow effect (วงกลมสีเบลอ มุมขวาบน)
    - label ตัวเล็ก uppercase
    - ตัวเลขขนาดใหญ่ (2rem, font-weight 800)
    - sub text ด้านล่าง พร้อม trend arrow (↑ สีเขียว, ↓ สีแดง)
    - hover: ขยับขึ้น 2px + box-shadow
    """
    trend_html = ""
    if trend:
        trend_color = "var(--accent-green)" if trend.startswith("↑") else "var(--accent-red)"
        trend_html = f'<span style="color:{trend_color}">{trend}</span> '

    return f"""
    <div style="
        background: #1a2035;
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 22px 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
    ">
        <div style="
            position: absolute; top: -30px; right: -30px;
            width: 80px; height: 80px; border-radius: 50%;
            background: {color}; filter: blur(40px); opacity: 0.15;
        "></div>
        <div style="
            font-size: 0.78rem; color: #64748b;
            text-transform: uppercase; letter-spacing: 0.06em;
            margin-bottom: 10px; font-weight: 600;
        ">{icon} {label}</div>
        <div style="
            font-size: 2rem; font-weight: 800;
            color: {color}; line-height: 1.1; margin-bottom: 4px;
        ">{value}</div>
        <div style="font-size: 0.75rem; color: #64748b;">
            {trend_html}{sub}
        </div>
    </div>
    """
```

**ใช้งาน:**
```python
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(metric_card("👥", "ผู้ใช้งาน", "1,247", "#3b82f6", "ล็อกอินใน 24 ชม.", "↑ 12%"), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("🆕", "สมัครใหม่", "38", "#8b5cf6", "วันนี้", "↑ 5"), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("💰", "รายรับ", f"฿{topup_thb:,}", "#10b981", "เงินจริงที่ลูกค้าเติมวันนี้"), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card("📊", "รายได้รับรู้", f"฿{recognized_thb:,.2f}", "#06b6d4", f"เครดิตที่ใช้ ÷ {rate} = บาท"), unsafe_allow_html=True)
```

### 3.2 Alert Card
ใช้แทน `st.warning()` / `st.error()` เดิม

```python
def alert_card(icon: str, title: str, desc: str, style: str = "warning", action_label: str = "", action_page: str = "") -> str:
    """
    style: "warning" (เหลือง), "danger" (แดง), "success" (เขียว)

    เดิม: st.warning("3 สลิปรอตรวจสอบ")
    ใหม่: alert card ที่มี icon ใหญ่, title + description, ปุ่ม action ด้านขวา
    """
    colors = {
        "warning": ("rgba(245,158,11,0.08)", "rgba(245,158,11,0.25)", "#fbbf24"),
        "danger": ("rgba(239,68,68,0.08)", "rgba(239,68,68,0.25)", "#f87171"),
        "success": ("rgba(16,185,129,0.06)", "rgba(16,185,129,0.2)", "#34d399"),
    }
    bg, border, text_color = colors.get(style, colors["warning"])

    action_html = ""
    if action_label:
        action_html = f"""
        <div style="margin-left:auto;padding:6px 14px;border-radius:8px;
            font-size:0.78rem;font-weight:600;cursor:pointer;
            border:1px solid rgba(255,255,255,0.15);
            background:rgba(255,255,255,0.05);color:#94a3b8;">
            {action_label}
        </div>"""

    return f"""
    <div style="display:flex;align-items:center;gap:14px;
        padding:16px 20px;border-radius:14px;
        background:{bg};border:1px solid {border};">
        <div style="font-size:1.6rem">{icon}</div>
        <div>
            <div style="font-weight:700;font-size:0.95rem;color:{text_color}">{title}</div>
            <div style="font-size:0.78rem;color:#64748b;margin-top:2px">{desc}</div>
        </div>
        {action_html}
    </div>
    """
```

### 3.3 Status Badge
ใช้แทนการแสดงสถานะเป็น text ธรรมดา

```python
def status_badge(status: str) -> str:
    """
    แสดง status badge แบบมี dot กลม + สีตามสถานะ:
    - active/verified/completed = เขียว
    - pending/reserved = เหลือง
    - rejected/failed/suspended = แดง
    - expired = เทา
    - draft = ม่วง
    """
    styles = {
        "active":    ("rgba(16,185,129,0.12)", "#34d399"),
        "verified":  ("rgba(16,185,129,0.12)", "#34d399"),
        "completed": ("rgba(16,185,129,0.12)", "#34d399"),
        "pending":   ("rgba(245,158,11,0.12)", "#fbbf24"),
        "reserved":  ("rgba(245,158,11,0.12)", "#fbbf24"),
        "rejected":  ("rgba(239,68,68,0.12)", "#f87171"),
        "failed":    ("rgba(239,68,68,0.12)", "#f87171"),
        "suspended": ("rgba(239,68,68,0.12)", "#f87171"),
        "expired":   ("rgba(100,116,139,0.12)", "#94a3b8"),
        "draft":     ("rgba(139,92,246,0.12)", "#a78bfa"),
    }
    bg, color = styles.get(status.lower(), ("rgba(100,116,139,0.12)", "#94a3b8"))
    return f"""<span style="
        display:inline-flex;align-items:center;gap:5px;
        padding:4px 10px;border-radius:20px;
        font-size:0.75rem;font-weight:600;
        background:{bg};color:{color};
    "><span style="width:6px;height:6px;border-radius:50%;
        background:{color};display:inline-block;"></span> {status}</span>"""
```

### 3.4 User Avatar
แสดง avatar ตัวอักษรย่อพร้อม gradient สี

```python
def user_avatar(name: str, email: str, size: int = 32) -> str:
    """สร้าง avatar ย่อจากชื่อ/อีเมล พร้อม gradient สีแบบสุ่มตาม hash"""
    initials = ""
    if name and name != "—":
        parts = name.split()
        initials = "".join(p[0].upper() for p in parts[:2])
    else:
        initials = email[:2].upper()

    # สีจาก hash ของ email
    gradients = [
        "linear-gradient(135deg,#3b82f6,#06b6d4)",
        "linear-gradient(135deg,#8b5cf6,#ec4899)",
        "linear-gradient(135deg,#f59e0b,#f97316)",
        "linear-gradient(135deg,#10b981,#06b6d4)",
        "linear-gradient(135deg,#ef4444,#f97316)",
        "linear-gradient(135deg,#6366f1,#8b5cf6)",
    ]
    gradient = gradients[hash(email) % len(gradients)]

    return f"""<div style="
        width:{size}px;height:{size}px;border-radius:8px;
        background:{gradient};
        display:flex;align-items:center;justify-content:center;
        font-size:{size*0.38}px;font-weight:700;color:#fff;
        flex-shrink:0;
    ">{initials}</div>"""
```

### 3.5 Data Section Wrapper
ครอบตาราง / รายการข้อมูล ให้มี header + filter pills

```python
def data_section_start(title: str, tag: str = "") -> str:
    tag_html = f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:#0f1629;border:1px solid #1e293b;color:#64748b;margin-left:8px">{tag}</span>' if tag else ""
    return f"""
    <div style="background:#1a2035;border:1px solid #1e293b;border-radius:14px;overflow:hidden;margin-bottom:24px;">
        <div style="display:flex;justify-content:space-between;align-items:center;
            padding:18px 24px;border-bottom:1px solid #1e293b;">
            <div style="font-weight:700;font-size:1rem;display:flex;align-items:center;gap:8px;">
                {title} {tag_html}
            </div>
        </div>
    """

def data_section_end() -> str:
    return "</div>"
```

---

## 4. หน้าที่ต้องปรับปรุง — รายละเอียดแต่ละหน้า

### 4.1 Dashboard (`pages/1_Dashboard.py`)

**หน้าที่ของหน้านี้:** แสดงสถิติรวมของวันนี้ + กราฟ 30 วัน + รายการรอดำเนินการ

**ข้อมูลที่ดึงจาก Firestore (ยังเหมือนเดิม):**
- `users` collection → นับ active users (login ใน 24 ชม.), new users วันนี้
- `slips` collection → ยอดเติมเงินวันนี้ (status=VERIFIED)
- `jobs` collection → จำนวนงานวันนี้, งาน failed วันนี้
- `system_config/app_settings` → exchange_rate
- `daily_reports` collection → ข้อมูลรายวัน 30 วัน สำหรับกราฟ
- `slips` (status=PENDING) → สลิปรอตรวจ
- `jobs` (status=RESERVED, created_at <= 2 ชม.ก่อน) → งานค้าง

**Layout ใหม่:**

```
┌─────────────────────────────────────────────────┐
│ Row 1: Metric Cards (4 คอลัมน์)                  │
│ [ผู้ใช้งาน] [สมัครใหม่] [รายรับ] [รายได้รับรู้]     │
├─────────────────────────────────────────────────┤
│ Row 2: Metric Cards (3 คอลัมน์)                  │
│ [งานทั้งหมด] [งานผิดพลาด] [อัตราสำเร็จ]          │
├─────────────────────────────────────────────────┤
│ Row 3: Alert Cards (2 คอลัมน์)                   │
│ [สลิปรอตรวจ-เหลือง] [งานค้าง-แดง]                │
│ หรือ [ระบบปกติ-เขียว] (full width ถ้าไม่มี alert) │
├─────────────────────────────────────────────────┤
│ Row 4: Charts (2 คอลัมน์)                        │
│ [กราฟรายได้ 30 วัน] [กราฟผู้ใช้ใหม่ 30 วัน]        │
└─────────────────────────────────────────────────┘
```

**สิ่งที่ต้องเปลี่ยน:**
1. แทนที่ `_metric_card()` เดิม (เป็น light theme) → ใช้ `metric_card()` ใหม่ (dark theme + glow)
2. เพิ่ม metric "อัตราสำเร็จ" (คำนวณจาก jobs completed / total)
3. แทนที่ `st.markdown(alert HTML)` เดิม → ใช้ `alert_card()` ใหม่
4. Chart cards ให้ครอบด้วย card style (bg-card, border, border-radius)
5. กราฟ Plotly ให้ใช้ dark theme: `template="plotly_dark"`, `paper_bgcolor='rgba(0,0,0,0)'`, `plot_bgcolor='rgba(0,0,0,0)'`

**Plotly chart theme ใน `utils/charts.py`:**
```python
def revenue_chart(data):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d["date"] for d in data],
        y=[d["revenue"] for d in data],
        marker_color='#10b981',
        marker_line_width=0,
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=200,
        xaxis=dict(gridcolor='rgba(255,255,255,0.04)', showgrid=False),
        yaxis=dict(gridcolor='rgba(255,255,255,0.04)'),
        font=dict(family="DM Sans, IBM Plex Sans Thai", color="#94a3b8"),
    )
    return fig
```

---

### 4.2 Users (`pages/2_Users.py`)

**หน้าที่:** ค้นหาผู้ใช้, ดูข้อมูล, ปรับเครดิต, ระงับ/เปิดบัญชี, รีเซ็ต Hardware ID

**ข้อมูลจาก Firestore:**
- `users` collection → ค้นหาด้วย email/full_name, ดึง 50 รายการล่าสุด
- `transactions` collection → ประวัติเครดิตของผู้ใช้
- `jobs` collection → ประวัติงานของผู้ใช้

**Layout ใหม่:**
```
┌─────────────────────────────────────────────────┐
│ Data Section: ตารางผู้ใช้                          │
│ Header: [ชื่อหน้า + tag จำนวน] [🔍 search box]    │
│ ┌─────────────────────────────────────────────┐ │
│ │ Table columns:                              │ │
│ │ ผู้ใช้(avatar+email+name) | เครดิต |          │ │
│ │ สถานะ(badge) | ใช้งานล่าสุด | สมัครเมื่อ       │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘

เมื่อเลือกแถว → แสดง User Detail ด้านล่าง (ใช้ st.container)
┌─────────────────────────────────────────────────┐
│ 👤 User Header: [Avatar ใหญ่] [email] [name]     │
├─────────────────────────────────────────────────┤
│ Info Grid (2 columns):                           │
│ [เครดิต] [เติมเงินรวม] [สถานะ] [สมัครเมื่อ]       │
│ [Hardware ID - full width]                       │
├─────────────────────────────────────────────────┤
│ Actions: [ปรับเครดิต] [ระงับ/เปิดบัญชี] [รีเซ็ต HW] │
├─────────────────────────────────────────────────┤
│ Tabs: [💳 ประวัติเครดิต] [📋 ประวัติงาน]             │
└─────────────────────────────────────────────────┘
```

**สิ่งที่ต้องเปลี่ยน:**
1. ตาราง → เพิ่ม user avatar (ตัวอักษรย่อ + gradient) ก่อนอีเมล
2. สถานะ → ใช้ `status_badge()` แทน text ธรรมดา
3. User detail panel → ใช้ info grid cards (bg-card, border-radius)
4. ประวัติเครดิต → แสดงเป็น list items ที่มี +/- สีเขียว/แดง แทน dataframe เปล่า
5. Action buttons → ใช้สีตาม context (primary=ปรับเครดิต, danger=ระงับ, ghost=รีเซ็ต)

**Info Item component:**
```python
def info_item(label: str, value: str, color: str = "", full_width: bool = False) -> str:
    """แสดงข้อมูลใน card เล็ก มี label ด้านบนและ value ด้านล่าง"""
    style = f"color:{color}" if color else ""
    span = "grid-column:1/-1;" if full_width else ""
    return f"""
    <div style="padding:14px 16px;background:#1a2035;border-radius:8px;
        border:1px solid #1e293b;{span}">
        <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;
            color:#64748b;margin-bottom:4px;font-weight:600">{label}</div>
        <div style="font-size:1rem;font-weight:600;{style}">{value}</div>
    </div>"""
```

**Transaction list item:**
```python
def transaction_item(description: str, date: str, amount: int) -> str:
    color = "#34d399" if amount > 0 else "#f87171"
    sign = "+" if amount > 0 else ""
    return f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
        padding:10px 14px;background:#1a2035;border-radius:8px;
        border:1px solid #1e293b;margin-bottom:8px">
        <div>
            <div style="font-size:0.85rem;font-weight:500">{description}</div>
            <div style="font-size:0.72rem;color:#64748b">{date}</div>
        </div>
        <span style="font-weight:700;color:{color};font-size:0.95rem">
            {sign}{amount:,}
        </span>
    </div>"""
```

---

### 4.3 Slips (`pages/3_Slips.py`)

**หน้าที่:** กรองสลิปตามสถานะ, ดูภาพสลิป, อนุมัติ/ปฏิเสธ

**ข้อมูลจาก Firestore:**
- `slips` collection → กรองด้วย status, เรียงตาม created_at DESC
- `users` collection → อัพเดทเครดิตเมื่ออนุมัติ
- `transactions` collection → บันทึกรายการเมื่ออนุมัติ

**Layout ใหม่:**
```
┌─────────────────────────────────────────────────┐
│ Data Section: ตารางสลิป                           │
│ Header: [ชื่อหน้า] [Filter Pills: PENDING|         │
│          VERIFIED|REJECTED|ALL]                    │
│ ┌─────────────────────────────────────────────┐ │
│ │ Table columns:                              │ │
│ │ วันที่(mono) | ผู้ใช้ | จำนวน(สีเขียว) |        │ │
│ │ เลขอ้างอิง(mono,cyan) | สถานะ(badge) |        │ │
│ │ [ปุ่มตรวจสอบ - เฉพาะ PENDING]                 │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘

เมื่อเลือกสลิป PENDING → แสดง Review Panel:
┌─────────────────────────────────────────────────┐
│ Left column: ภาพสลิป (st.image)                   │
│ Right column:                                     │
│   Info Grid: [ผู้ใช้] [จำนวน] [เลขอ้างอิง] [วันที่]  │
│   จำนวนเครดิต: [input ตัวเลข] (คำนวณ: ฿ × rate)   │
│   Actions: [✅ อนุมัติ] [❌ ปฏิเสธ + เหตุผล]        │
└─────────────────────────────────────────────────┘
```

**Filter Pills:** แทน `st.selectbox` → ใช้ปุ่มกลมๆ แถวเดียว
```python
def filter_pills(options: list[str], selected: str) -> None:
    """แสดง filter pills เป็นแถวปุ่มกลม ใช้ st.columns + st.button"""
    cols = st.columns(len(options))
    for i, opt in enumerate(options):
        with cols[i]:
            btn_type = "primary" if opt == selected else "secondary"
            if st.button(opt, key=f"filter_{opt}", type=btn_type):
                st.session_state["filter"] = opt
                st.rerun()
```

**สิ่งที่ต้องเปลี่ยน:**
1. Filter → เปลี่ยนจาก selectbox เป็น filter pills
2. จำนวนเงิน → แสดงสีเขียว + font-weight bold
3. เลขอ้างอิง → ใช้ mono font สีฟ้า (cyan)
4. ปุ่ม "ตรวจสอบ" → ปุ่ม primary เล็กๆ ในคอลัมน์สุดท้าย
5. Review panel → จัดเป็น 2 คอลัมน์ (ภาพ | ข้อมูล+action)

---

### 4.4 Jobs (`pages/4_Jobs.py`)

**หน้าที่:** กรองงาน, ดูรายละเอียด, คืนเครดิตงานค้าง

**ข้อมูลจาก Firestore:**
- `jobs` collection → กรองด้วย status
- `users` collection → resolve email จาก user_id, อัพเดทเครดิตเมื่อ refund

**Layout ใหม่:**
```
┌─────────────────────────────────────────────────┐
│ Data Section: ตารางงาน                            │
│ Header: [ชื่อหน้า] [Filter Pills: ALL|RESERVED|    │
│          COMPLETED|EXPIRED|FAILED]                │
│ ┌─────────────────────────────────────────────┐ │
│ │ Table columns:                              │ │
│ │ Token(mono,cyan) | ผู้ใช้ | โหมด(tag) |         │ │
│ │ ไฟล์ | สถานะ(badge) | สร้างเมื่อ                │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘

เมื่อเลือกงาน → แสดง Job Detail:
┌─────────────────────────────────────────────────┐
│ Header: [Job Token (mono)] [Status Badge]         │
│ Info Grid (2 columns):                           │
│ [จองไว้ cr] [ใช้แล้ว cr] [ไฟล์] [โหมด]             │
│ [สำเร็จ] [ล้มเหลว] [ผู้ใช้ - full width]            │
│ [อายุ] [เวอร์ชัน]                                  │
├─────────────────────────────────────────────────┤
│ ถ้า RESERVED + อายุ > 2 ชม.:                      │
│ ⚠️ Alert Card: "งานค้างเกิน 2 ชั่วโมง"              │
│ [💰 ปุ่มคืนเครดิต (สีเหลือง)]                       │
└─────────────────────────────────────────────────┘
```

**สิ่งที่ต้องเปลี่ยน:**
1. Token → แสดงเป็น mono font สีฟ้า (cyan) ตัด 8 ตัว + "..."
2. โหมด → แสดงเป็น tag (พื้นหลังเข้ม + border + ตัวอักษรจาง)
3. งานค้าง → แสดง alert card สีแดง + ปุ่มคืนเครดิตสีเหลือง
4. filter pills แทน selectbox

---

### 4.5 System Config (`pages/5_System_Config.py`)

**หน้าที่:** ตั้งค่าเวอร์ชันแอป, อัตราเครดิต, การประมวลผล, maintenance mode, พรอมต์, blacklist

**Layout ใหม่:**
```
┌──────────────────────┬──────────────────────┐
│ Card: 📱 เวอร์ชันแอป   │ Card: 💰 อัตราเครดิต   │
│ - เวอร์ชันล่าสุด        │ - iStock ภาพ/วิดีโอ    │
│ - บังคับอัพเดท          │ - Adobe ภาพ/วิดีโอ     │
│ - ลิงก์ดาวน์โหลด       │ - exchange rate       │
│ [💾 บันทึก]             │ [💾 บันทึก]             │
├──────────────────────┼──────────────────────┤
│ Card: ⚙️ การประมวลผล  │ Card: 🚧 Maintenance  │
│ - context cache       │ - Toggle switch       │
│ - max images          │ - ข้อความแจ้ง           │
│ - max videos          │ - Status indicator    │
│ [💾 บันทึก]             │ (เขียว=ปกติ / แดง=ปิด)  │
├──────────────────────┼──────────────────────┤
│ Card: 📝 พรอมต์        │ Card: 🚫 Blacklist     │
│ - รายการพรอมต์ 3 แบบ   │ - input + ปุ่มเพิ่ม       │
│ - แต่ละแบบมีจำนวนตัวอักษร│ - แสดง tags สีแดง      │
│ - ปุ่มแก้ไขแต่ละแบบ      │ - แต่ละ tag มี × ลบ     │
└──────────────────────┴──────────────────────┘
```

**Config Card wrapper:**
```python
def config_card(title: str, content_html: str) -> str:
    return f"""
    <div style="background:#1a2035;border:1px solid #1e293b;
        border-radius:14px;padding:24px;">
        <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:16px;
            display:flex;align-items:center;gap:8px">{title}</h4>
        {content_html}
    </div>"""
```

**Maintenance Toggle:** ใช้ `st.toggle()` (Streamlit built-in) แล้ว style ด้วย CSS
```python
is_maintenance = st.toggle("เปิด Maintenance Mode", value=_settings.get("maintenance_mode", False))
```

**Blacklist Tags:** แสดงเป็น chips/tags สีแดง
```python
def blacklist_tag(word: str) -> str:
    return f"""<span style="display:inline-flex;align-items:center;gap:6px;
        padding:5px 12px;border-radius:20px;
        background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);
        font-size:0.78rem;color:#f87171">{word}
        <span style="cursor:pointer;opacity:0.6">×</span></span>"""
```

---

### 4.6 Audit Logs (`pages/6_Audit_Logs.py`)

**หน้าที่:** แสดง log ระบบ กรองตามระดับ severity

**Layout ใหม่:**
```
┌─────────────────────────────────────────────────┐
│ Data Section: บันทึกระบบ                          │
│ Header: [ชื่อหน้า] [Filter Pills: WARNING+|ALL|     │
│          INFO|WARNING|ERROR|CRITICAL]              │
│ ┌─────────────────────────────────────────────┐ │
│ │ Log entries (แต่ละ entry):                    │ │
│ │ [●severity dot(glow)] [event title]          │ │
│ │ [meta: user, details] [เวลา(mono) ขวามือ]     │ │
│ │ คลิกเพื่อ expand → แสดง JSON details          │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Severity Dot styling:**
```python
def severity_dot(severity: str) -> str:
    colors = {
        "INFO":     ("#3b82f6", "rgba(59,130,246,0.4)"),
        "WARNING":  ("#f59e0b", "rgba(245,158,11,0.4)"),
        "ERROR":    ("#ef4444", "rgba(239,68,68,0.4)"),
        "CRITICAL": ("#7c3aed", "rgba(124,58,237,0.4)"),
    }
    bg, shadow = colors.get(severity, ("#94a3b8", "rgba(148,163,184,0.4)"))
    return f"""<div style="width:10px;height:10px;border-radius:50%;
        background:{bg};box-shadow:0 0 8px {shadow};
        flex-shrink:0;margin-top:6px"></div>"""
```

**สิ่งที่ต้องเปลี่ยน:**
1. เปลี่ยนจาก `st.expander()` เป็น log entry list ที่มี severity dot + กดเพื่อ expand
2. Meta info (user, job token, IP) แสดงในแถวเดียว สีจาง
3. เวลาแสดงด้วย mono font ชิดขวา
4. Event labels ภาษาไทย (ใช้ `_EVENT_LABELS` ที่มีอยู่แล้ว)

---

### 4.7 Promotions (`pages/7_Promotions.py`)

**หน้าที่:** สร้าง/แก้ไข/จัดการโปรโมชั่น

**Layout ใหม่:**
```
┌─────────────────────────────────────────────────┐
│ Header Row: [Filter Pills] [➕ สร้างโปรโมชั่นใหม่]   │
├─────────────────────────────────────────────────┤
│ Promo Grid (auto-fill, minmax 340px):             │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│ │ Card 1  │ │ Card 2  │ │ Card 3  │              │
│ │ banner  │ │ banner  │ │ banner  │              │
│ │ gradient│ │ gradient│ │ gradient│              │
│ │─────────│ │─────────│ │─────────│              │
│ │ name    │ │ name    │ │ name    │              │
│ │ type    │ │ type    │ │ type    │              │
│ │ status  │ │ status  │ │ status  │              │
│ │ banner  │ │ banner  │ │ banner  │              │
│ │ text    │ │ text    │ │ text    │              │
│ │─────────│ │─────────│ │─────────│              │
│ │ stats:  │ │ stats:  │ │ stats:  │              │
│ │ ใช้|bonus│ │ ใช้|bonus│ │ ใช้|bonus│              │
│ │ |ยอดเติม │ │ |ยอดเติม │ │ |ยอดเติม │              │
│ └─────────┘ └─────────┘ └─────────┘              │
└─────────────────────────────────────────────────┘

แต่ละ card มี:
- 8px gradient banner ด้านบน (ตามสี banner_color)
- ชื่อโปร + ประเภท + status badge
- ข้อความ banner ใน box สีอ่อน
- สถิติ 3 ตัว: จำนวนใช้ | เครดิตโบนัส | ยอดเติม
```

**Promo Card component:**
```python
def promo_card(promo: dict) -> str:
    name = promo.get("name", "—")
    status = promo.get("status", "DRAFT")
    display = promo.get("display", {})
    stats = promo.get("stats", {})
    banner_color = display.get("banner_color", "#775DD0")
    banner_text = display.get("banner_text", "")
    # ... สร้าง HTML card
```

---

## 5. Business Logic ที่ต้องคงไว้เหมือนเดิม

**ห้ามเปลี่ยน logic เหล่านี้:**

### 5.1 Firestore Operations
- ทุก collection reference (`users_ref()`, `jobs_ref()`, etc.) ใช้จาก `utils/firestore_client.py`
- การ query ใช้ simple filter + sort ใน Python (หลีกเลี่ยง composite index)
- ใช้ `FieldFilter` สำหรับ where clause

### 5.2 Credit System
- อนุมัติสลิป → เพิ่มเครดิต user + บันทึก transaction
- ปรับเครดิต → อัพเดท user + บันทึก transaction (type=ADJUSTMENT)
- คืนเครดิต → อัพเดท job status เป็น EXPIRED + เพิ่มเครดิต user + บันทึก transaction (type=REFUND)
- exchange_rate มาจาก `system_config/app_settings`

### 5.3 Caching
- ใช้ `@st.cache_data(ttl=60)` สำหรับข้อมูลที่เปลี่ยนบ่อย (stats, pending)
- ใช้ `@st.cache_data(ttl=300)` สำหรับข้อมูลที่เปลี่ยนน้อย (daily reports)
- เมื่อมีการแก้ไขข้อมูล → `st.cache_data.clear()` + `st.rerun()`

### 5.4 Security
- ทุกหน้าต้อง authenticate (ถ้ามี auth middleware)
- ไม่แสดง full user_id → ตัดเหลือ 12 ตัว + "..."
- Hardware ID แสดงเฉพาะใน user detail

---

## 6. ไฟล์ที่ต้องสร้างใหม่

```
utils/
├── theme.py          # ← เขียนใหม่: inject_css() + dark theme CSS
├── components.py     # ← สร้างใหม่: metric_card, alert_card, status_badge,
│                     #   user_avatar, info_item, transaction_item,
│                     #   filter_pills, config_card, blacklist_tag,
│                     #   severity_dot, promo_card, data_section
└── charts.py         # ← แก้ไข: เปลี่ยนเป็น dark theme Plotly charts
```

---

## 7. Checklist

- [ ] `utils/theme.py` — Dark theme CSS injection ครอบคลุม Streamlit ทุก component
- [ ] `utils/components.py` — HTML component functions ทั้งหมด
- [ ] `utils/charts.py` — Plotly charts dark theme
- [ ] `.streamlit/config.toml` — Dark theme config
- [ ] `pages/1_Dashboard.py` — ใช้ metric_card, alert_card, dark charts
- [ ] `pages/2_Users.py` — ใช้ user_avatar, status_badge, info_item, transaction_item
- [ ] `pages/3_Slips.py` — ใช้ filter_pills, status_badge, info grid
- [ ] `pages/4_Jobs.py` — ใช้ filter_pills, status_badge, alert_card สำหรับงานค้าง
- [ ] `pages/5_System_Config.py` — ใช้ config_card, toggle, blacklist_tag
- [ ] `pages/6_Audit_Logs.py` — ใช้ severity_dot, log entry layout
- [ ] `pages/7_Promotions.py` — ใช้ promo_card grid, filter_pills
- [ ] ทดสอบว่า Firestore operations ยังทำงานปกติ
- [ ] ทดสอบว่าทุกปุ่ม action (อนุมัติ/ปฏิเสธ/ปรับเครดิต/คืนเครดิต) ยังทำงานปกติ
- [ ] ทดสอบ responsive layout (4 col → 2 col → 1 col)

---

## 8. หมายเหตุสำคัญ

1. **อย่าเปลี่ยน Firestore query logic** — แค่เปลี่ยนวิธีแสดงผล
2. **ใช้ `unsafe_allow_html=True`** — จำเป็นสำหรับ custom HTML components
3. **Font import ต้องอยู่ใน `inject_css()`** — ผ่าน `<style>@import url(...)</style>`
4. **ทุกสีต้อง consistent** — ใช้ CSS variables หรือ Python constants
5. **Plotly charts** — ต้องใช้ `use_container_width=True` เสมอ
6. **อ้างอิง prototype** — ดูไฟล์ `BigEye_Pro_Admin_Redesign.html` สำหรับ visual reference
