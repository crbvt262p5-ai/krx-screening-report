from __future__ import annotations

import json
import shutil
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "data"
SITE_DIR = BASE_DIR / "site"
SITE_REPORTS_DIR = SITE_DIR / "reports"
SITE_DATA_DIR = SITE_DIR / "data"


def _latest_report_date() -> str:
    dated_reports = sorted(REPORTS_DIR.glob("daily_*.html"))
    if dated_reports:
        return dated_reports[-1].stem.replace("daily_", "")
    raise FileNotFoundError("No daily HTML report found. Run the screening pipeline first.")


def _copy_if_exists(source: Path, target: Path) -> None:
    if source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _write_history(report_date: str) -> None:
    dated_html = sorted(REPORTS_DIR.glob("daily_*.html"), reverse=True)
    history = []
    for html_path in dated_html[:30]:
        date_text = html_path.stem.replace("daily_", "")
        history.append(
            {
                "date": date_text,
                "html": f"reports/{html_path.name}",
                "markdown": f"reports/daily_{date_text}.md",
                "csv": f"data/screened_{date_text}.csv",
                "latest": date_text == report_date,
            }
        )
    (SITE_DIR / "history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    report_date = _latest_report_date()
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    latest_html = REPORTS_DIR / "latest.html"
    latest_md = REPORTS_DIR / "latest.md"
    latest_csv = DATA_DIR / "latest.csv"
    dated_html = REPORTS_DIR / f"daily_{report_date}.html"
    dated_md = REPORTS_DIR / f"daily_{report_date}.md"
    dated_csv = DATA_DIR / f"screened_{report_date}.csv"

    _copy_if_exists(latest_html if latest_html.exists() else dated_html, SITE_DIR / "index.html")
    _copy_if_exists(latest_html if latest_html.exists() else dated_html, SITE_DIR / "latest.html")
    _copy_if_exists(latest_md if latest_md.exists() else dated_md, SITE_DIR / "latest.md")
    _copy_if_exists(latest_csv if latest_csv.exists() else dated_csv, SITE_DIR / "latest.csv")

    _copy_if_exists(dated_html, SITE_REPORTS_DIR / f"daily_{report_date}.html")
    _copy_if_exists(dated_md, SITE_REPORTS_DIR / f"daily_{report_date}.md")
    _copy_if_exists(dated_csv, SITE_DATA_DIR / f"screened_{report_date}.csv")

    _write_history(report_date)

    manifest = {
        "latest_date": report_date,
        "index": "index.html",
        "latest_html": "latest.html",
        "latest_markdown": "latest.md",
        "latest_csv": "latest.csv",
    }
    (SITE_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Built Pages site at {SITE_DIR}")


if __name__ == "__main__":
    main()
