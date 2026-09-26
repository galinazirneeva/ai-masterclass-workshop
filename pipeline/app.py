"""
Anomaly Pipeline Dashboard
--------------------------
Read-only view of the gated anomaly detection pipeline (pipeline/src).
It does not detect anything itself: every alert comes from run_pipeline(),
the same code that passed Gate 1, Gate 2, Gate 3 and human sign-off.

Run with:
    streamlit run pipeline/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline" / "src"))

from anomaly_detection import run_pipeline  # noqa: E402
from baseline import METRIC_COLUMNS, compute_expected_baselines, load_datasets, merge_context  # noqa: E402

DATA_DIR = ROOT / "data"

# Same palette as the vibe coding dashboards, so the comparison on stage is fair.
COLOR_LINE = "#2a78d6"
COLOR_EXPECTED = "rgba(42, 120, 214, 0.45)"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_TEXT_SECONDARY = "#52514e"
COLOR_MUTED = "#898781"
SURFACE = "#fcfcfb"

SEVERITY_COLORS = {
    "critical": "#d03b3b",
    "high": "#e0751b",
    "medium": "#d4a72c",
    "low": "#9aa5b1",
}
EXPECTED_COLOR = "#898781"

METRIC_LABELS = {
    "revenue_usd": "Revenue (USD)",
    "orders_count": "Orders",
    "avg_order_value_usd": "Avg. Order Value (USD)",
    "customer_churn_rate": "Customer Churn Rate",
    "support_tickets": "Support Tickets",
    "ai_feature_usage_rate": "AI Feature Usage Rate",
}

st.set_page_config(
    page_title="Anomaly Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    f"""
    <style>
        .block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }}
        h1 {{ font-weight: 700; letter-spacing: -0.01em; }}
        .app-subtitle {{ color: {COLOR_TEXT_SECONDARY}; font-size: 0.95rem; margin-top: -0.6rem; margin-bottom: 1.6rem; }}
        div[data-testid="stMetric"] {{ background: {SURFACE}; border: 1px solid {COLOR_GRID}; border-radius: 10px; padding: 14px 18px 10px 18px; }}
        div[data-testid="stMetricLabel"] {{ color: {COLOR_TEXT_SECONDARY}; }}
        .section-label {{ color: {COLOR_MUTED}; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.06em; font-weight: 600; margin-top: 1.6rem; margin-bottom: 0.4rem; }}
        .badge {{ display: inline-block; border-radius: 999px; padding: 1px 10px; font-size: 0.78rem; font-weight: 600; }}
        .gates {{ color: {COLOR_TEXT_SECONDARY}; font-size: 0.85rem; background: {SURFACE}; border: 1px solid {COLOR_GRID}; border-radius: 10px; padding: 10px 14px; margin-bottom: 1rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Running the pipeline…")
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    # The dashboard needs the alerts, not LLM-written summaries: run without the API key.
    saved_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        alerts = pd.DataFrame(run_pipeline(DATA_DIR))
    finally:
        if saved_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved_key
    context_df, metrics_df = load_datasets(DATA_DIR)
    frame = compute_expected_baselines(merge_context(metrics_df, context_df))
    alerts["date"] = pd.to_datetime(alerts["date"])
    return alerts.sort_values("date"), frame


alerts, frame = load()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Anomaly Pipeline Dashboard")
st.markdown(
    f'<div class="app-subtitle">Context-aware anomaly detection across {len(METRIC_COLUMNS)} metrics · '
    f'{frame["date"].min():%b %d, %Y} – {frame["date"].max():%b %d, %Y}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="gates">Every alert below comes from <code>pipeline/src</code> — code that passed '
    "<b>Gate 1</b> (human-approved spec), <b>Gate 2</b> (tests), <b>Gate 3</b> (methodology review) "
    "and <b>human sign-off</b>. No sliders: thresholds are owned decisions, not knobs.</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
critical = alerts[alerts["severity"] == "critical"]
expected = alerts[alerts["is_expected"]]
kpi = st.columns(4)
kpi[0].metric("Days covered", f"{frame.shape[0]}")
kpi[1].metric("Alerts", f"{len(alerts)}", help="One alert per day with at least one anomalous metric.")
kpi[2].metric(
    "Critical",
    f"{len(critical)}",
    help="Critical = a multi-metric incident. " + ", ".join(f"{d:%b %d}" for d in critical["date"]),
)
kpi[3].metric("Explained by context", f"{len(expected)}", help="Shown for transparency, never escalated.")

if not critical.empty:
    lines = " · ".join(f"<b>{r.date:%b %d}</b> — {r.anomaly_type.replace('_', ' ')}" for r in critical.itertuples())
    st.markdown(
        f'<div style="margin-top:0.8rem"><span class="badge" style="background:rgba(208,59,59,0.10);'
        f'color:{SEVERITY_COLORS["critical"]}">CRITICAL</span>&nbsp; {lines}</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Charts — actual vs context-adjusted expected, alerts coloured by severity
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Metric detail</div>', unsafe_allow_html=True)


def metric_chart(metric: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=frame["date"], y=frame[f"{metric}_expected"], mode="lines", name="Expected (with context)",
        line=dict(width=1.5, color=COLOR_EXPECTED, dash="dot"), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=frame["date"], y=frame[metric], mode="lines", name=METRIC_LABELS[metric],
        line=dict(width=2, color=COLOR_LINE),
        hovertemplate="%{x|%b %d, %Y}<br>Value: %{y:,.3g}<extra></extra>",
    ))

    rows = alerts[alerts["related_metrics"].apply(lambda m: metric in m)]
    values = frame.set_index("date")[metric]
    for label, subset, color, symbol in (
        ("Explained by context", rows[rows["is_expected"]], EXPECTED_COLOR, "circle-open"),
        *[
            (sev.capitalize(), rows[(~rows["is_expected"]) & (rows["severity"] == sev)], col, "diamond")
            for sev, col in SEVERITY_COLORS.items()
        ],
    ):
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["date"], y=values.reindex(subset["date"]).values, mode="markers", name=label,
            marker=dict(size=12, color=color, symbol=symbol, line=dict(width=1.5, color=color if symbol == "circle-open" else "white")),
            customdata=subset[["anomaly_type", "severity"]],
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>%{x|%b %d, %Y}<br>Value: %{y:,.3g}<extra></extra>",
        ))

    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        hovermode="closest", font=dict(size=12, color="#0b0b0b"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor=COLOR_AXIS, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLOR_GRID, showline=False, zeroline=False)
    return fig


cols = st.columns(2)
for i, metric in enumerate(METRIC_COLUMNS):
    n = int(alerts["related_metrics"].apply(lambda m: metric in m).sum())
    with cols[i % 2]:
        head = st.columns([3, 1])
        head[0].markdown(f"**{METRIC_LABELS[metric]}**")
        if n:
            head[1].markdown(
                f'<span class="badge" style="background:rgba(42,120,214,0.10);color:{COLOR_LINE}">{n} alert{"s" if n > 1 else ""}</span>',
                unsafe_allow_html=True,
            )
        st.plotly_chart(metric_chart(metric), use_container_width=True, config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Alert table
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Alerts</div>', unsafe_allow_html=True)
table = pd.DataFrame({
    "Date": alerts["date"].dt.strftime("%Y-%m-%d"),
    "Type": alerts["anomaly_type"].str.replace("_", " "),
    "Severity": alerts["severity"],
    "Status": alerts["is_expected"].map({True: "Expected (context)", False: "Unexpected"}),
    "Metrics": alerts["related_metrics"].apply(lambda m: ", ".join(METRIC_LABELS.get(x, x) for x in m)),
})
st.dataframe(table, use_container_width=True, hide_index=True)

st.caption(
    "Expected = rolling median baseline adjusted by business context (holidays, campaigns). "
    "Detection logic lives in methodology-critical files and cannot change without human sign-off."
)
