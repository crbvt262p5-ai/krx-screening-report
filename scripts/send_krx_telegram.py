from __future__ import annotations

import html
import json
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _normalize_public_url(url: str) -> str:
    clean = url.strip().rstrip("/")
    if not clean:
        return ""
    if clean.endswith(".html"):
        return clean
    return f"{clean}/latest.html"


def _latest_report_date() -> str:
    dated_reports = sorted((BASE_DIR / "reports").glob("daily_*.html"))
    if not dated_reports:
        return "unknown"
    return dated_reports[-1].stem.replace("daily_", "")


def _load_run_status() -> dict[str, object]:
    path = BASE_DIR / "data" / "run_status.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _core_missing_count(frame: pd.DataFrame) -> int:
    core_fields = {
        "prev_close",
        "market_cap",
        "per",
        "pbr",
        "dividend_yield",
        "sales_3y",
        "op_income_3y",
        "net_income_3y",
    }
    total = 0
    if "missing_data" not in frame.columns:
        return total
    for value in frame["missing_data"].fillna(""):
        flags = {item for item in str(value).split("|") if item}
        if flags & core_fields:
            total += 1
    return total


def _slice_top(frame: pd.DataFrame, score_column: str, count: int = 5, exclude_flag: bool = False) -> pd.DataFrame:
    working = frame.copy()
    if exclude_flag and "excluded" in working.columns:
        excluded = working["excluded"].astype(str).str.lower().eq("true")
        working = working[~excluded]
    if score_column not in working.columns:
        return working.head(0)
    working[score_column] = pd.to_numeric(working[score_column], errors="coerce")
    return working.nlargest(count, score_column)


def _style_top(
    frame: pd.DataFrame,
    style_column: str,
    style_name: str,
    score_column: str,
    count: int = 3,
) -> pd.DataFrame:
    if style_column not in frame.columns:
        return frame.head(0)
    filtered = frame[frame[style_column].fillna("") == style_name].copy()
    if filtered.empty:
        return filtered
    filtered[score_column] = pd.to_numeric(filtered[score_column], errors="coerce")
    return filtered.nlargest(count, score_column)


def _special_dividend_watch(frame: pd.DataFrame, count: int = 3) -> pd.DataFrame:
    working = frame.copy()
    for column in ("dividend_yield_trailing", "dividend_yield_normalized"):
        if column not in working.columns:
            return working.head(0)
        working[column] = pd.to_numeric(working[column], errors="coerce")
    working = working[
        working["dividend_yield_trailing"].notna()
        & working["dividend_yield_normalized"].notna()
    ].copy()
    if working.empty:
        return working
    working["dividend_gap_pct"] = (
        working["dividend_yield_trailing"] - working["dividend_yield_normalized"]
    ).round(2)
    working = working[
        (working["dividend_gap_pct"] >= 2.0)
        | (working["dividend_yield_trailing"] >= working["dividend_yield_normalized"] * 1.8)
    ]
    if working.empty:
        return working
    return working.nlargest(count, "dividend_gap_pct")


def _format_row(row: pd.Series, score_column: str, include_style: bool = True) -> str:
    name = html.escape(str(row.get("name", "-")))
    ticker = html.escape(str(row.get("ticker", "-")))
    sector = str(row.get("sector", "") or "").strip()
    style = ""
    if include_style:
        if score_column == "value_score":
            style = str(row.get("value_style", "") or "")
        else:
            style = str(row.get("growth_style", "") or "")
    score = pd.to_numeric(row.get(score_column), errors="coerce")
    score_text = f"{score:.1f}" if pd.notna(score) else "-"
    parts = [f"<b>{name}</b> ({ticker})", f"score {score_text}"]
    if sector:
        parts.append(html.escape(sector))
    if style:
        parts.append(html.escape(style))
    tags = str(row.get("tags", "") or "").strip()
    if tags:
        parts.append(html.escape(tags.replace("|", ", ")))
    return " | ".join(parts)


def _format_dividend_watch(row: pd.Series) -> str:
    name = html.escape(str(row.get("name", "-")))
    ticker = html.escape(str(row.get("ticker", "-")))
    trailing = pd.to_numeric(row.get("dividend_yield_trailing"), errors="coerce")
    normalized = pd.to_numeric(row.get("dividend_yield_normalized"), errors="coerce")
    trailing_text = f"{trailing:.1f}%" if pd.notna(trailing) else "-"
    normalized_text = f"{normalized:.1f}%" if pd.notna(normalized) else "-"
    return f"<b>{name}</b> ({ticker}) | T {trailing_text} / N {normalized_text}"


def _section(title: str, rows: list[str]) -> list[str]:
    if not rows:
        return []
    return [f"<b>{html.escape(title)}</b>"] + rows + [""]


def main() -> None:
    load_dotenv(BASE_DIR / ".env")

    token = _require_env("KRX_TELEGRAM_BOT_TOKEN")
    chat_id = _require_env("KRX_TELEGRAM_CHAT_ID")
    public_url = _normalize_public_url(os.getenv("KRX_REPORT_PUBLIC_URL", ""))

    csv_path = BASE_DIR / "data" / "latest.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Latest CSV not found: {csv_path}")

    frame = pd.read_csv(csv_path)
    report_date = _latest_report_date()
    run_status = _load_run_status()

    excluded_count = int(frame["excluded"].astype(str).str.lower().eq("true").sum()) if "excluded" in frame.columns else 0
    core_missing = _core_missing_count(frame)

    mode = str(run_status.get("mode", "") or "").strip()
    trading_date = str(run_status.get("trading_date", "") or "").strip()
    status_lines: list[str] = []
    if mode == "cached_trading_date":
        status_lines.append("운영 모드: <b>캐시 fallback</b>")
        if trading_date:
            status_lines.append(f"기준 거래일: <b>{html.escape(trading_date)}</b>")
    elif mode == "live":
        status_lines.append("운영 모드: <b>라이브</b>")

    value_top = _slice_top(frame, "value_score", count=5, exclude_flag=True)
    growth_top = _slice_top(frame, "growth_early_score", count=5)
    dividend_compounder = _style_top(frame, "value_style", "Dividend Compounder", "value_score", count=3)
    growth_proven = _style_top(frame, "growth_style", "Growth Proven", "growth_early_score", count=3)
    special_watch = _special_dividend_watch(frame, count=3)

    lines: list[str] = [
        f"<b>KRX Daily Screening</b> {html.escape(report_date)}",
        *status_lines,
        f"전체 스캔 종목: <b>{len(frame):,}</b>",
        f"급등 제외 종목: <b>{excluded_count:,}</b>",
        f"핵심 데이터 부족: <b>{core_missing:,}</b>",
        "",
    ]
    lines += _section("Value Top 5", [_format_row(row, "value_score") for _, row in value_top.iterrows()])
    lines += _section("Growth Top 5", [_format_row(row, "growth_early_score") for _, row in growth_top.iterrows()])
    lines += _section(
        "Dividend Compounder",
        [_format_row(row, "value_score") for _, row in dividend_compounder.iterrows()],
    )
    lines += _section(
        "Growth Proven",
        [_format_row(row, "growth_early_score") for _, row in growth_proven.iterrows()],
    )
    lines += _section(
        "Special Dividend Watch",
        [_format_dividend_watch(row) for _, row in special_watch.iterrows()],
    )
    if public_url:
        lines += [f'<a href="{html.escape(public_url)}">최신 리포트 열기</a>']

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "\n".join(lines).strip(),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    response.raise_for_status()
    print("Telegram notification sent")


if __name__ == "__main__":
    main()
