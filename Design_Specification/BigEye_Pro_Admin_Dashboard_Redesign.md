# BigEye Pro — Admin Dashboard Redesign
### จากธรรมดา → Professional Dashboard ที่ดูดีและใช้งานง่าย
### สำหรับสั่ง AI IDE แก้ไข

---

## ปัญหาปัจจุบัน

1. **สีจืดชืด** — Streamlit default ขาว/เทา ไม่มี identity
2. **ข้อมูลกระจัด** — ตัวเลขสำคัญหาไม่เจอ
3. **ไม่มี visual hierarchy** — ทุกอย่างดูเท่ากันหมด
4. **Alert ไม่โดดเด่น** — สลิปรอตรวจ / งานค้าง ดูไม่เห็น
5. **กราฟไม่สื่อ** — ไม่มี context, ไม่มี comparison

---

## Design Direction: "Executive Dark Dashboard"

**แนวคิด:** Dashboard แบบ CEO-level ที่เปิดขึ้นมาเห็นสถานะทุกอย่างภายใน 3 วินาที

- **Dark theme** — ลดความล้าตา (admin ใช้ทั้งวัน)
- **Color accent** ใช้ gradient เดียวกับ BigEye Pro app: `#FF00CC → #7B2FFF`
- **Card-based layout** — ทุกข้อมูลอยู่ใน card ที่ชัดเจน
- **Status-first** — เรื่องด่วนขึ้นบนสุดเสมอ

---

## ไฟล์ที่ต้องแก้

| ไฟล์ | แก้อะไร |
|:--|:--|
| `utils/theme.py` | เปลี่ยน CSS ทั้งหมด → Dark Executive Theme |
| `pages/1_Dashboard.py` | Redesign metric cards + charts |
| `pages/2_Users.py` | ปรับ table + detail panel |
| `pages/3_Slips.py` | ปรับ slip review layout |
| `pages/4_Jobs.py` | ปรับ job detail layout |
| `pages/5_System_Config.py` | จัดกลุ่ม settings ดีขึ้น |
| `pages/6_Audit_Logs.py` | ปรับ log entry display |
| `pages/7_Promotions.py` | ปรับ promo card layout |
| `app.py` | ปรับ home page + navigation |

---

## Step 1: แก้ `utils/theme.py` — Dark Executive Theme

### แทนที่ `_CSS` ทั้งหมดด้วย:

