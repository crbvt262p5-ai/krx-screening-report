from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class OutputHealth:
    row_count: int
    buy_review_count: int
    core_count: int
    per_coverage: float
    pbr_coverage: float
    sales_coverage: float
    publishable: bool
    reason: str


def assess_output_health(frame: pd.DataFrame) -> OutputHealth:
    row_count = len(frame)
    buy_review_count = 0
    core_count = 0
    if "recommendation_bucket" in frame.columns:
        buy_review_count = int((frame["recommendation_bucket"] == "실매수 검토").sum())
    if "core_bucket" in frame.columns:
        core_count = int(frame["core_bucket"].notna().sum())

    per_coverage = _coverage(frame, "per")
    pbr_coverage = _coverage(frame, "pbr")
    sales_coverage = _coverage(frame, "sales_3y")

    publishable = (
        row_count >= 2000
        and per_coverage >= 0.50
        and pbr_coverage >= 0.50
        and sales_coverage >= 0.50
        and (buy_review_count >= 5 or core_count >= 3)
    )

    if publishable:
        reason = "healthy"
    elif row_count < 2000:
        reason = "row_count_too_small"
    elif per_coverage < 0.50 or pbr_coverage < 0.50:
        reason = "valuation_coverage_too_low"
    elif sales_coverage < 0.50:
        reason = "financial_history_coverage_too_low"
    else:
        reason = "core_bucket_count_too_low"

    return OutputHealth(
        row_count=row_count,
        buy_review_count=buy_review_count,
        core_count=core_count,
        per_coverage=per_coverage,
        pbr_coverage=pbr_coverage,
        sales_coverage=sales_coverage,
        publishable=publishable,
        reason=reason,
    )


def _coverage(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns or frame.empty:
        return 0.0
    series = frame[column]
    if series.dtype == object:
        return float(series.fillna("").astype(str).str.strip().ne("").mean())
    return float(series.notna().mean())
