from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "pipeline" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from anomaly_detection import run_pipeline
from baseline import compute_expected_baselines, load_datasets, merge_context
from llm_interpretation import build_llm_response
from scoring import build_alert_candidates, compute_metric_z_scores


def _candidate_map(context_loaded: bool = True) -> dict[str, dict]:
    context_df, metrics_df = load_datasets(ROOT / "data")
    if context_loaded:
        merged = merge_context(metrics_df, context_df)
        baseline = compute_expected_baselines(merged)
    else:
        baseline = compute_expected_baselines(metrics_df, require_context=False)
    scored = compute_metric_z_scores(baseline)
    candidates = build_alert_candidates(scored, z_threshold=3.0)
    return {row["date"].strftime("%Y-%m-%d"): row for _, row in candidates.iterrows()}


def test_real_anomalies_in_the_dataset_are_detected() -> None:
    candidate_map = _candidate_map(context_loaded=True)

    assert "2025-11-05" in candidate_map
    nov_05 = candidate_map["2025-11-05"]
    nov_05_metrics = {item["metric"] for item in nov_05["anomalies"]}
    assert {"revenue_usd", "orders_count", "support_tickets"}.issubset(nov_05_metrics)

    for day in ["2025-10-20", "2025-10-21", "2025-10-22"]:
        row = candidate_map[day]
        metrics = {item["metric"] for item in row["anomalies"]}
        assert "support_tickets" in metrics
        assert "revenue_usd" not in metrics
        assert "orders_count" not in metrics

    for day in ["2025-10-28", "2025-10-29", "2025-10-30", "2025-10-31"]:
        row = candidate_map[day]
        metrics = {item["metric"] for item in row["anomalies"]}
        assert "customer_churn_rate" in metrics


def test_black_friday_is_not_flagged_when_context_is_loaded() -> None:
    candidate_map = _candidate_map(context_loaded=True)
    row = candidate_map["2025-11-28"]
    metrics = {item["metric"] for item in row["anomalies"]}

    assert "revenue_usd" not in metrics
    assert "orders_count" not in metrics
    assert "support_tickets" in metrics


def test_revenue_support_correlation_is_detected() -> None:
    df = pd.DataFrame([
        {
            "date": pd.Timestamp("2025-11-05"),
            "revenue_usd": 500.0,
            "orders_count": 20.0,
            "avg_order_value_usd": 25.0,
            "customer_churn_rate": 0.06,
            "support_tickets": 60.0,
            "ai_feature_usage_rate": 0.15,
            "revenue_usd_baseline": 2500.0,
            "revenue_usd_mad": 300.0,
            "orders_count_baseline": 200.0,
            "orders_count_mad": 25.0,
            "avg_order_value_usd_baseline": 100.0,
            "avg_order_value_usd_mad": 10.0,
            "customer_churn_rate_baseline": 0.02,
            "customer_churn_rate_mad": 0.005,
            "support_tickets_baseline": 15.0,
            "support_tickets_mad": 5.0,
            "ai_feature_usage_rate_baseline": 0.10,
            "ai_feature_usage_rate_mad": 0.02,
            "revenue_usd_expected": 2500.0,
            "orders_count_expected": 200.0,
            "avg_order_value_usd_expected": 100.0,
            "customer_churn_rate_expected": 0.02,
            "support_tickets_expected": 15.0,
            "ai_feature_usage_rate_expected": 0.10,
            "is_holiday": 0,
            "holiday_name": "",
            "is_release_day": 0,
            "marketing_campaign": "",
            "expected_revenue_multiplier": 1.0,
        }
    ])

    candidates = build_alert_candidates(df, z_threshold=3.0)
    assert not candidates.empty
    anomalies = candidates.iloc[0]["anomalies"]
    correlation = next((item for item in anomalies if item["metric"] == "revenue_support_correlation"), None)
    assert correlation is not None
    assert correlation["severity"] == "critical"
    assert correlation["is_expected"] is False


def test_churn_recovery_is_filtered_when_delta_is_near_zero() -> None:
    candidate_map = _candidate_map(context_loaded=True)
    for date in ["2025-11-14", "2025-11-17", "2025-12-21"]:
        row = candidate_map[date]
        metrics = {item["metric"] for item in row["anomalies"]}
        assert "customer_churn_rate" not in metrics


