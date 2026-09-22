# methodology_critical: true
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
import pandas as pd

METRIC_COLUMNS = [
    "revenue_usd",
    "orders_count",
    "avg_order_value_usd",
    "customer_churn_rate",
    "support_tickets",
    "ai_feature_usage_rate",
]


def load_datasets(data_dir: str | Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load business context and operational metrics from the project data folder."""
    data_dir = Path(data_dir)
    context_df = pd.read_csv(data_dir / "business_context.csv", parse_dates=["date"])
    metrics_df = pd.read_csv(data_dir / "ecommerce_dataset.csv", parse_dates=["date"])
    return context_df, metrics_df


def merge_context(metrics_df: pd.DataFrame, context_df: pd.DataFrame) -> pd.DataFrame:
    """Join business context with daily operational metrics."""
    merged = metrics_df.merge(context_df, on="date", how="left")
    merged = merged.sort_values("date").reset_index(drop=True)

    for column in ["holiday_name", "marketing_campaign"]:
        merged[column] = merged[column].fillna("")

    merged["is_holiday"] = pd.to_numeric(merged["is_holiday"], errors="coerce").fillna(0).astype(int)
    merged["is_release_day"] = pd.to_numeric(merged["is_release_day"], errors="coerce").fillna(0).astype(int)
    merged["expected_revenue_multiplier"] = pd.to_numeric(
        merged["expected_revenue_multiplier"], errors="coerce"
    ).fillna(1.0)

    return merged


def _rolling_median(series: pd.Series, window: int) -> pd.Series:
    previous = series.shift(1)
    return previous.rolling(window=window, min_periods=max(3, window // 2)).median()


def _rolling_mad(series: pd.Series, baseline: pd.Series, window: int) -> pd.Series:
    deviations = (series.shift(1) - baseline).abs()
    return deviations.rolling(window=window, min_periods=max(3, window // 2)).median().fillna(0.0)


def _context_multiplier(row: pd.Series) -> float:
    multiplier = float(row.get("expected_revenue_multiplier", 1.0) or 1.0)
    is_campaign = bool(str(row.get("marketing_campaign", "")).strip())
    is_holiday = bool(row.get("is_holiday", 0))
    if is_campaign:
        return max(multiplier, 1.2)
    if is_holiday:
        return max(multiplier, 1.1)
    return 1.0


def compute_expected_baselines(
    merged_df: pd.DataFrame, windows: Iterable[int] = (7, 30), require_context: bool = True
) -> pd.DataFrame:
    """Create rolling median baselines and expected values for the core metrics.

    By default, production use requires business context to avoid silently mis-scoring
    holiday and campaign periods. Tests may intentionally bypass the guard via
    require_context=False when simulating a no-context diagnostic path.
    """
    result = merged_df.copy()
    windows = tuple(windows)

    if require_context:
        required_columns = {
            "is_holiday",
            "holiday_name",
            "is_release_day",
            "marketing_campaign",
            "expected_revenue_multiplier",
        }
        missing = sorted(column for column in required_columns if column not in result.columns)
        if missing:
            raise ValueError(
                "Business context columns are missing; production anomaly scoring requires context. "
                f"Missing columns: {missing}"
            )

    if "is_holiday" not in result.columns:
        result["is_holiday"] = 0
    if "holiday_name" not in result.columns:
        result["holiday_name"] = ""
    if "is_release_day" not in result.columns:
        result["is_release_day"] = 0
    if "marketing_campaign" not in result.columns:
        result["marketing_campaign"] = ""
    if "expected_revenue_multiplier" not in result.columns:
        result["expected_revenue_multiplier"] = 1.0

    for metric in METRIC_COLUMNS:
        median_7 = _rolling_median(result[metric], windows[0])
        median_30 = _rolling_median(result[metric], windows[1])
        combined_median = median_7.combine_first(median_30).fillna(result[metric].median())

        mad_7 = _rolling_mad(result[metric], median_7, windows[0])
        mad_30 = _rolling_mad(result[metric], median_30, windows[1])
        combined_mad = mad_7.combine_first(mad_30).fillna(1.0)

        result[f"{metric}_baseline"] = combined_median
        result[f"{metric}_mad"] = combined_mad

        if metric in {"revenue_usd", "orders_count"}:
            multiplier = result.apply(lambda row: _context_multiplier(row), axis=1)
            result[f"{metric}_expected"] = (combined_median * multiplier).fillna(result[metric])
        else:
            result[f"{metric}_expected"] = combined_median.fillna(result[metric])

    result["baseline_window_days"] = 7
    return result


def robust_z_score(value: float, baseline: float, mad: float) -> float:
    """Compute a robust z-score using the rolling median and MAD."""
    if pd.isna(value) or pd.isna(baseline) or pd.isna(mad):
        return 0.0

    if mad == 0:
        return 0.0

    score = (value - baseline) / (1.4826 * mad)
    return float(score)


__all__ = [
    "METRIC_COLUMNS",
    "load_datasets",
    "merge_context",
    "compute_expected_baselines",
    "robust_z_score",
]