```python
_CSS = """
<style>
    /* ═══════════════════════════════════════
       BigEye Pro Admin — Executive Dark Theme
       ═══════════════════════════════════════ */

    /* ── Root variables ── */
    :root {
        --bg-primary: #0B0F19;
        --bg-secondary: #111827;
        --bg-card: #1A2035;
        --bg-card-hover: #1F2A45;
        --border: #1E2A45;
        --border-light: #2A3A5C;
        --text-primary: #E8ECF4;
        --text-secondary: #8892A8;
        --text-dim: #4A5568;
        --accent-pink: #FF00CC;
        --accent-purple: #7B2FFF;
        --success: #00E396;
        --warning: #FEB019;
        --error: #FF4560;
        --info: #00B4D8;
        --gold: #FFD700;
    }

    /* ── Global background ── */
    .stApp, [data-testid="stAppViewContainer"] {
        background: var(--bg-primary) !important;
    }
    .main .block-container {
        padding-top: 1.2rem;
        max-width: 1400px;
    }

    /* ── Sidebar — Deep Navy gradient ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e1a 0%, #0d1526 50%, #111d35 100%) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] * {
        color: var(--text-secondary) !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--border);
        color: var(--text-primary) !important;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 500;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(135deg, rgba(255,0,204,0.08), rgba(123,47,255,0.08));
        border-color: rgba(255,0,204,0.3);
        color: var(--accent-pink) !important;
    }

    /* ── Headers ── */
    h1 {
        color: var(--text-primary) !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
    }
    p, li, span, label, .stMarkdown {
        color: var(--text-secondary) !important;
    }

    /* ── Cards (st.metric, forms, expanders) ── */
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 20px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Forms ── */
    [data-testid="stForm"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 24px !important;
    }

    /* ── Inputs ── */
    input, textarea, [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        background: var(--bg-secondary) !important;
        border-color: var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 10px !important;
    }
    input:focus, textarea:focus {
        border-color: var(--accent-pink) !important;
    }

    /* ── Select / Dropdowns ── */
    [data-baseweb="select"] > div {
        background: var(--bg-secondary) !important;
        border-color: var(--border) !important;
        border-radius: 10px !important;
    }
    [data-baseweb="select"] * {
        color: var(--text-primary) !important;
    }
    [data-baseweb="popover"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
    }
    [data-baseweb="menu"] {
        background: var(--bg-card) !important;
    }
    [data-baseweb="menu"] li {
        color: var(--text-secondary) !important;
    }
    [data-baseweb="menu"] li:hover {
        background: rgba(255,0,204,0.08) !important;
        color: var(--accent-pink) !important;
    }

    /* ── Buttons ── */
    .stButton button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        border-radius: 10px !important;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, rgba(255,0,204,0.1), rgba(123,47,255,0.1)) !important;
        border-color: rgba(255,0,204,0.4) !important;
        color: var(--accent-pink) !important;
    }
    /* Primary buttons — gradient */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent-pink), var(--accent-purple)) !important;
        border: none !important;
        color: #fff !important;
        font-weight: 600;
    }
    .stButton button[kind="primary"]:hover {
        opacity: 0.9;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        margin-bottom: 10px;
    }
    [data-testid="stExpander"] summary {
        color: var(--text-primary) !important;
    }

    /* ── Dataframe / Tables ── */
    [data-testid="stDataFrame"] {
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    [data-testid="stDataFrame"] table {
        background: var(--bg-card) !important;
    }
    [data-testid="stDataFrame"] th {
        background: var(--bg-secondary) !important;
        color: var(--text-secondary) !important;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stDataFrame"] td {
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--bg-secondary);
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border-radius: 8px;
        padding: 8px 20px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: var(--bg-card) !important;
        color: var(--accent-pink) !important;
    }

    /* ── Dividers ── */
    hr {
        border-color: var(--border) !important;
    }

    /* ── Info/Warning/Error boxes ── */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
    }

    /* ── Code blocks ── */
    code {
        background: var(--bg-secondary) !important;
        color: var(--accent-pink) !important;
        border-radius: 6px;
        padding: 2px 6px;
    }

    /* ── Captions ── */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--text-dim) !important;
    }

    /* ── Number inputs ── */
    [data-testid="stNumberInput"] input {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
    }

    /* ── JSON viewer ── */
    .react-json-view {
        background: var(--bg-secondary) !important;
        border-radius: 10px;
        padding: 12px;
    }

    /* ── Plotly charts background ── */
    .js-plotly-plot .plotly .main-svg {
        background: transparent !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb {
        background: var(--border-light);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
</style>
"""
```

---

## Step 2: แก้ `pages/1_Dashboard.py` — Metric Cards ใหม่

### แทนที่ `_metric_card()` ด้วย:

```python
def _metric_card(icon: str, label: str, value: str, color: str, sub: str = "") -> str:
    sub_html = f'<div style="font-size:0.75rem;color:#4A5568;margin-top:6px">{sub}</div>' if sub else ""
    return f"""
    <div style="
        background: linear-gradient(135deg, #1A2035 0%, #111827 100%);
        border: 1px solid #1E2A45;
        border-left: 3px solid {color};
        border-radius: 14px;
        padding: 22px 20px;
        height: 100%;
        transition: transform 0.15s, box-shadow 0.15s;
    ">
        <div style="
            font-size: 0.72rem;
            color: #8892A8;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 600;
            margin-bottom: 10px;
        ">
            {icon} {label}
        </div>
        <div style="
            font-size: 2.2rem;
            font-weight: 800;
            color: #E8ECF4;
            line-height: 1.1;
            letter-spacing: -0.02em;
        ">
            {value}
        </div>
        {sub_html}
    </div>
    """
```

### แก้สี metric cards — ใช้สี semantic:

