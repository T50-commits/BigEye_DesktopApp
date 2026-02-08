"""
BigEye Pro Admin — Chart Helpers
Plotly chart builders for the dashboard.
"""
import plotly.graph_objects as go
import pandas as pd


def revenue_chart(data: list[dict]) -> go.Figure:
    """Line chart for daily revenue (last 30 days).
    data: list of {"date": "2026-02-01", "revenue": 800}
    """
    if not data:
        fig = go.Figure()
        fig.add_annotation(text="No revenue data", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="#888"))
        fig.update_layout(_base_layout("Revenue (THB)"))
        return fig

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["revenue"],
        mode="lines+markers",
        line=dict(color="#00E396", width=2),
        marker=dict(size=6),
        fill="tozeroy",
        fillcolor="rgba(0,227,150,0.1)",
    ))
    fig.update_layout(_base_layout("Revenue (THB)"))
    return fig


def user_growth_chart(data: list[dict]) -> go.Figure:
    """Bar chart for new user registrations (last 30 days).
    data: list of {"date": "2026-02-01", "new_users": 5}
    """
    if not data:
        fig = go.Figure()
        fig.add_annotation(text="No user data", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="#888"))
        fig.update_layout(_base_layout("New Users"))
        return fig

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date"], y=df["new_users"],
        marker_color="#775DD0",
    ))
    fig.update_layout(_base_layout("New Users"))
    return fig


def _base_layout(title: str) -> dict:
    return dict(
        title=title,
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=20, t=40, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )
