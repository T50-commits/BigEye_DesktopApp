"""
BigEye Pro Admin — Chart Helpers
Plotly chart builders for the dashboard.
"""
import plotly.graph_objects as go
import pandas as pd


def revenue_chart(data: list[dict]) -> go.Figure:
    """Area chart for daily revenue (last 30 days)."""
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="ยังไม่มีข้อมูลรายได้",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="#94a3b8"),
        )
        fig.update_layout(_base_layout())
        return fig

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig = go.Figure()
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
    fig.update_layout(_base_layout())
    fig.update_yaxes(tickprefix="฿", tickformat=",")
    return fig


def user_growth_chart(data: list[dict]) -> go.Figure:
    """Bar chart for new user registrations (last 30 days)."""
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="ยังไม่มีข้อมูลผู้ใช้ใหม่",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="#94a3b8"),
        )
        fig.update_layout(_base_layout())
        return fig

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig = go.Figure()
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
    fig.update_layout(_base_layout())
    return fig


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