```python
# Row 1
with c1:
    st.markdown(_metric_card("👥", "ผู้ใช้งาน", str(stats["active_users"]),
        "#00B4D8", "ล็อกอินใน 24 ชม."), unsafe_allow_html=True)
with c2:
    st.markdown(_metric_card("🆕", "สมัครใหม่", str(stats["new_users"]),
        "#7B2FFF", "วันนี้"), unsafe_allow_html=True)
with c3:
    st.markdown(_metric_card("💰", "รายรับ (เติมเงิน)", f"฿{stats['topup_thb']:,}",
        "#00E396", "เงินจริงที่ลูกค้าเติมวันนี้"), unsafe_allow_html=True)
with c4:
    st.markdown(_metric_card("📊", "รายได้รับรู้", f"฿{stats['recognized_thb']:,.2f}",
        "#FF00CC", f"เครดิตที่ใช้ ÷ {stats['exchange_rate']} = บาท"), unsafe_allow_html=True)
```

### แก้ Alert cards — ใน dark theme:

```python
# Pending slips alert
if pending_slips > 0:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(254,176,25,0.08), rgba(254,176,25,0.03));
        border: 1px solid rgba(254,176,25,0.25);
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 14px;
    ">
        <span style="font-size:1.8rem">🧾</span>
        <div>
            <div style="font-weight:700;color:#FEB019;font-size:1rem">{pending_slips} สลิปรอตรวจสอบ</div>
            <div style="font-size:0.82rem;color:#8892A8;margin-top:2px">ไปที่หน้า "สลิปเติมเงิน" เพื่อดำเนินการ</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Stuck jobs alert
if stuck_jobs > 0:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(255,69,96,0.08), rgba(255,69,96,0.03));
        border: 1px solid rgba(255,69,96,0.25);
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 14px;
    ">
        <span style="font-size:1.8rem">⚠️</span>
        <div>
            <div style="font-weight:700;color:#FF4560;font-size:1rem">{stuck_jobs} งานค้าง (RESERVED)</div>
            <div style="font-size:0.82rem;color:#8892A8;margin-top:2px">งานหมดอายุ — ไปที่หน้า "ตรวจสอบงาน" เพื่อคืนเครดิต</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# All OK
if pending_slips == 0 and stuck_jobs == 0:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(0,227,150,0.08), rgba(0,227,150,0.03));
        border: 1px solid rgba(0,227,150,0.25);
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 14px;
    ">
        <span style="font-size:1.8rem">✅</span>
        <div style="font-weight:600;color:#00E396">ไม่มีรายการรอดำเนินการ — ระบบทำงานปกติ</div>
    </div>
    """, unsafe_allow_html=True)
```

---

## Step 3: แก้ `utils/charts.py` — Dark Theme Charts

### แทนที่ `_base_layout()`:

```python
def _base_layout() -> dict:
    return dict(
        template="plotly_dark",
        height=340,
        margin=dict(l=50, r=20, t=10, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", size=12, color="#8892A8"),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=11, color="#4A5568"),
            linecolor="#1E2A45",
        ),
        yaxis=dict(
            gridcolor="rgba(30,42,69,0.6)",
            gridwidth=1,
            tickfont=dict(size=11, color="#4A5568"),
            linecolor="#1E2A45",
            zerolinecolor="#1E2A45",
        ),
        hoverlabel=dict(
            bgcolor="#1A2035",
            font_color="#E8ECF4",
            font_size=13,
            bordercolor="#2A3A5C",
        ),
        showlegend=False,
    )
```

### Revenue chart — gradient fill:
```python
fig.add_trace(go.Scatter(
    x=df["date"], y=df["revenue"],
    mode="lines+markers",
    name="รายได้ (บาท)",
    line=dict(color="#00E396", width=2.5, shape="spline"),
    marker=dict(size=5, color="#00E396"),
    fill="tozeroy",
    fillcolor="rgba(0,227,150,0.08)",
    hovertemplate="<b>%{x|%d %b}</b><br>฿%{y:,.0f}<extra></extra>",
))
```

### User growth chart — accent color bars:
```python
fig.add_trace(go.Bar(
    x=df["date"], y=df["new_users"],
    name="ผู้ใช้ใหม่",
    marker=dict(
        color="rgba(123,47,255,0.7)",
        line=dict(color="#7B2FFF", width=1),
        cornerradius=6,
    ),
    hovertemplate="<b>%{x|%d %b}</b><br>%{y} คน<extra></extra>",
))
```

---

## Step 4: แก้ `app.py` — Home Page ใหม่

### Navigation cards — dark theme:

```python
def _nav_card(icon: str, title: str, desc: str, color: str) -> str:
    return f"""
    <div style="
        background: linear-gradient(135deg, #1A2035 0%, #111827 100%);
        border: 1px solid #1E2A45;
        border-radius: 14px;
        padding: 24px 20px;
        margin-bottom: 12px;
        transition: all 0.15s;
        cursor: pointer;
    "
    onmouseover="this.style.borderColor='rgba(255,0,204,0.3)'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 16px rgba(0,0,0,0.3)'"
    onmouseout="this.style.borderColor='#1E2A45'; this.style.transform='translateY(0)'; this.style.boxShadow='none'"
    >
        <div style="font-size:1.8rem;margin-bottom:10px">{icon}</div>
        <div style="font-weight:700;font-size:1.05rem;color:#E8ECF4;margin-bottom:4px">{title}</div>
        <div style="color:#8892A8;font-size:0.85rem;line-height:1.4">{desc}</div>
    </div>
    """

# Navigation
_pages = [
    ("📊", "แดชบอร์ด", "สถิติวันนี้ รายได้ การเติบโตผู้ใช้", "#00B4D8"),
    ("👥", "ผู้ใช้งาน", "จัดการผู้ใช้ เครดิต ระงับ/เปิดบัญชี", "#7B2FFF"),
    ("🧾", "สลิปเติมเงิน", "ตรวจสอบ อนุมัติ/ปฏิเสธสลิป", "#FEB019"),
    ("⚙️", "ตรวจสอบงาน", "ดูสถานะงาน คืนเครดิตงานค้าง", "#00E396"),
    ("🔧", "ตั้งค่าระบบ", "เวอร์ชัน อัตราเครดิต พรอมต์ คำต้องห้าม", "#FF00CC"),
    ("📋", "บันทึกระบบ", "เหตุการณ์สำคัญ ติดตามพฤติกรรม", "#8892A8"),
    ("🎁", "โปรโมชั่น", "จัดการแคมเปญ โบนัส ส่วนลด", "#FFD700"),
]

cols = st.columns(3)
for i, (icon, title, desc, color) in enumerate(_pages):
    with cols[i % 3]:
        st.markdown(_nav_card(icon, title, desc, color), unsafe_allow_html=True)
```

---

## Step 5: ปรับ Sidebar ใน `app.py`

```python
with st.sidebar:
    st.markdown("""
    <div style="
        text-align: center;
        padding: 16px 0 8px 0;
    ">
        <div style="
            font-size: 1.4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #FF00CC, #7B2FFF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        ">👁 BigEye Pro</div>
        <div style="
            font-size: 0.75rem;
            color: #4A5568;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-top: 4px;
        ">Admin Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    env = os.getenv("ENVIRONMENT", "development")
    env_color = "#00E396" if env == "production" else "#FEB019"
    st.markdown(f"""
    <div style="
        background: rgba(255,255,255,0.03);
        border: 1px solid #1E2A45;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            background: {env_color};
            margin-right: 6px;
        "></span>
        <span style="font-size:0.8rem;color:#8892A8">{env}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()
```

---

## สรุป

### ก่อน vs หลัง

| จุด | ก่อน | หลัง |
|:--|:--|:--|
| **พื้นหลัง** | ขาว Streamlit default | Dark `#0B0F19` |
| **Cards** | ขาว/เทาจืด | Dark cards + border-left สี semantic |
| **Buttons** | Streamlit default | Ghost buttons + gradient primary |
| **Charts** | Light theme | Dark theme + สีเข้ากับ accent |
| **Alerts** | ขาว/เหลือง/แดง | Dark translucent + border สี |
| **Tables** | Default dataframe | Dark table + colored headers |
| **Sidebar** | Default sidebar | Deep navy + gradient logo |
| **Navigation** | Card ขาว | Dark card + hover glow |

### วิธีสั่ง AI IDE

สั่งทีละไฟล์:
```
Prompt 1: "แก้ utils/theme.py — เปลี่ยน CSS ตาม Step 1 ใน redesign guide"
Prompt 2: "แก้ pages/1_Dashboard.py — เปลี่ยน metric cards + alerts ตาม Step 2"
Prompt 3: "แก้ utils/charts.py — เปลี่ยน chart theme ตาม Step 3"
Prompt 4: "แก้ app.py — เปลี่ยน home page + sidebar ตาม Step 4-5"
```

ทุก prompt ให้แนบไฟล์ redesign guide ด้วย
