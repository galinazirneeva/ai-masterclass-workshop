# methodology_critical: true
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

from llm_interpretation import build_llm_response


def severity_for_score(score: float, signal_count: int) -> str:
    """Map a combined anomaly score to a severity label."""
    if score >= 10 or (score >= 6 and signal_count >= 2):
        return "critical"
    if score >= 7 or signal_count >= 2:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def confidence_for_score(score: float, signal_count: int) -> float:
    """Convert anomaly magnitude and signal count into a 0-1 confidence value."""
    confidence = min(0.99, 0.45 + (score / 18.0) + (signal_count * 0.08))
    return round(max(0.0, min(confidence, 0.99)), 2)


def classify_metric_event(metric: str, z_score: float) -> str:
    """Return the anomaly category name for a metric-level event."""
    metric_map = {
        "revenue_usd": "revenue_surge" if z_score >= 0 else "revenue_shortfall",
        "orders_count": "orders_surge" if z_score >= 0 else "orders_collapse",
        "avg_order_value_usd": "aov_surge" if z_score >= 0 else "aov_decline",
        "customer_churn_rate": "churn_deterioration" if z_score >= 0 else "churn_recovery",
        "support_tickets": "support_spike" if z_score >= 0 else "support_relief",
        "ai_feature_usage_rate": "ai_usage_spike" if z_score >= 0 else "ai_usage_drop",
    }
    return metric_map.get(metric, "metric_anomaly")


def build_alerts(candidate_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Rank candidate dates into alert records aligned with the specification output."""
    alerts: List[Dict[str, Any]] = []

    for _, row in candidate_df.iterrows():
        anomalies = row["anomalies"]
        if not anomalies:
            continue

        highest = max(abs(item["z_score"]) for item in anomalies)
        primary_metric = max(anomalies, key=lambda item: abs(item["z_score"]))
        score = float(row["combined_anomaly_score"])
        severity = severity_for_score(score, len(anomalies))
        confidence = confidence_for_score(score, len(anomalies))

        actual_metric = primary_metric["metric"]
        actual_z = float(primary_metric["z_score"])
        anomaly_type = classify_metric_event(actual_metric, actual_z)

        is_expected = (
            row.get("context", {}).get("holiday") is True
            or bool(str(row.get("context", {}).get("holiday_name", "")).strip())
            or bool(str(row.get("context", {}).get("marketing_campaign", "")).strip())
        ) and anomaly_type == "support_spike"

        revenue_item = next((item for item in anomalies if item["metric"] == "revenue_usd"), None)
        support_item = next((item for item in anomalies if item["metric"] == "support_tickets"), None)
        if revenue_item is not None and revenue_item["expected"] > 0 and float(revenue_item["actual"]) < 0.2 * float(revenue_item["expected"]):
            is_expected = False
        if support_item is not None and support_item["expected"] > 0 and float(support_item["actual"]) > 5.0 * float(support_item["expected"]):
            is_expected = False

        record = {
            "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
            "anomaly_type": anomaly_type,
            "severity": severity,
            "confidence": confidence,
            "score": round(score, 2),
            "expected_value": round(primary_metric["expected"], 2),
            "actual_value": round(float(primary_metric["actual"]), 2),
            "delta": round(float(primary_metric["delta"]), 2),
            "context": row["context"],
            "is_expected": is_expected,
            "root_cause_hypotheses": [
                "context-adjusted outlier relative to rolling median",
                "multiple metric pressure suggests operational disruption",
                "review supporting business context before action",
            ],
            "llm_summary": "",
            "related_metrics": [item["metric"] for item in anomalies],
        }

        llm_response = build_llm_response(record)
        record["llm_summary"] = llm_response["summary"]
        record["root_cause_hypotheses"] = llm_response["recommended_actions"]
        alerts.append(record)

    return alerts


__all__ = ["severity_for_score", "confidence_for_score", "classify_metric_event", "build_alerts"]
