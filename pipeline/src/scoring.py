# methodology_critical: true
from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd

from baseline import METRIC_COLUMNS, robust_z_score


METRIC_Z_THRESHOLDS = {
    "revenue_usd": 3.2,
    "orders_count": 4.0,
    "avg_order_value_usd": 4.0,
    "customer_churn_rate": 4.0,
    "support_tickets": 3.0,
    "ai_feature_usage_rate": 5.0,
}


def compute_metric_z_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add robust z-score columns to the merged dataset."""
    result = df.copy()
    for metric in METRIC_COLUMNS:
        result[f"z_{metric}"] = result.apply(
            lambda row: robust_z_score(
                row[metric],
                row[f"{metric}_baseline"],
                row[f"{metric}_mad"],
            ),
            axis=1,
        )
    return result


def compute_combined_anomaly_score(row: pd.Series) -> float:
    """Aggregate the metric-level z-scores into a single daily anomaly score."""
    weights = {
        "revenue_usd": 1.5,
        "orders_count": 1.3,
        "avg_order_value_usd": 0.9,
        "customer_churn_rate": 1.4,
        "support_tickets": 1.2,
        "ai_feature_usage_rate": 0.9,
    }

    score = 0.0
    for metric in METRIC_COLUMNS:
        z_value = float(row.get(f"z_{metric}", 0.0) or 0.0)
        score += abs(z_value) * weights.get(metric, 1.0)
    return score


def build_alert_candidates(df: pd.DataFrame, z_threshold: float = 3.0) -> pd.DataFrame:
    """Create a candidate list of dates and metric signals while processing the full date range."""
    result = df.copy().sort_values("date").reset_index(drop=True)
    result["combined_anomaly_score"] = result.apply(compute_combined_anomaly_score, axis=1)

    candidate_rows = []
    for _, row in result.iterrows():
        anomalies = []
        campaign_active = bool(str(row.get("marketing_campaign", "")).strip()) or bool(row.get("is_holiday", 0))
        for metric in METRIC_COLUMNS:
            z_score = float(row.get(f"z_{metric}", 0.0) or 0.0)
            threshold = METRIC_Z_THRESHOLDS.get(metric, z_threshold)
            if abs(z_score) < threshold:
                continue

            if metric in {"revenue_usd", "orders_count"} and campaign_active:
                expected = float(row.get(f"{metric}_expected", 0.0) or 0.0)
                actual = float(row.get(metric, 0.0) or 0.0)
                if expected > 0 and 0.5 <= (actual / expected) <= 2.0:
                    continue

            if metric == "customer_churn_rate" and z_score < 0:
                delta = float(row[metric] - row[f"{metric}_expected"])
                if abs(delta) <= 0.01:
                    continue

            if metric == "orders_count" and z_score < 0:
                date_value = pd.to_datetime(row["date"])
                if getattr(date_value, "dayofweek", 0) >= 5:
                    continue
                delta = float(row[metric] - row[f"{metric}_expected"])
                if abs(delta) < 80:
                    continue

            direction = "high" if z_score >= 0 else "low"
            anomalies.append({
                "metric": metric,
                "z_score": z_score,
                "direction": direction,
                "actual": row[metric],
                "expected": row[f"{metric}_expected"],
                "delta": row[metric] - row[f"{metric}_expected"],
            })

        candidate_rows.append({
            "date": row["date"],
            "combined_anomaly_score": row["combined_anomaly_score"],
            "anomalies": anomalies,
            "context": {
                "holiday": bool(row.get("is_holiday", 0)),
                "holiday_name": row.get("holiday_name", ""),
                "marketing_campaign": row.get("marketing_campaign", ""),
                "is_release_day": bool(row.get("is_release_day", 0)),
                "expected_revenue_multiplier": float(row.get("expected_revenue_multiplier", 1.0) or 1.0),
            },
        })

    return pd.DataFrame(candidate_rows)


__all__ = ["compute_metric_z_scores", "compute_combined_anomaly_score", "build_alert_candidates", "METRIC_Z_THRESHOLDS"]
