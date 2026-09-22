from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from alert_ranking import build_alerts
from baseline import compute_expected_baselines, load_datasets, merge_context
from scoring import build_alert_candidates, compute_metric_z_scores


def run_pipeline(data_dir: str | Path) -> List[Dict[str, Any]]:
    """Run the full anomaly detection pipeline and return ranked alerts."""
    context_df, metrics_df = load_datasets(data_dir)
    merged_df = merge_context(metrics_df, context_df)
    baseline_df = compute_expected_baselines(merged_df)
    z_scored_df = compute_metric_z_scores(baseline_df)
    candidate_df = build_alert_candidates(z_scored_df, z_threshold=3.0)
    alerts = build_alerts(candidate_df)
    return alerts


def main() -> None:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    alerts = sorted(run_pipeline(data_dir), key=lambda alert: alert["date"])
    print(json.dumps(alerts, indent=2))


if __name__ == "__main__":
    main()