def test_weekend_orders_collapse_threshold_is_stricter() -> None:
    candidate_map = _candidate_map(context_loaded=True)
    for date in ["2025-10-18", "2025-10-19", "2025-10-25", "2025-10-26"]:
        row = candidate_map.get(date)
        if row is not None:
            metrics = {item["metric"] for item in row["anomalies"]}
            assert "orders_count" not in metrics

    nov_05 = candidate_map["2025-11-05"]
    metrics = {item["metric"] for item in nov_05["anomalies"]}
    assert "orders_count" in metrics


def test_black_friday_support_spike_is_marked_expected() -> None:
    alerts = run_pipeline(ROOT / "data")
    black_friday = [alert for alert in alerts if alert["date"] == "2025-11-28"]
    assert black_friday
    assert any(alert.get("is_expected") is True for alert in black_friday)


def test_black_friday_is_flagged_without_context() -> None:
    candidate_map = _candidate_map(context_loaded=False)
    row = candidate_map["2025-11-28"]
    metrics = {item["metric"] for item in row["anomalies"]}

    assert "revenue_usd" in metrics
    assert "orders_count" in metrics


def test_ai_feature_usage_spike_in_december_is_detected() -> None:
    candidate_map = _candidate_map(context_loaded=True)
    december_dates = [date for date in candidate_map if date.startswith("2025-12")]
    assert december_dates

    detected = []
    for date in december_dates:
        row = candidate_map[date]
        metrics = {item["metric"] for item in row["anomalies"]}
        if "ai_feature_usage_rate" in metrics:
            detected.append(date)

    assert detected
    assert any(date in detected for date in ["2025-12-10", "2025-12-11", "2025-12-12"])


def test_alert_schema_matches_spec() -> None:
    alerts = run_pipeline(ROOT / "data")
    assert alerts
    alert = alerts[0]

    required_fields = {
        "date",
        "anomaly_type",
        "severity",
        "confidence",
        "score",
        "expected_value",
        "actual_value",
        "delta",
        "context",
        "root_cause_hypotheses",
        "llm_summary",
        "related_metrics",
    }
    assert required_fields.issubset(alert.keys())
    assert isinstance(alert["context"], dict)
    assert isinstance(alert["related_metrics"], list)
    assert bool(alert["llm_summary"])


def test_llm_summary_uses_anthropic_api_when_environment_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            payload = {
                "content": [
                    {
                        "type": "text",
                        "text": '{"summary": "Anthropic summary", "likely_cause": "Ops issue", "confidence": 0.91, "recommended_actions": ["Review"], "alert_type": "ops", "evidence_summary": ["Checked"]}',
                    }
                ]
            }
            return __import__("json").dumps(payload).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = {k.lower(): v for k, v in request.headers.items()}
        return DummyResponse()

    import llm_interpretation

    monkeypatch.setattr(llm_interpretation.request, "urlopen", fake_urlopen)

    alert = {
        "date": "2025-11-05",
        "anomaly_type": "revenue_shortfall",
        "severity": "high",
        "confidence": 0.9,
        "expected_value": 22000,
        "actual_value": 2524,
        "delta": -19476,
        "related_metrics": ["revenue_usd", "support_tickets"],
        "context": {"holiday": False, "marketing_campaign": "November Sale"},
    }

    response = build_llm_response(alert)
    assert response["summary"] == "Anthropic summary"
    assert "api.anthropic.com" in captured["url"]
    assert captured["headers"]["x-api-key"] == "test-key"


def test_missing_context_halts_the_pipeline(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    metrics_source = ROOT / "data" / "ecommerce_dataset.csv"
    metrics_path = data_dir / "ecommerce_dataset.csv"
    metrics_path.write_text(metrics_source.read_text(), encoding="utf-8")

    with pytest.raises((FileNotFoundError, ValueError)):
        run_pipeline(data_dir)


if __name__ == "__main__":
    pytest.main([str(Path(__file__).resolve()), "-q"])
