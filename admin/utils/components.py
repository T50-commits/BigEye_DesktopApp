"""
BigEye Pro Admin — Reusable HTML Components
Dark theme component library for all admin pages.
"""
import streamlit as st


def metric_card(icon: str, label: str, value: str, color: str, sub: str = "", trend: str = "") -> str:
    """
    Render metric card with glow effect, large value, optional trend arrow.
    """
    trend_html = ""
    if trend:
        trend_color = "#34d399" if trend.startswith("\u2191") else "#f87171"
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


def alert_card(icon: str, title: str, desc: str, style: str = "warning",
               action_label: str = "", action_page: str = "") -> str:
    """
    Alert card with icon, title, description, optional action button.
    style: "warning" (yellow), "danger" (red), "success" (green)
    """
    colors = {
        "warning": ("rgba(245,158,11,0.08)", "rgba(245,158,11,0.25)", "#fbbf24"),
        "danger":  ("rgba(239,68,68,0.08)", "rgba(239,68,68,0.25)", "#f87171"),
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


def status_badge(status: str) -> str:
    """
    Status badge with colored dot.
    active/verified/completed = green, pending/reserved = yellow,
    rejected/failed/suspended = red, expired = gray, draft = purple
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


def user_avatar(name: str, email: str, size: int = 32) -> str:
    """Create avatar initials with gradient color based on email hash."""
    initials = ""
    if name and name != "\u2014":
        parts = name.split()
        initials = "".join(p[0].upper() for p in parts[:2])
    else:
        initials = email[:2].upper()

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
        display:inline-flex;align-items:center;justify-content:center;
        font-size:{size*0.38}px;font-weight:700;color:#fff;
        flex-shrink:0;
    ">{initials}</div>"""


def info_item(label: str, value: str, color: str = "", full_width: bool = False) -> str:
    """Small info card with label on top and value below."""
    style = f"color:{color}" if color else ""
    span = "grid-column:1/-1;" if full_width else ""
    return f"""
    <div style="padding:14px 16px;background:#1a2035;border-radius:8px;
        border:1px solid #1e293b;{span}">
        <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;
            color:#64748b;margin-bottom:4px;font-weight:600">{label}</div>
        <div style="font-size:1rem;font-weight:600;{style}">{value}</div>
    </div>"""


def transaction_item(description: str, date: str, amount: int) -> str:
    """Transaction list item with colored +/- amount."""
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


def data_section_start(title: str, tag: str = "") -> str:
    """Wrapper header for data sections (tables, lists)."""
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


def filter_pills(options: list, selected: str) -> None:
    """Render filter pills as a row of buttons."""
    cols = st.columns(len(options))
    for i, opt in enumerate(options):
        with cols[i]:
            btn_type = "primary" if opt == selected else "secondary"
            if st.button(opt, key=f"filter_{opt}", type=btn_type, use_container_width=True):
                st.session_state["filter"] = opt
                st.rerun()


def severity_dot(severity: str) -> str:
    """Colored dot with glow for log severity."""
    colors = {
        "INFO":     ("#3b82f6", "rgba(59,130,246,0.4)"),
        "WARNING":  ("#f59e0b", "rgba(245,158,11,0.4)"),
        "ERROR":    ("#ef4444", "rgba(239,68,68,0.4)"),
        "CRITICAL": ("#7c3aed", "rgba(124,58,237,0.4)"),
    }
    bg, shadow = colors.get(severity, ("#94a3b8", "rgba(148,163,184,0.4)"))
    return f"""<div style="width:10px;height:10px;border-radius:50%;
        background:{bg};box-shadow:0 0 8px {shadow};
        flex-shrink:0;margin-top:6px;display:inline-block"></div>"""


def config_card(title: str, content_html: str) -> str:
    """Wrapper card for system config sections."""
    return f"""
    <div style="background:#1a2035;border:1px solid #1e293b;
        border-radius:14px;padding:24px;">
        <h4 style="font-size:0.95rem;font-weight:700;margin-bottom:16px;
            display:flex;align-items:center;gap:8px">{title}</h4>
        {content_html}
    </div>"""


def blacklist_tag(word: str) -> str:
    """Red chip/tag for blacklist words."""
    return f"""<span style="display:inline-flex;align-items:center;gap:6px;
        padding:5px 12px;border-radius:20px;
        background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);
        font-size:0.78rem;color:#f87171">{word}
        <span style="cursor:pointer;opacity:0.6">\u00d7</span></span>"""


def chart_card(title: str) -> str:
    """Card wrapper for Plotly charts."""
    return f"""
    <div style="background:#1a2035;border:1px solid #1e293b;border-radius:14px;
        padding:18px 18px 8px 18px;margin-bottom:8px">
        <div style="font-weight:700;font-size:1rem;color:#f1f5f9;margin-bottom:4px">{title}</div>
    </div>
    """
