from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "ticker",
    "name",
    "market",
    "prev_close",
    "value_score",
    "growth_early_score",
    "business_quality_score",
    "liquidity_support_score",
    "value_trap_risk_score",
    "stage",
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    reports_dir = root / "reports"

    latest_csv = data_dir / "latest.csv"
    latest_html = reports_dir / "latest.html"
    latest_md = reports_dir / "latest.md"

    hard_failures: list[str] = []
    warnings: list[str] = []

    for path in (latest_csv, latest_html, latest_md):
        if not path.exists() or path.stat().st_size == 0:
            hard_failures.append(f"missing_or_empty:{path.name}")

    if hard_failures:
        _print_result(hard_failures, warnings, None)
        return 1

    frame = pd.read_csv(latest_csv, encoding="utf-8-sig")
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing_columns:
        hard_failures.append(f"missing_columns:{','.join(missing_columns)}")
        _print_result(hard_failures, warnings, None)
        return 1

    row_count = len(frame)
    if row_count < 2000:
        hard_failures.append(f"row_count_too_small:{row_count}")

    missing_prev_close = int(frame["prev_close"].isna().sum())
    missing_scores = int(frame["value_score"].isna().sum() + frame["growth_early_score"].isna().sum())
    trap_warnings = int(frame["tags"].fillna("").astype(str).str.contains("가치 함정 주의").sum())
    low_liquidity = int(frame["tags"].fillna("").astype(str).str.contains("유동성 주의").sum())

    if missing_prev_close > row_count * 0.2:
        warnings.append(f"high_missing_prev_close:{missing_prev_close}")
    if missing_scores > 0:
        warnings.append(f"missing_scores:{missing_scores}")
    if trap_warnings == 0:
        warnings.append("no_value_trap_warnings")
    if low_liquidity == 0:
        warnings.append("no_liquidity_warnings")

    _print_result(hard_failures, warnings, frame)
    return 1 if hard_failures else 0


def _print_result(
    hard_failures: list[str],
    warnings: list[str],
    frame: pd.DataFrame | None,
) -> None:
    print("KRX verification report")
    if frame is not None:
        print(f"- rows: {len(frame)}")
        print(f"- latest ticker sample: {', '.join(frame['ticker'].astype(str).head(5).tolist())}")
    print(f"- hard_failures: {', '.join(hard_failures) if hard_failures else 'none'}")
    print(f"- warnings: {', '.join(warnings) if warnings else 'none'}")


if __name__ == "__main__":
    sys.exit(main())
