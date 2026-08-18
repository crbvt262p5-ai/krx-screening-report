from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from krx_screening.models import EquitySnapshot
from krx_screening.scoring import _classify_theme


LIST_COLUMNS = {
    "news_keyword_hits",
    "important_news_items",
    "important_disclosures",
    "theme_evidence",
}

FLOAT_COLUMNS = {
    "avg_trading_value_20d",
    "avg_trading_value_60d",
    "market_cap",
    "business_quality_score",
    "tam_expansion_score",
    "theme_score",
}

TEXT_COLUMNS = {
    "sector",
    "industry",
    "theme",
    "sub_theme",
    "theme_confidence",
}


def _parse_list(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    if " | " in text:
        return [item.strip() for item in text.split(" | ") if item.strip()]
    if "|" in text:
        return [item.strip() for item in text.split("|") if item.strip()]
    return [text]


def _parse_float(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() == "nan":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _build_reference_map(data_dir: Path) -> dict[str, dict[str, object]]:
    sources = [data_dir / "latest.csv"]
    sources.extend(sorted(data_dir.glob("screened_*.csv"), reverse=True))
    reference: dict[str, dict[str, object]] = {}
    for path in sources:
        if not path.exists():
            continue
        frame = pd.read_csv(path, encoding="utf-8-sig")
        for row in frame.to_dict(orient="records"):
            ticker = str(row.get("ticker", "")).strip()
            if not ticker or ticker in reference:
                continue
            reference[ticker] = row
    return reference


def _snapshot_from_row(row: dict[str, object], fallback: dict[str, object]) -> EquitySnapshot:
    def pick(column: str) -> object:
        direct = row.get(column)
        if direct is not None and not (isinstance(direct, float) and pd.isna(direct)) and str(direct).strip() not in {"", "nan", "None"}:
            return direct
        return fallback.get(column)

    snapshot = EquitySnapshot(
        ticker=str(pick("ticker") or ""),
        market=str(pick("market") or "KOSPI"),
        name=str(pick("name") or ""),
    )
    snapshot.sector = _parse_text(pick("sector"))
    snapshot.industry = _parse_text(pick("industry"))
    snapshot.avg_trading_value_20d = _parse_float(pick("avg_trading_value_20d"))
    snapshot.avg_trading_value_60d = _parse_float(pick("avg_trading_value_60d"))
    snapshot.market_cap = _parse_float(pick("market_cap"))
    snapshot.business_quality_score = _parse_float(pick("business_quality_score")) or 0.0
    snapshot.tam_expansion_score = _parse_float(pick("tam_expansion_score")) or 0.0
    snapshot.news_keyword_hits = _parse_list(pick("news_keyword_hits"))
    snapshot.important_news_items = _parse_list(pick("important_news_items"))
    snapshot.important_disclosures = _parse_list(pick("important_disclosures"))
    return snapshot


def _write_theme_fields(frame: pd.DataFrame, index: int, snapshot: EquitySnapshot) -> bool:
    updates = {
        "theme": snapshot.theme or "미분류",
        "sub_theme": snapshot.sub_theme or "",
        "theme_score": snapshot.theme_score,
        "theme_confidence": snapshot.theme_confidence or "",
        "theme_gate_pass": bool(snapshot.theme_gate_pass),
        "theme_evidence": " | ".join(snapshot.theme_evidence),
    }
    changed = False
    for column, value in updates.items():
        previous = frame.at[index, column] if column in frame.columns else None
        if pd.isna(previous):
            previous = None
        if previous != value:
            frame.at[index, column] = value
            changed = True
    return changed


def backfill_history(data_dir: Path, dry_run: bool = False) -> list[tuple[str, int, int]]:
    reference_map = _build_reference_map(data_dir)
    results: list[tuple[str, int, int]] = []
    for path in sorted(data_dir.glob("screened_*.csv")):
        frame = pd.read_csv(path, encoding="utf-8-sig")
        for column in ["theme", "sub_theme", "theme_score", "theme_confidence", "theme_gate_pass", "theme_evidence"]:
            if column not in frame.columns:
                frame[column] = ""

        changed_rows = 0
        gated_rows = 0
        for index, row in enumerate(frame.to_dict(orient="records")):
            ticker = str(row.get("ticker", "")).strip()
            fallback = reference_map.get(ticker, {})
            snapshot = _snapshot_from_row(row, fallback)
            _classify_theme(snapshot)
            if snapshot.theme_gate_pass:
                gated_rows += 1
            if _write_theme_fields(frame, index, snapshot):
                changed_rows += 1

        results.append((path.name, changed_rows, gated_rows))
        if changed_rows and not dry_run:
            frame.to_csv(path, index=False, encoding="utf-8-sig")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill theme classification into historical screened CSV files.")
    parser.add_argument("--data-dir", default="data", help="Directory containing screened_*.csv files")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files; only report planned changes")
    args = parser.parse_args()

    results = backfill_history(Path(args.data_dir), dry_run=args.dry_run)
    for filename, changed_rows, gated_rows in results:
        print(f"{filename}: changed={changed_rows} theme_gate_pass={gated_rows}")


if __name__ == "__main__":
    main()
