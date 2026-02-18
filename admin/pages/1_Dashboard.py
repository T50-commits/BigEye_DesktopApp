"""
BigEye Pro Admin — หน้าแดชบอร์ด
สถิติวันนี้, กราฟรายได้, การเติบโตผู้ใช้, รายการรอดำเนินการ
"""
import streamlit as st
from utils.auth import require_auth
require_auth()

from datetime import datetime, timedelta, timezone

from utils.firestore_client import (
    users_ref, jobs_ref, slips_ref, transactions_ref, daily_reports_ref,
    system_config_ref,
)
from utils.charts import revenue_chart, user_growth_chart
from utils.theme import inject_css
from utils.components import metric_card, alert_card, chart_card

inject_css()

# ── Page-specific CSS for grid layout ──
st.markdown("""
<style>
.mg{display:grid;gap:16px;margin-bottom:24px}
.mg4{grid-template-columns:repeat(4,1fr)}
.mg3{grid-template-columns:repeat(3,1fr)}
.mg2{grid-template-columns:repeat(2,1fr)}
.mc{background:#1a2035;border:1px solid #1e293b;border-radius:14px;padding:22px 20px;position:relative;overflow:hidden;transition:all .3s}
.mc:hover{border-color:#334155;transform:translateY(-2px);box-shadow:0 8px 40px rgba(0,0,0,.4)}
.mc .gw{position:absolute;top:-30px;right:-30px;width:80px;height:80px;border-radius:50%;filter:blur(40px);opacity:.15}
.mc .lb{font-size:.78rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;font-weight:600;display:flex;align-items:center;gap:8px}
.mc .vl{font-size:2rem;font-weight:800;line-height:1.1;margin-bottom:4px}
.mc .su{font-size:.75rem;color:#64748b;display:flex;align-items:center;gap:4px}
.tu{color:#10b981}.td{color:#ef4444}
.ar{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.ac{display:flex;align-items:center;gap:14px;padding:16px 20px;border-radius:14px;border:1px solid;transition:all .2s}
.ac.w{background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.25)}
.ac.d{background:rgba(239,68,68,.08);border-color:rgba(239,68,68,.25)}
.ac.s{background:rgba(16,185,129,.06);border-color:rgba(16,185,129,.2);grid-column:1/-1}
.ac .ai{font-size:1.6rem}
.ac .at .tt{font-weight:700;font-size:.95rem}
.ac .at .ds{font-size:.78rem;color:#64748b;margin-top:2px}
.ac .ab{margin-left:auto;padding:6px 14px;border-radius:8px;font-size:.78rem;font-weight:600;cursor:pointer;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.05);color:#94a3b8;transition:all .2s;text-decoration:none;display:inline-block}
.ac .ab:hover{background:rgba(255,255,255,.1);color:#f1f5f9}
.cr{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.cc{background:#1a2035;border:1px solid #1e293b;border-radius:14px;padding:24px}
.cc .ch{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.cc .cht{font-weight:700;font-size:1rem}
.cc .cp{font-size:.75rem;color:#64748b;padding:4px 10px;background:#0f1629;border-radius:8px;border:1px solid #1e293b}
.tb-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}
.tb-head .pt{font-size:1.25rem;font-weight:700;display:flex;align-items:center;gap:10px}
.tb-head .acts{display:flex;align-items:center;gap:12px}
.clk{font-family:'JetBrains Mono',monospace;font-size:.8rem;color:#64748b}
@media(max-width:1200px){.mg4{grid-template-columns:repeat(2,1fr)}}
@media(max-width:768px){.mg4,.mg3,.mg2,.ar,.cr{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)

# ── Helper: query Firestore with caching ──

@st.cache_data(ttl=60)
def load_today_stats():
    """Load today's key metrics from Firestore."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Active users (logged in within 24h)
    active_users = 0
    try:
        docs = users_ref().where("last_login", ">=", yesterday_start).stream()
        active_users = sum(1 for _ in docs)
    except Exception:
        pass

    # New users today
    new_users = 0
    try:
        docs = users_ref().where("created_at", ">=", today_start).stream()
        new_users = sum(1 for _ in docs)
    except Exception:
        pass

    # ── รายรับ (Top-up THB) — เงินจริงที่ลูกค้าเติมเข้ามาวันนี้ ──
    topup_thb = 0
    try:
        docs = list(slips_ref().where("status", "==", "VERIFIED").stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                topup_thb += d.get("amount_detected", 0)
    except Exception:
        pass

    # ── รายได้รับรู้ (Used credits → THB) — เครดิตที่ลูกค้าใช้จริงแปลงกลับเป็นบาท ──
    # actual_usage = เครดิตที่ใช้จริง, credit_rate = อัตราเครดิต/ไฟล์
    # เราแปลงกลับเป็นบาทด้วย exchange_rate (1 บาท = N เครดิต)
    recognized_thb = 0.0
    exchange_rate = 4
    try:
        cfg = system_config_ref().document("app_settings").get()
        if cfg.exists:
            exchange_rate = cfg.to_dict().get("exchange_rate", 4)
    except Exception:
        pass

    try:
        docs = list(jobs_ref().where("status", "==", "COMPLETED").stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                usage = d.get("actual_usage", 0)
                if usage > 0 and exchange_rate > 0:
                    recognized_thb += usage / exchange_rate
    except Exception:
        pass

    # Jobs today
    jobs_count = 0
    try:
        docs = list(jobs_ref().stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                jobs_count += 1
    except Exception:
        pass

    # Errors today (failed jobs)
    errors = 0
    try:
        docs = list(jobs_ref().where("status", "==", "FAILED").stream())
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("created_at")
            if ts and hasattr(ts, "timestamp") and ts >= today_start:
                errors += 1
    except Exception:
        pass

    return {
        "active_users": active_users,
        "new_users": new_users,
        "topup_thb": topup_thb,
        "recognized_thb": round(recognized_thb, 2),
        "exchange_rate": exchange_rate,
        "jobs": jobs_count,
        "errors": errors,
    }


@st.cache_data(ttl=300)
def load_daily_reports(days: int = 30):
    """Load daily reports for charts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    revenue_data = []
    user_data = []

    try:
        docs = (
            daily_reports_ref()
            .where("date", ">=", cutoff.strftime("%Y-%m-%d"))
            .order_by("date")
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
            date_str = d.get("date", "")
            revenue_data.append({"date": date_str, "revenue": d.get("revenue", 0)})
            user_data.append({"date": date_str, "new_users": d.get("new_users", 0)})
    except Exception:
        pass

    return revenue_data, user_data


@st.cache_data(ttl=60)
def load_pending_actions():
    """Load pending slips and stuck jobs."""
    pending_slips = 0
    stuck_jobs = 0

    try:
        docs = slips_ref().where("status", "==", "PENDING").stream()
        pending_slips = sum(1 for _ in docs)
    except Exception:
        pass

    expire_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    try:
        docs = (
            jobs_ref()
            .where("status", "==", "RESERVED")
            .where("created_at", "<=", expire_cutoff)
            .stream()
        )
        stuck_jobs = sum(1 for _ in docs)
    except Exception:
        pass

    return pending_slips, stuck_jobs


# ── Render ──

stats = load_today_stats()
pending_slips, stuck_jobs = load_pending_actions()

# ── Header bar (like prototype) ──
now_local = datetime.now(timezone(timedelta(hours=7)))
thai_months = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
               "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
thai_year = now_local.year + 543
clock_str = f"{now_local.strftime('%H:%M:%S')} • {now_local.day:02d} {thai_months[now_local.month]} {thai_year}"

hdr_left, hdr_right = st.columns([3, 1])
with hdr_left:
    st.markdown(f"""
    <div class="tb-head">
        <div class="pt">📊 แดชบอร์ด</div>
        <div class="acts">
            <span class="clk">{clock_str}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
with hdr_right:
    if st.button("🔄 รีเฟรช", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Helper: build metric card as raw HTML (matching prototype .mc class) ──
def _mc(icon, label, value, color, sub_html=""):
    return f"""<div class="mc"><div class="gw" style="background:{color}"></div>
    <div class="lb">{icon} {label}</div>
    <div class="vl" style="color:{color}">{value}</div>
    <div class="su">{sub_html}</div></div>"""

# ── Row 1: Metric Cards (4 columns — CSS Grid) ──
total = stats["jobs"]
errors = stats["errors"]
err_pct = round(errors / total * 100, 1) if total > 0 else 0
success_rate = round(((total - errors) / total * 100), 1) if total > 0 else 100
rate_color = "#10b981" if success_rate >= 95 else "#f59e0b" if success_rate >= 80 else "#ef4444"

st.markdown(f"""
<div class="mg mg4">
    {_mc("👥", "ผู้ใช้งาน", f"{stats['active_users']:,}", "#3b82f6",
         f'<span class="tu">↑</span> ล็อกอินใน 24 ชม.')}
    {_mc("🆕", "สมัครใหม่", str(stats["new_users"]), "#8b5cf6",
         f'<span class="tu">↑ {stats["new_users"]}</span> วันนี้')}
    {_mc("💰", "รายรับ (เติมเงิน)", f"฿{stats['topup_thb']:,}", "#10b981",
         "เงินจริงที่ลูกค้าเติมวันนี้")}
    {_mc("📊", "รายได้รับรู้", f"฿{stats['recognized_thb']:,.2f}", "#06b6d4",
         f"เครดิตที่ใช้ ÷ {stats['exchange_rate']} = บาท")}
</div>
""", unsafe_allow_html=True)

# ── Row 2: Jobs (3 columns — CSS Grid) ──
st.markdown(f"""
<div class="mg mg3">
    {_mc("⚙️", "งานทั้งหมด", str(total), "#f59e0b", "วันนี้")}
    {_mc("❌", "งานผิดพลาด", str(errors), "#ef4444",
         f'<span class="td">{err_pct}%</span> error rate')}
    {_mc("✅", "อัตราสำเร็จ", f"{success_rate}%", rate_color, "เสถียร")}
</div>
""", unsafe_allow_html=True)

# ── Alerts (CSS Grid 2 columns) ──
if pending_slips > 0 or stuck_jobs > 0:
    alert_html = '<div class="ar">'
    if pending_slips > 0:
        alert_html += f"""
        <div class="ac w">
            <div class="ai">🧾</div>
            <div class="at">
                <div class="tt" style="color:#fbbf24">{pending_slips} สลิปรอตรวจสอบ</div>
                <div class="ds">ไปที่หน้า "สลิปเติมเงิน" เพื่อดำเนินการ</div>
            </div>
            <span class="ab">ดูสลิป →</span>
        </div>"""
    if stuck_jobs > 0:
        alert_html += f"""
        <div class="ac d">
            <div class="ai">⚠️</div>
            <div class="at">
                <div class="tt" style="color:#f87171">{stuck_jobs} งานค้าง (RESERVED)</div>
                <div class="ds">งานหมดอายุ — คืนเครดิตให้ผู้ใช้</div>
            </div>
            <span class="ab">ดูงาน →</span>
        </div>"""
    alert_html += '</div>'
    st.markdown(alert_html, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="ar">
        <div class="ac s">
            <div class="ai">✅</div>
            <div class="at">
                <div class="tt" style="color:#34d399">ระบบทำงานปกติ</div>
                <div class="ds">ไม่มีรายการรอดำเนินการ</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Charts (use st.columns for Plotly, but wrap in card styling) ──
revenue_data, user_data = load_daily_reports()

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("""
    <div style="background:#1a2035;border:1px solid #1e293b;border-radius:14px;padding:20px 24px 8px 24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-weight:700;font-size:1rem">💰 รายได้ (30 วันล่าสุด)</span>
            <span style="font-size:.75rem;color:#64748b;padding:4px 10px;background:#0f1629;border-radius:8px;border:1px solid #1e293b">30 วัน</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(revenue_chart(revenue_data), use_container_width=True)

with col_right:
    st.markdown("""
    <div style="background:#1a2035;border:1px solid #1e293b;border-radius:14px;padding:20px 24px 8px 24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-weight:700;font-size:1rem">👥 ผู้ใช้ใหม่ (30 วันล่าสุด)</span>
            <span style="font-size:.75rem;color:#64748b;padding:4px 10px;background:#0f1629;border-radius:8px;border:1px solid #1e293b">30 วัน</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(user_growth_chart(user_data), use_container_width=True)
