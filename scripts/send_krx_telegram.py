from __future__ import annotations

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


def _top_names(frame: pd.DataFrame, score_column: str, count: int = 5, exclude_flag: bool = False) -> str:
    working = frame.copy()
    if exclude_flag and "excluded" in working.columns:
        excluded = working["excluded"].astype(str).str.lower().eq("true")
        working = working[~excluded]
    if score_column not in working.columns:
        return "-"
    rows = working.nlargest(count, score_column)
    if rows.empty:
        return "-"
    return ", ".join(str(name) for name in rows["name"].head(count).tolist())


def main() -> None:
    load_dotenv(BASE_DIR / ".env")

    token = _require_env("KRX_TELEGRAM_BOT_TOKEN")
    chat_id = _require_env("KRX_TELEGRAM_CHAT_ID")
    public_url = os.getenv("KRX_REPORT_PUBLIC_URL", "").strip()

    csv_path = BASE_DIR / "data" / "latest.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Latest CSV not found: {csv_path}")

    frame = pd.read_csv(csv_path)
    report_date = "unknown"
    dated_reports = sorted((BASE_DIR / "reports").glob("daily_*.html"))
    if dated_reports:
        report_date = dated_reports[-1].stem.replace("daily_", "")

    excluded_count = int(frame["excluded"].astype(str).str.lower().eq("true").sum()) if "excluded" in frame.columns else 0
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
    core_missing = 0
    if "missing_data" in frame.columns:
        for value in frame["missing_data"].fillna(""):
            flags = {item for item in str(value).split("|") if item}
            if flags & core_fields:
                core_missing += 1

    value_names = _top_names(frame, "value_score", exclude_flag=True)
    growth_names = _top_names(frame, "growth_early_score")

    lines = [
        f"KRX daily screening {report_date}",
        f"전체 스캔 종목: {len(frame):,}",
        f"급등 제외 종목: {excluded_count:,}",
        f"핵심 데이터 부족: {core_missing:,}",
        "",
        f"Value 상위: {value_names}",
        f"Growth 상위: {growth_names}",
    ]
    if public_url:
        lines.extend(["", f"리포트 보기: {public_url}"])

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "\n".join(lines),
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    response.raise_for_status()
    print("Telegram notification sent")


if __name__ == "__main__":
    main()
