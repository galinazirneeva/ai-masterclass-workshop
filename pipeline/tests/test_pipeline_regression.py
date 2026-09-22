from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "pipeline" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from baseline import compute_expected_baselines, load_datasets, merge_context
from scoring import build_alert_candidates, compute_metric_z_scores


def _candidate_frame() -> pd.DataFrame:
    context_df, metrics_df = load_datasets(ROOT / "data")
    merged = merge_context(metrics_df, context_df)
    baseline = compute_expected_baselines(merged)
    scored = compute_metric_z_scores(baseline)
    candidates = build_alert_candidates(scored, z_threshold=3.0)
    return candidates


def test_full_date_range_is_processed() -> None:
    candidates = _candidate_frame()
    dates = pd.to_datetime(candidates["date"])

    assert len(dates) == 92
    assert dates.min().strftime("%Y-%m-%d") == "2025-10-01"
    assert dates.max().strftime("%Y-%m-%d") == "2025-12-31"


def test_required_anomalies_are_retained() -> None:
    candidates = _candidate_frame()
    candidate_dates = candidates.set_index("date")

    nov_05 = candidate_dates.loc["2025-11-05"] if "2025-11-05" in candidate_dates.index else None
    assert nov_05 is not None
    nov_05_metrics = {item["metric"] for item in nov_05["anomalies"]}
    assert "revenue_usd" in nov_05_metrics
    assert "orders_count" in nov_05_metrics
    assert "support_tickets" in nov_05_metrics

    for date in ["2025-10-20", "2025-10-21", "2025-10-22"]:
        row = candidate_dates.loc[date]
        metrics = {item["metric"] for item in row["anomalies"]}
        assert "support_tickets" in metrics
        assert "revenue_usd" not in metrics
        assert "orders_count" not in metrics

    for date in ["2025-10-28", "2025-10-29", "2025-10-30", "2025-10-31"]:
        row = candidate_dates.loc[date]
        metrics = {item["metric"] for item in row["anomalies"]}
        assert "customer_churn_rate" in metrics
        assert "revenue_usd" not in metrics
        assert "orders_count" not in metrics


def test_black_friday_revenue_spike_is_suppressed() -> None:
    candidates = _candidate_frame()
    candidate_dates = candidates.set_index("date")
    row = candidate_dates.loc["2025-11-28"]
    metrics = {item["metric"] for item in row["anomalies"]}

    assert "revenue_usd" not in metrics
    assert "orders_count" not in metrics
