from __future__ import annotations

import json
from datetime import date
from html import escape

import pandas as pd

from .config import Settings
from .models import EquitySnapshot


def write_outputs(settings: Settings, trading_date: date, equities: list[EquitySnapshot]) -> tuple[str, str]:
    settings.ensure_directories()
    csv_path = settings.data_dir / f"screened_{trading_date.isoformat()}.csv"
    md_path = settings.reports_dir / f"daily_{trading_date.isoformat()}.md"
    html_path = settings.reports_dir / f"daily_{trading_date.isoformat()}.html"
    latest_csv_path = settings.data_dir / "latest.csv"
    latest_md_path = settings.reports_dir / "latest.md"
    latest_html_path = settings.reports_dir / "latest.html"

    frame = pd.DataFrame([equity.to_record() for equity in equities]).sort_values(
        by=["final_score", "estimate_revision_score", "tam_expansion_score", "value_score"],
        ascending=False,
    )
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
    frame.to_csv(latest_csv_path, index=False, encoding="utf-8-sig")

    markdown = _build_markdown(settings, trading_date, equities, frame)
    html = _build_html(settings, trading_date, equities, frame)
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(markdown)
    with latest_md_path.open("w", encoding="utf-8") as handle:
        handle.write(markdown)
    with html_path.open("w", encoding="utf-8") as handle:
        handle.write(html)
    with latest_html_path.open("w", encoding="utf-8") as handle:
        handle.write(html)

    return str(md_path), str(csv_path)


def _build_markdown(
    settings: Settings,
    trading_date: date,
    equities: list[EquitySnapshot],
    frame: pd.DataFrame,
) -> str:
    working = _normalize_frame(frame)
    history = _load_recent_top_counts(settings, trading_date)
    summary = _summary_metrics(equities, working)
    buy_review = working[working["recommendation_bucket"] == "실매수 검토"].sort_values(
        by=["final_score", "estimate_revision_score", "business_quality_score"],
        ascending=False,
    )
    value_core = buy_review[buy_review["core_bucket"].fillna("") == "Value Core"]
    growth_core = buy_review[buy_review["core_bucket"].fillna("") == "Growth Core"]
    small_watch = working[working["recommendation_bucket"] == "소액 관찰"].sort_values(
        by=["final_score", "dividend_potential_score", "cashflow_quality_score"],
        ascending=False,
    )
    trap_watch = working[working["recommendation_bucket"] == "가치함정 경고"].sort_values(
        by=["value_trap_risk_score", "governance_warning_score", "final_score"],
        ascending=False,
    )
    value_top = _select_featured_rows(
        _value_table_ready(working[~working["excluded"]]),
        score_column="value_score",
        history_counts=history["value"],
        weekly_counts=history["value_weekly"],
        limit=20,
    )
    growth_universe = working[
        (~working["excluded"])
        & (working["recommendation_bucket"].fillna("") != "제외")
    ]
    growth_top = _select_featured_rows(
        growth_universe,
        score_column="growth_early_score",
        history_counts=history["growth"],
        weekly_counts=history["growth_weekly"],
        limit=20,
    )
    deep_value = _style_slice(value_top, "value_style", "Deep Value", 5)
    dividend_compounder = _style_slice(value_top, "value_style", "Dividend Compounder", 5)
    turnaround_value = _style_slice(value_top, "value_style", "Turnaround Value", 5)
    growth_proven = _style_slice(growth_top, "growth_style", "Growth Proven", 5)
    growth_speculative = _style_slice(growth_top, "growth_style", "Growth Speculative", 5)
    missed_leaders = working[
        (~working["excluded"])
        & (working["missed_leader_score"] >= 8.5)
    ].sort_values(
        by=["missed_leader_score", "final_score", "estimate_revision_score"],
        ascending=False,
    ).head(12)
    special_dividend_watch = _special_dividend_watchlist(working, limit=12)

    parts = [
        f"# KRX Daily Screening Report ({trading_date.isoformat()})",
        "",
        "## Summary",
        f"- Universe: {summary['total']} 종목",
        f"- Excluded by momentum rules: {summary['excluded']} 종목",
        f"- Missing finance/data flags: {summary['missing']} 종목",
        f"- Core missing fields: {summary['core_missing']} 종목",
        f"- 실매수 검토: {summary['buy_review']} 종목",
        f"- Value Core: {summary['value_core']} 종목",
        f"- Growth Core: {summary['growth_core']} 종목",
        f"- 소액 관찰: {summary['small_watch']} 종목",
        f"- 가치함정 경고: {summary['trap_watch']} 종목",
        f"- Historical cache assists: {summary['cache_rows']} 종목",
        "",
        "## Bucket Definitions",
        _bucket_definitions_markdown(),
        "",
        "## Quick Picks",
        "### Value Core",
        _bullet_summary(value_core.head(10), score_column="final_score"),
        "",
        "### Growth Core",
        _bullet_summary(growth_core.head(10), score_column="final_score"),
        "",
        "### 소액 관찰",
        _bullet_summary(small_watch.head(10), score_column="final_score"),
        "",
        "### 가치함정 경고",
        _bullet_summary(trap_watch.head(10), score_column="value_trap_risk_score"),
        "",
        "## Value Lenses",
        "### Deep Value",
        _bullet_summary(deep_value, score_column="final_score"),
        "",
        "### Dividend Compounder",
        _bullet_summary(dividend_compounder, score_column="final_score"),
        "",
        "### Turnaround Value",
        _bullet_summary(turnaround_value, score_column="final_score"),
        "",
        "## Growth Lenses",
        "### Growth Proven",
        _bullet_summary(growth_proven, score_column="growth_early_score"),
        "",
        "### Growth Speculative",
        _bullet_summary(growth_speculative, score_column="growth_early_score"),
        "",
        "## Missed Leader Detector",
        _bullet_summary(missed_leaders, score_column="missed_leader_score"),
        "",
        "## Top Value Bucket",
        _table_for_markdown(value_top, bucket="value"),
        "",
        "## Top Growth Early Bucket",
        _table_for_markdown(growth_top, bucket="growth"),
        "",
        "## Special Dividend Watch",
        _table_for_markdown(special_dividend_watch, bucket="special_dividend"),
        "",
        "## Notes",
        "- `excluded=true` 는 최근 급등 규칙 때문에 밸류 버킷에서 제외된 종목입니다.",
        "- `missing_data` 는 소스 부재 시 자동으로 붙는 플래그이며 파이프라인은 중단되지 않습니다.",
        "- `Core missing fields` 는 가격/시총/PER/PBR/배당/3개년 실적처럼 핵심 판단 항목 기준입니다.",
        "- 상단 추천은 최근 반복 노출, 업종 쏠림, 시총 쏠림을 완화한 `다변화 뷰` 기준입니다.",
        "- `Special Dividend Watch` 는 최근 실제 배당수익률이 평년화 배당수익률보다 과도하게 높아 착시 가능성이 있는 종목입니다.",
    ]
    return "\n".join(parts)


def _build_html(
    settings: Settings,
    trading_date: date,
    equities: list[EquitySnapshot],
    frame: pd.DataFrame,
) -> str:
    working = _normalize_frame(frame)
    history = _load_recent_top_counts(settings, trading_date)
    summary = _summary_metrics(equities, working)
    buy_review = working[working["recommendation_bucket"] == "실매수 검토"].sort_values(
        by=["final_score", "estimate_revision_score", "business_quality_score"],
        ascending=False,
    )
    value_core = buy_review[buy_review["core_bucket"].fillna("") == "Value Core"]
    growth_core = buy_review[buy_review["core_bucket"].fillna("") == "Growth Core"]
    small_watch = working[working["recommendation_bucket"] == "소액 관찰"].sort_values(
        by=["final_score", "dividend_potential_score", "cashflow_quality_score"],
        ascending=False,
    )
    trap_watch = working[working["recommendation_bucket"] == "가치함정 경고"].sort_values(
        by=["value_trap_risk_score", "governance_warning_score", "final_score"],
        ascending=False,
    )
    value_top = _select_featured_rows(
        _value_table_ready(working[~working["excluded"]]),
        score_column="value_score",
        history_counts=history["value"],
        weekly_counts=history["value_weekly"],
        limit=20,
    )
    growth_universe = working[
        (~working["excluded"])
        & (working["recommendation_bucket"].fillna("") != "제외")
    ]
    growth_top = _select_featured_rows(
        growth_universe,
        score_column="growth_early_score",
        history_counts=history["growth"],
        weekly_counts=history["growth_weekly"],
        limit=20,
    )
    deep_value = _style_slice(value_top, "value_style", "Deep Value", 4)
    dividend_compounder = _style_slice(value_top, "value_style", "Dividend Compounder", 4)
    turnaround_value = _style_slice(value_top, "value_style", "Turnaround Value", 4)
    growth_proven = _style_slice(growth_top, "growth_style", "Growth Proven", 4)
    growth_speculative = _style_slice(growth_top, "growth_style", "Growth Speculative", 4)
    missed_leaders = working[
        (~working["excluded"])
        & (working["missed_leader_score"] >= 8.5)
    ].sort_values(
        by=["missed_leader_score", "final_score", "estimate_revision_score"],
        ascending=False,
    ).head(8)
    special_dividend_watch = _special_dividend_watchlist(working, limit=12)
    full_list = _rank_for_explorer(
        working[
            (~working["excluded"])
            & (working["recommendation_bucket"].fillna("") != "제외")
        ],
        score_column="final_score",
        history_counts=history["value"],
        weekly_counts=history["value_weekly"],
    ).head(200)

    summary_cards = [
        ("전체 스캔 종목", f"{summary['total']:,}"),
        ("Value Core", f"{summary['value_core']:,}"),
        ("Growth Core", f"{summary['growth_core']:,}"),
        ("소액 관찰", f"{summary['small_watch']:,}"),
        ("가치함정 경고", f"{summary['trap_watch']:,}"),
        ("핵심 데이터 부족", f"{summary['core_missing']:,}"),
        ("캐시 보강 종목", f"{summary['cache_rows']:,}"),
        ("급등 제외 종목", f"{summary['excluded']:,}"),
    ]

    missing_counts = _top_missing_counts(working)
    definitions_html = _bucket_definitions_html()
    conviction_html = _conviction_grid(pd.concat([value_core.head(2), growth_core.head(2)], ignore_index=True))
    quick_review = _card_grid(buy_review.head(8), "final_score", accent="value")
    quick_watch = _card_grid(small_watch.head(8), "final_score", accent="growth")
    trap_watch_html = _card_grid(trap_watch.head(8), "value_trap_risk_score", accent="growth")
    memo_value_core_html = _memo_grid(value_core.head(5), title="Value Core", tone="value")
    memo_growth_core_html = _memo_grid(growth_core.head(5), title="Growth Core", tone="growth")
    memo_watch_html = _memo_grid(small_watch.head(5), title="소액 관찰", tone="growth")
    memo_trap_html = _memo_grid(trap_watch.head(5), title="가치함정 경고", tone="danger")
    deep_value_html = _card_grid(deep_value, "final_score", accent="value")
    dividend_compounder_html = _card_grid(dividend_compounder, "final_score", accent="value")
    turnaround_value_html = _card_grid(turnaround_value, "final_score", accent="value")
    growth_proven_html = _card_grid(growth_proven, "growth_early_score", accent="growth")
    growth_speculative_html = _card_grid(growth_speculative, "growth_early_score", accent="growth")
    missed_leader_html = _card_grid(missed_leaders, "missed_leader_score", accent="growth")
    special_watch_html = _html_table(special_dividend_watch, bucket="special_dividend")
    spotlight_html = _spotlight_strip(value_top, growth_top, missed_leaders)
    universe_json = json.dumps(_records_for_ui(full_list), ensure_ascii=False)
    value_table = _html_table(value_top, bucket="value")
    growth_table = _html_table(growth_top, bucket="growth")
    summary_html = "".join(
        f'<div class="metric-card"><span class="metric-label">{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in summary_cards[:4]
    )
    missing_html = "".join(
        f'<span class="chip">{escape(name)} {count}</span>' for name, count in missing_counts
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KRX Daily Screening {trading_date.isoformat()}</title>
  <style>
    :root {{
      --bg: #f5efe6;
      --panel: rgba(255,255,255,0.82);
      --panel-strong: #fffaf3;
      --text: #1c1a18;
      --muted: #6b6257;
      --line: rgba(44, 36, 27, 0.10);
      --value: #0f766e;
      --growth: #b45309;
      --danger: #b91c1c;
      --soft-green: #dff7ef;
      --soft-amber: #fff1d6;
      --soft-rose: #fde7e7;
      --soft-blue: #e4efff;
      --shadow: 0 24px 60px rgba(58, 42, 24, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Pretendard", "SUIT", "Apple SD Gothic Neo", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(227, 196, 125, 0.30), transparent 24%),
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.18), transparent 28%),
        linear-gradient(180deg, #f7f1e7 0%, #f3ebe0 45%, #efe7dc 100%);
      min-height: 100vh;
      scroll-behavior: smooth;
    }}
    .shell {{
      width: min(1380px, calc(100vw - 32px));
      margin: 24px auto 40px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(255,250,243,0.92), rgba(244,234,219,0.95));
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 28px;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -40px -60px auto;
      width: 240px;
      height: 240px;
      background: radial-gradient(circle, rgba(180,83,9,0.18), transparent 62%);
      pointer-events: none;
    }}
    .eyebrow {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 10px 0 6px;
      font-size: clamp(30px, 4vw, 52px);
      line-height: 1;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 15px;
      max-width: 780px;
      line-height: 1.6;
    }}
    .hero-layout {{
      display: block;
    }}
    .hero-copy {{
      position: relative;
      z-index: 1;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 22px;
    }}
    .metric-card {{
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid var(--line);
      backdrop-filter: blur(10px);
    }}
    .metric-card strong {{
      display: block;
      font-size: 28px;
      margin-top: 6px;
    }}
    .metric-card:nth-child(1) strong,
    .metric-card:nth-child(5) strong {{ color: #111827; }}
    .metric-card:nth-child(2) strong,
    .metric-card:nth-child(6) strong {{ color: var(--growth); }}
    .metric-card:nth-child(3) strong {{ color: var(--danger); }}
    .metric-card:nth-child(4) strong {{ color: var(--value); }}
    .metric-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .hero-note {{
      margin-top: 18px;
      padding: 16px 18px;
      border-radius: 20px;
      background: rgba(255,255,255,0.62);
      border: 1px solid rgba(44, 36, 27, 0.08);
      color: var(--muted);
      line-height: 1.65;
      font-size: 14px;
    }}
    .section {{
      margin-top: 20px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .section-head {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 18px;
    }}
    .section-head h2 {{
      margin: 0;
      font-size: 24px;
    }}
    .section-head span {{
      color: var(--muted);
      font-size: 14px;
    }}
    .memo-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .definition-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 16px;
    }}
    .definition-card {{
      border-radius: 18px;
      padding: 16px;
      background: rgba(255,255,255,0.64);
      border: 1px solid var(--line);
    }}
    .definition-card h3 {{
      margin: 0 0 8px;
      font-size: 18px;
    }}
    .definition-card p {{
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }}
    .definition-card ul {{
      margin: 0;
      padding-left: 18px;
      font-size: 13px;
      line-height: 1.65;
    }}
    .memo-panel {{
      border-radius: 22px;
      padding: 20px;
      border: 1px solid var(--line);
      background: rgba(255,250,243,0.9);
    }}
    .memo-panel.value {{ box-shadow: inset 0 0 0 1px rgba(15,118,110,0.08); }}
    .memo-panel.growth {{ box-shadow: inset 0 0 0 1px rgba(180,83,9,0.08); }}
    .memo-panel.danger {{ box-shadow: inset 0 0 0 1px rgba(185,28,28,0.08); }}
    .memo-panel h2 {{
      margin: 0 0 6px;
      font-size: 22px;
    }}
    .memo-panel > p {{
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }}
    .memo-card {{
      padding: 14px 0;
      border-top: 1px solid rgba(44, 36, 27, 0.08);
    }}
    .memo-card:first-of-type {{
      border-top: none;
      padding-top: 0;
    }}
    .memo-card h3 {{
      margin: 0;
      font-size: 20px;
    }}
    .memo-summary {{
      margin-top: 8px;
      color: var(--muted);
      line-height: 1.6;
      font-size: 13px;
    }}
    .memo-points {{
      margin: 10px 0 0;
      padding-left: 18px;
      line-height: 1.65;
      color: var(--text);
      font-size: 13px;
    }}
    .fold {{
      margin-top: 18px;
      border-top: 1px solid rgba(44, 36, 27, 0.08);
      padding-top: 18px;
    }}
    .fold summary {{
      cursor: pointer;
      font-weight: 700;
      font-size: 15px;
      color: var(--text);
      list-style: none;
    }}
    .fold summary::-webkit-details-marker {{
      display: none;
    }}
    .fold summary::after {{
      content: "열기";
      float: right;
      color: var(--muted);
      font-weight: 500;
      font-size: 13px;
    }}
    .fold[open] summary::after {{
      content: "닫기";
    }}
    .fold-body {{
      margin-top: 16px;
    }}
    .pick-card {{
      border-radius: 20px;
      padding: 16px;
      border: 1px solid var(--line);
      background: var(--panel-strong);
      min-height: 190px;
      display: flex;
      flex-direction: column;
    }}
    .conviction-card {{
      border-radius: 22px;
      padding: 20px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,250,243,0.98), rgba(250,245,237,0.92));
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    }}
    .conviction-card h3 {{
      margin: 0;
      font-size: 30px;
    }}
    .conviction-score {{
      display: inline-flex;
      margin-top: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--soft-green);
      color: var(--value);
      font-weight: 700;
      font-size: 15px;
    }}
    .conviction-metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .conviction-metrics div {{
      padding: 12px;
      border-radius: 16px;
      background: rgba(255,255,255,0.76);
      border: 1px solid var(--line);
    }}
    .conviction-metrics strong {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .conviction-metrics span {{
      display: block;
      margin-top: 4px;
      font-size: 22px;
      font-weight: 700;
    }}
    .reason-list {{
      margin: 16px 0 0;
      padding-left: 18px;
      line-height: 1.7;
    }}
    .decision {{
      margin-top: 16px;
      padding: 14px 16px;
      border-radius: 16px;
      background: rgba(15, 118, 110, 0.06);
      border: 1px solid rgba(15, 118, 110, 0.14);
    }}
    .pick-card.value {{ box-shadow: inset 0 0 0 1px rgba(15,118,110,0.08); }}
    .pick-card.growth {{ box-shadow: inset 0 0 0 1px rgba(180,83,9,0.08); }}
    .pick-card h3 {{
      margin: 0 0 8px;
      font-size: 20px;
    }}
    .pick-card .meta {{
      margin-top: 14px;
      flex: 1;
    }}
    .ticker {{
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .score-badge {{
      display: inline-flex;
      margin-top: 10px;
      padding: 6px 10px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 13px;
    }}
    .score-badge.value {{ background: var(--soft-green); color: var(--value); }}
    .score-badge.growth {{ background: var(--soft-amber); color: var(--growth); }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
      font-size: 13px;
      color: var(--muted);
    }}
    .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}
    .chip {{
      display: inline-flex;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(28,26,24,0.06);
      color: var(--text);
      font-size: 12px;
    }}
    .chip.strong {{
      background: var(--soft-blue);
      color: #1d4ed8;
      font-weight: 700;
    }}
    .controls {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    .controls input, .controls select {{
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fffdf8;
      padding: 12px 14px;
      font: inherit;
      min-width: 180px;
    }}
    .explorer-summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .explorer-summary .chip {{
      background: rgba(255,255,255,0.8);
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.68);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #fffaf3;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
    }}
    tr:hover td {{
      background: rgba(255,255,255,0.8);
    }}
    .stage {{
      display: inline-flex;
      padding: 4px 8px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 12px;
    }}
    .stage-초입 {{ background: var(--soft-green); color: var(--value); }}
    .stage-중간 {{ background: #e7eefb; color: #1d4ed8; }}
    .stage-후반 {{ background: var(--soft-amber); color: var(--growth); }}
    .stage-과열 {{ background: var(--soft-rose); color: var(--danger); }}
    .subtle {{
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 1100px) {{
      .metric-grid, .memo-grid, .card-grid, .definition-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 720px) {{
      .shell {{ width: min(100vw - 20px, 100%); margin: 12px auto 28px; }}
      .hero, .section {{ padding: 18px; border-radius: 20px; }}
      .metric-grid, .memo-grid, .card-grid, .definition-grid {{ grid-template-columns: 1fr; }}
      .controls input, .controls select {{ width: 100%; min-width: 0; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-layout">
        <div class="hero-copy">
          <div class="eyebrow">KRX Automated Screening</div>
          <h1>{escape(trading_date.isoformat())}</h1>
          <p>오늘의 결론만 먼저 보이도록 정리했습니다. 상단은 실제 투자 행동 기준으로 묶고, 세부 표와 렌즈는 아래로 접었습니다.</p>
          <div class="hero-note">먼저 `Value Core`와 `Growth Core`를 보고, 다음으로 `소액 관찰`, 마지막으로 `가치함정 경고`를 확인하면 됩니다. 점수보다 판단 문장과 주의점을 먼저 읽는 구조입니다.</div>
        </div>
      </div>
      <div class="metric-grid">{summary_html}</div>
    </section>
    <section class="section">
      <div class="section-head">
        <h2>오늘의 메모</h2>
        <span>실제 행동 기준으로만 네 그룹을 나눴습니다.</span>
      </div>
      <div class="definition-grid">
        {definitions_html}
      </div>
      <div class="memo-grid">
        {memo_value_core_html}
        {memo_growth_core_html}
        {memo_watch_html}
        {memo_trap_html}
      </div>
      <details class="fold">
        <summary>세부 데이터와 렌즈 더 보기</summary>
        <div class="fold-body">
          <div class="section-head">
            <h2>운영 상태</h2>
            <span>가장 많이 비는 항목과 운영 상태</span>
          </div>
          <div class="chip-row">{missing_html}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Core 카드</h2>
            <span>유동성 10억 기준과 반복성, 현금창출 질을 통과한 실매수 후보</span>
          </div>
          <div class="card-grid">{quick_review}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>소액 관찰 카드</h2>
            <span>논리는 있으나 유동성이나 구조상 비중을 크게 싣기 어려운 후보</span>
          </div>
          <div class="card-grid">{quick_watch}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>가치함정 경고 카드</h2>
            <span>싸 보여도 구조적 할인일 수 있는 후보</span>
          </div>
          <div class="card-grid">{trap_watch_html}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Missed Leader Detector</h2>
            <span>아직 덜 알려진 재평가 후보</span>
          </div>
          <div class="card-grid">{missed_leader_html}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Growth Proven</h2>
            <span>체급, 유동성, 실적 체력을 함께 통과한 성장주</span>
          </div>
          <div class="card-grid">{growth_proven_html}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Growth Speculative</h2>
            <span>테마·초기 모멘텀은 있으나 아직 검증이 더 필요한 후보</span>
          </div>
          <div class="card-grid">{growth_speculative_html}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Top Value 20</h2>
            <span>압축한 표</span>
          </div>
          <div class="table-wrap">{value_table}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Top Growth 20</h2>
            <span>과열 여부와 52주 위치를 함께 표시</span>
          </div>
          <div class="table-wrap">{growth_table}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Special Dividend Watch</h2>
            <span>최근 실제 배당이 높아 보여도 평년 배당력은 낮을 수 있는 종목</span>
          </div>
          <div class="table-wrap">{special_watch_html}</div>
          <div class="section-head" style="margin-top:22px;">
            <h2>Candidate Explorer</h2>
            <span>상위 200개 비제외 종목 검색/필터</span>
          </div>
          <div class="explorer-summary">
            <span class="chip strong">탐색 대상 {len(full_list):,}개</span>
            <span class="chip">정렬 기준 최종점수</span>
            <span class="chip">기본값은 실매수·관찰·경고만 표시</span>
          </div>
          <div class="controls">
            <input id="searchInput" type="search" placeholder="종목명 또는 티커 검색">
            <select id="bucketFilter">
              <option value="actionable">Core·관찰·경고</option>
              <option value="value_core">Value Core만</option>
              <option value="growth_core">Growth Core만</option>
              <option value="watch">소액 관찰만</option>
              <option value="trap">가치함정 경고만</option>
              <option value="all">전체 보기</option>
            </select>
            <select id="marketFilter">
              <option value="">시장 전체</option>
              <option value="KOSPI">KOSPI</option>
              <option value="KOSDAQ">KOSDAQ</option>
            </select>
            <select id="stageFilter">
              <option value="">단계 전체</option>
              <option value="초입">초입</option>
              <option value="중간">중간</option>
              <option value="후반">후반</option>
              <option value="과열">과열</option>
            </select>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>종목</th>
                  <th>시장</th>
                  <th>업종</th>
                  <th>시총구간</th>
                  <th>전일 종가</th>
                  <th>PER</th>
                  <th>PBR</th>
                  <th>배당 T</th>
                  <th>배당 N</th>
                  <th>6M</th>
                  <th>Value</th>
                  <th>Value Style</th>
                  <th>Growth</th>
                  <th>Growth Style</th>
                  <th>Core</th>
                  <th>최근반복</th>
                  <th>Stage</th>
                  <th>태그</th>
                  <th>결측</th>
                </tr>
              </thead>
              <tbody id="universeBody"></tbody>
            </table>
          </div>
        </div>
      </details>
    </section>
  </div>
  <script>
    const universeRows = {universe_json};
    const body = document.getElementById("universeBody");
    const searchInput = document.getElementById("searchInput");
    const bucketFilter = document.getElementById("bucketFilter");
    const marketFilter = document.getElementById("marketFilter");
    const stageFilter = document.getElementById("stageFilter");

    function stageBadge(stage) {{
      return `<span class="stage stage-${{stage || '초입'}}">${{stage || '-'}}</span>`;
    }}

    function fmt(value, suffix = "") {{
      if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "-";
      return `${{Number(value).toLocaleString("ko-KR", {{ maximumFractionDigits: 2 }})}}${{suffix}}`;
    }}

    function renderUniverse() {{
      const q = searchInput.value.trim().toLowerCase();
      const bucket = bucketFilter.value;
      const market = marketFilter.value;
      const stage = stageFilter.value;
      const filtered = universeRows.filter((row) => {{
        const matchQuery = !q || `${{row.name}} ${{row.ticker}}`.toLowerCase().includes(q);
        const matchBucket =
          bucket === "all"
          || (bucket === "value_core" && row.core_bucket === "Value Core")
          || (bucket === "growth_core" && row.core_bucket === "Growth Core")
          || (bucket === "watch" && row.recommendation_bucket === "소액 관찰")
          || (bucket === "trap" && row.recommendation_bucket === "가치함정 경고")
          || (
            bucket === "actionable"
            && ["Value Core", "Growth Core"].includes(row.core_bucket)
          )
          || (
            bucket === "actionable"
            && ["소액 관찰", "가치함정 경고"].includes(row.recommendation_bucket)
          );
        const matchMarket = !market || row.market === market;
        const matchStage = !stage || row.stage === stage;
        return matchQuery && matchBucket && matchMarket && matchStage;
      }});

      body.innerHTML = filtered.map((row) => `
        <tr>
          <td><strong>${{row.name}}</strong><div class="subtle">${{row.ticker}}</div></td>
          <td>${{row.market || "-"}}</td>
          <td>${{row.sector || "-"}}</td>
          <td>${{row.size_bucket || "-"}}</td>
          <td>${{fmt(row.prev_close)}}</td>
          <td>${{fmt(row.per)}}</td>
          <td>${{fmt(row.pbr)}}</td>
          <td>${{fmt(row.dividend_yield_trailing, "%")}}</td>
          <td>${{fmt(row.dividend_yield_normalized, "%")}}</td>
          <td>${{fmt(row.returns_6m_pct, "%")}}</td>
          <td>${{fmt(row.value_score)}}</td>
          <td>${{row.value_style || "-"}}</td>
          <td>${{fmt(row.growth_early_score)}}</td>
          <td>${{row.growth_style || "-"}}</td>
          <td>${{row.core_bucket || row.recommendation_bucket || "-"}}</td>
          <td>${{fmt(row.repeat_top_count)}}</td>
          <td>${{stageBadge(row.stage)}}</td>
          <td>${{row.tags || "-"}}</td>
          <td>${{row.missing_data || "-"}}</td>
        </tr>
      `).join("");
    }}

    searchInput.addEventListener("input", renderUniverse);
    bucketFilter.addEventListener("change", renderUniverse);
    marketFilter.addEventListener("change", renderUniverse);
    stageFilter.addEventListener("change", renderUniverse);
    renderUniverse();
  </script>
</body>
</html>"""


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    for column, default in (
        ("sector", ""),
        ("industry", ""),
        ("size_bucket", ""),
        ("dividend_yield_source", ""),
        ("dividend_yield_trailing", ""),
        ("dividend_yield_normalized", ""),
        ("business_quality_score", 0),
        ("liquidity_support_score", 0),
        ("value_trap_risk_score", 0),
        ("estimate_revision_score", 0),
        ("tam_expansion_score", 0),
        ("flow_momentum_score", 0),
        ("shareholder_return_score", 0),
        ("ownership_flow_score", 0),
        ("valuation_score", 0),
        ("policy_score", 0),
        ("payout_repeatability_score", 0),
        ("cashflow_quality_score", 0),
        ("governance_warning_score", 0),
        ("investability_score", 0),
        ("missed_leader_score", 0),
        ("final_score", 0),
        ("foreign_net_buy_3m", 0),
        ("pension_net_buy_3m", 0),
        ("etf_holding_change_3m", 0),
        ("foreign_net_buy_ratio_3m", 0),
        ("pension_net_buy_ratio_3m", 0),
        ("net_buy_ratio_3m", 0),
        ("total_equity", 0),
        ("total_debt", 0),
        ("ebitda", 0),
        ("fcf_yield_pct", 0),
        ("ev_ebitda", 0),
        ("peg", 0),
        ("industry_avg_per", 0),
        ("industry_per_discount_pct", 0),
        ("roe_pct", 0),
        ("roic_pct", 0),
        ("dividend_growth_rate_pct", 0),
        ("dividend_cut_flag", False),
        ("special_dividend_adjusted", False),
        ("treasury_stock_ratio_pct", 0),
        ("treasury_burn_recent", False),
        ("payout_increase_flag", False),
        ("dividend_tax_benefit_score", 0),
        ("tax_exemption_benefit_score", 0),
        ("governance_reform_score", 0),
        ("commercial_code_benefit_score", 0),
        ("consensus_op_income_estimate", 0),
        ("consensus_net_income_estimate", 0),
        ("consensus_eps_estimate", 0),
        ("op_income_revision_3m_pct", 0),
        ("op_income_revision_6m_pct", 0),
        ("op_income_revision_12m_pct", 0),
        ("net_income_revision_3m_pct", 0),
        ("net_income_revision_6m_pct", 0),
        ("net_income_revision_12m_pct", 0),
        ("eps_revision_3m_pct", 0),
        ("eps_revision_6m_pct", 0),
        ("eps_revision_12m_pct", 0),
        ("value_style", ""),
        ("growth_style", ""),
        ("recommendation_bucket", "보류"),
        ("core_bucket", ""),
        ("recommendation_reasons", ""),
        ("repeat_top_count", 0),
        ("source_notes", ""),
        ("missing_data", ""),
        ("tags", ""),
    ):
        if column not in working.columns:
            working[column] = default
    for column in (
        "value_score",
        "growth_early_score",
        "dividend_potential_score",
        "returns_6m_pct",
        "high_52w_ratio_pct",
        "repeat_top_count",
        "dividend_yield_trailing",
        "dividend_yield_normalized",
        "business_quality_score",
        "liquidity_support_score",
        "value_trap_risk_score",
        "estimate_revision_score",
        "tam_expansion_score",
        "flow_momentum_score",
        "shareholder_return_score",
        "ownership_flow_score",
        "valuation_score",
        "policy_score",
        "payout_repeatability_score",
        "cashflow_quality_score",
        "governance_warning_score",
        "investability_score",
        "missed_leader_score",
        "final_score",
        "foreign_net_buy_3m",
        "pension_net_buy_3m",
        "etf_holding_change_3m",
        "foreign_net_buy_ratio_3m",
        "pension_net_buy_ratio_3m",
        "net_buy_ratio_3m",
        "total_equity",
        "total_debt",
        "ebitda",
        "fcf_yield_pct",
        "ev_ebitda",
        "peg",
        "industry_avg_per",
        "industry_per_discount_pct",
        "roe_pct",
        "roic_pct",
        "dividend_growth_rate_pct",
        "treasury_stock_ratio_pct",
        "dividend_tax_benefit_score",
        "tax_exemption_benefit_score",
        "governance_reform_score",
        "commercial_code_benefit_score",
        "consensus_op_income_estimate",
        "consensus_net_income_estimate",
        "consensus_eps_estimate",
        "op_income_revision_3m_pct",
        "op_income_revision_6m_pct",
        "op_income_revision_12m_pct",
        "net_income_revision_3m_pct",
        "net_income_revision_6m_pct",
        "net_income_revision_12m_pct",
        "eps_revision_3m_pct",
        "eps_revision_6m_pct",
        "eps_revision_12m_pct",
    ):
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")
    if "excluded" in working.columns:
        working["excluded"] = working["excluded"].astype(str).str.lower().eq("true")
    for column in ("dividend_cut_flag", "special_dividend_adjusted", "treasury_burn_recent", "payout_increase_flag"):
        if column in working.columns:
            working[column] = working[column].astype(str).str.lower().eq("true")
    return working


def _summary_metrics(equities: list[EquitySnapshot], working: pd.DataFrame) -> dict[str, int]:
    total = len(equities) if equities else len(working)
    excluded = sum(1 for equity in equities if equity.excluded) if equities else int(working["excluded"].sum())
    missing = sum(1 for equity in equities if equity.missing_data) if equities else int(
        working["missing_data"].fillna("").astype(str).ne("").sum()
    )
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
    if equities:
        core_missing = sum(
            1 for equity in equities if any(field in core_fields for field in equity.missing_data)
        )
        value_heat = sum(1 for equity in equities if equity.stage == "과열" and not equity.excluded)
        early_stage = sum(1 for equity in equities if equity.stage == "초입" and not equity.excluded)
    else:
        core_missing = int(
            working["missing_data"].fillna("").astype(str).apply(
                lambda value: any(field in core_fields for field in value.split("|") if field)
            ).sum()
        )
        value_heat = int(((working["stage"] == "과열") & (~working["excluded"])).sum())
        early_stage = int(((working["stage"] == "초입") & (~working["excluded"])).sum())
    cache_rows = int(working["source_notes"].fillna("").str.contains("cache:historical_csv").sum())
    buy_review = int((working["recommendation_bucket"] == "실매수 검토").sum())
    value_core = int((working["core_bucket"].fillna("") == "Value Core").sum()) if "core_bucket" in working.columns else 0
    growth_core = int((working["core_bucket"].fillna("") == "Growth Core").sum()) if "core_bucket" in working.columns else 0
    small_watch = int((working["recommendation_bucket"] == "소액 관찰").sum())
    trap_watch = int((working["recommendation_bucket"] == "가치함정 경고").sum())
    return {
        "total": total,
        "excluded": excluded,
        "missing": missing,
        "core_missing": core_missing,
        "value_heat": value_heat,
        "early_stage": early_stage,
        "cache_rows": cache_rows,
        "buy_review": buy_review,
        "value_core": value_core,
        "growth_core": growth_core,
        "small_watch": small_watch,
        "trap_watch": trap_watch,
    }


def _top_missing_counts(working: pd.DataFrame) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for value in working["missing_data"].fillna(""):
        for item in filter(None, str(value).split("|")):
            counts[item] = counts.get(item, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:8]


def _value_table_ready(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    required = ("prev_close", "per", "pbr")
    for column in required:
        if column not in working.columns:
            working[column] = pd.NA
        working[column] = pd.to_numeric(working[column], errors="coerce")

    filtered = working[
        working["prev_close"].notna()
        & working["per"].notna()
        & working["pbr"].notna()
    ].copy()

    if "industry_per_discount_pct" in filtered.columns:
        filtered["industry_per_discount_pct"] = pd.to_numeric(
            filtered["industry_per_discount_pct"], errors="coerce"
        )

    value_like = (
        (filtered["per"] <= 20)
        | (filtered["pbr"] <= 1.5)
        | (filtered.get("industry_per_discount_pct", pd.Series(index=filtered.index, dtype=float)) >= 10)
    )
    filtered = filtered[value_like].copy()

    # Top Value is for actual valuation comparison, not partially-populated placeholders.
    if "recommendation_bucket" in filtered.columns:
        filtered = filtered[filtered["recommendation_bucket"].fillna("") != "제외"]
    return filtered


def _load_recent_top_counts(settings: Settings, trading_date: date) -> dict[str, dict[str, int]]:
    value_counts: dict[str, int] = {}
    growth_counts: dict[str, int] = {}
    value_weekly_counts: dict[str, int] = {}
    growth_weekly_counts: dict[str, int] = {}
    history_files = sorted(settings.data_dir.glob("screened_*.csv"), reverse=True)
    processed = 0
    for path in history_files:
        if path.name == f"screened_{trading_date.isoformat()}.csv":
            continue
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        working = _normalize_frame(frame)
        value_top = working[~working["excluded"]].nlargest(20, "final_score")["ticker"].astype(str).tolist()
        growth_top = working.nlargest(20, "growth_early_score")["ticker"].astype(str).tolist()
        for ticker in value_top:
            value_counts[ticker] = value_counts.get(ticker, 0) + 1
        for ticker in growth_top:
            growth_counts[ticker] = growth_counts.get(ticker, 0) + 1
        if processed < 5:
            for ticker in value_top:
                value_weekly_counts[ticker] = value_weekly_counts.get(ticker, 0) + 1
            for ticker in growth_top:
                growth_weekly_counts[ticker] = growth_weekly_counts.get(ticker, 0) + 1
        processed += 1
        if processed >= 10:
            break
    return {
        "value": value_counts,
        "growth": growth_counts,
        "value_weekly": value_weekly_counts,
        "growth_weekly": growth_weekly_counts,
    }


def _rank_for_explorer(
    frame: pd.DataFrame,
    score_column: str,
    history_counts: dict[str, int],
    weekly_counts: dict[str, int] | None = None,
) -> pd.DataFrame:
    working = frame.copy()
    core_fields = {"per", "pbr", "dividend_yield", "sales_3y", "op_income_3y", "net_income_3y"}
    repeat_counts: list[int] = []
    adjusted_scores: list[float] = []
    for row in working.itertuples(index=False):
        ticker = str(getattr(row, "ticker", ""))
        repeat_count = history_counts.get(ticker, 0)
        weekly_repeat = (weekly_counts or {}).get(ticker, 0)
        repeat_counts.append(repeat_count)
        base_score = getattr(row, score_column, None)
        if pd.isna(base_score):
            base_score = 0.0
        stage_bonus = {"초입": 0.8, "중간": 0.4, "후반": -0.15, "과열": -0.9}.get(
            str(getattr(row, "stage", "") or ""),
            0.0,
        )
        missing_count = len(
            [item for item in str(getattr(row, "missing_data", "") or "").split("|") if item in core_fields]
        )
        data_penalty = missing_count * 0.25
        repeat_penalty = min(3.0, repeat_count * 0.55)
        weekly_penalty = min(2.0, weekly_repeat * 0.45)
        final_score = getattr(row, "final_score", None)
        if pd.isna(final_score):
            final_score = base_score
        adjusted_scores.append(float(final_score) + stage_bonus - data_penalty - repeat_penalty - weekly_penalty)
    working["repeat_top_count"] = repeat_counts
    working["display_score"] = adjusted_scores
    return working.sort_values(
        by=["display_score", score_column, "estimate_revision_score", "tam_expansion_score"],
        ascending=False,
    )


def _select_featured_rows(
    frame: pd.DataFrame,
    score_column: str,
    history_counts: dict[str, int],
    weekly_counts: dict[str, int] | None,
    limit: int,
) -> pd.DataFrame:
    ranked = _rank_for_explorer(
        frame,
        score_column=score_column,
        history_counts=history_counts,
        weekly_counts=weekly_counts,
    )
    if ranked.empty:
        return ranked

    picks: list[int] = []
    sector_counts: dict[str, int] = {}
    size_counts: dict[str, int] = {}
    phases = (
        (2, 3),
        (3, 4),
        (10_000, 10_000),
    )

    for sector_cap, size_cap in phases:
        for idx, row in ranked.iterrows():
            if idx in picks:
                continue
            sector = str(row.get("sector") or "").strip()
            size_bucket = str(row.get("size_bucket") or "").strip()
            if sector and sector_counts.get(sector, 0) >= sector_cap:
                continue
            if size_bucket and size_counts.get(size_bucket, 0) >= size_cap:
                continue
            picks.append(idx)
            if sector:
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
            if size_bucket:
                size_counts[size_bucket] = size_counts.get(size_bucket, 0) + 1
            if len(picks) >= limit:
                break
        if len(picks) >= limit:
            break

    return ranked.loc[picks].reset_index(drop=True)


def _style_slice(frame: pd.DataFrame, column: str, target: str, limit: int) -> pd.DataFrame:
    if column not in frame.columns:
        return frame.head(0)
    filtered = frame[frame[column].fillna("") == target]
    return filtered.head(limit)


def _table_for_markdown(frame: pd.DataFrame, bucket: str) -> str:
    if frame.empty:
        return "_No rows_"

    if bucket == "value":
        columns = [
            "ticker",
            "name",
            "core_bucket",
            "sector",
            "size_bucket",
            "prev_close",
            "per",
            "peg",
            "roe_pct",
            "pbr",
            "dividend_yield_trailing",
            "dividend_yield_normalized",
            "returns_6m_pct",
            "final_score",
            "value_score",
            "estimate_revision_score",
            "tam_expansion_score",
            "ownership_flow_score",
            "policy_score",
            "dividend_potential_score",
            "business_quality_score",
            "liquidity_support_score",
            "stage",
            "tags",
            "missing_data",
        ]
    elif bucket == "special_dividend":
        columns = [
            "ticker",
            "name",
            "sector",
            "prev_close",
            "dividend_yield_trailing",
            "dividend_yield_normalized",
            "dividend_gap_pct",
            "dividends_3y",
            "tags",
        ]
    else:
        columns = [
            "ticker",
            "name",
            "sector",
            "size_bucket",
            "prev_close",
            "per",
            "pbr",
            "returns_6m_pct",
            "high_52w_ratio_pct",
            "growth_early_score",
            "value_score",
            "stage",
            "tags",
            "missing_data",
        ]
    table = frame[columns].copy()
    return table.to_markdown(index=False)


def _bullet_summary(frame: pd.DataFrame, score_column: str) -> str:
    if frame.empty:
        return "_No rows_"

    lines = []
    for row in frame.itertuples(index=False):
        score = getattr(row, score_column)
        returns_6m = getattr(row, "returns_6m_pct", None)
        stage = getattr(row, "stage", "")
        tags = getattr(row, "tags", "")
        sector = getattr(row, "sector", "") or getattr(row, "market", "")
        size_bucket = getattr(row, "size_bucket", "")
        recommendation_bucket = getattr(row, "core_bucket", None) or getattr(row, "recommendation_bucket", "")
        score_text = f"{score:.1f}" if pd.notna(score) else "-"
        returns_text = f"{returns_6m:.1f}%" if pd.notna(returns_6m) else "-"
        tag_text = f" / {tags}" if tags else ""
        lines.append(
            f"- {row.name} ({row.ticker}) [{sector} {size_bucket}] {recommendation_bucket} / score {score_text}, 6M {returns_text}, stage {stage}{tag_text}"
        )
    return "\n".join(lines)


def _card_grid(frame: pd.DataFrame, score_column: str, accent: str) -> str:
    cards: list[str] = []
    for row in frame.itertuples(index=False):
        score = getattr(row, score_column)
        score_text = f"{score:.1f}" if pd.notna(score) else "-"
        returns_text = f"{getattr(row, 'returns_6m_pct', float('nan')):.1f}%" if pd.notna(getattr(row, "returns_6m_pct", None)) else "-"
        trailing = getattr(row, "dividend_yield_trailing", None)
        normalized = getattr(row, "dividend_yield_normalized", None)
        trailing_text = f"{trailing:.2f}%" if pd.notna(trailing) else "-"
        normalized_text = f"{normalized:.2f}%" if pd.notna(normalized) else "-"
        div_text = f"{trailing_text} / {normalized_text}"
        cards.append(
            f"""
            <article class="pick-card {accent}">
              <div class="ticker">{escape(str(row.ticker))}</div>
              <h3>{escape(str(row.name))}</h3>
              <span class="score-badge {accent}">score {escape(score_text)}</span>
              <div class="meta">
                <div><strong>업종</strong><br>{escape(_fmt_cell(getattr(row, 'sector', None)))}</div>
                <div><strong>시총구간</strong><br>{escape(_fmt_cell(getattr(row, 'size_bucket', None)))}</div>
                <div><strong>PER</strong><br>{escape(_fmt_cell(getattr(row, 'per', None)))}</div>
                <div><strong>PBR</strong><br>{escape(_fmt_cell(getattr(row, 'pbr', None)))}</div>
                <div><strong>6M</strong><br>{escape(returns_text)}</div>
                <div><strong>배당 T/N</strong><br>{escape(div_text)}</div>
              </div>
              <div class="chip-row">
                <span class="chip">{escape(str(getattr(row, 'stage', '-') or '-'))}</span>
                {f'<span class="chip">{escape(str(getattr(row, "tags", "")))}</span>' if getattr(row, "tags", "") else ""}
              </div>
            </article>
            """
        )
    return "".join(cards)


def _conviction_grid(frame: pd.DataFrame) -> str:
    cards: list[str] = []
    for row in frame.itertuples(index=False):
        reasons = _recommendation_reasons(row)
        cards.append(
            f"""
            <article class="conviction-card">
              <div class="ticker">{escape(str(row.ticker))}</div>
              <h3>{escape(str(row.name))}</h3>
              <div class="conviction-score">총점 {escape(_fmt_cell(getattr(row, 'final_score', None)))}</div>
              <div class="conviction-metrics">
                <div><strong>Valuation</strong><span>{escape(_fmt_cell(getattr(row, 'valuation_score', None)))}</span></div>
                <div><strong>EPS Revision</strong><span>{escape(_fmt_cell(getattr(row, 'estimate_revision_score', None)))}</span></div>
                <div><strong>TAM Expansion</strong><span>{escape(_fmt_cell(getattr(row, 'tam_expansion_score', None)))}</span></div>
                <div><strong>Ownership</strong><span>{escape(_fmt_cell(getattr(row, 'ownership_flow_score', None)))}</span></div>
                <div><strong>Policy</strong><span>{escape(_fmt_cell(getattr(row, 'policy_score', None)))}</span></div>
                <div><strong>Business</strong><span>{escape(_fmt_cell(getattr(row, 'business_quality_score', None)))}</span></div>
              </div>
              <div class="subtle" style="margin-top:16px;">추천 이유</div>
              <ol class="reason-list">{''.join(f'<li>{escape(reason)}</li>' for reason in reasons)}</ol>
              <div class="decision"><strong>판단</strong><br>현재 단계 : {escape(str(getattr(row, 'stage', '-') or '-'))}</div>
            </article>
            """
        )
    return "".join(cards)


def _memo_grid(frame: pd.DataFrame, title: str, tone: str) -> str:
    intro_map = {
        "Value Core": "싸 보이는 것만이 아니라 사업체력과 현금흐름까지 통과한 가치주 후보입니다.",
        "Growth Core": "성장률만이 아니라 체급, 수급, 실적 체력까지 통과한 성장주 후보입니다.",
        "소액 관찰": "논리는 있지만 비중을 크게 실기 전 더 확인이 필요한 후보입니다.",
        "가치함정 경고": "싸 보이더라도 할인 이유를 먼저 설명해야 하는 후보입니다.",
    }
    cards: list[str] = []
    for row in frame.itertuples(index=False):
        reasons = _recommendation_reasons(row)[:2]
        caution = _memo_caution(row)
        metric_line = _bucket_metric_line(row)
        cards.append(
            f"""
            <article class="memo-card">
              <div class="ticker">{escape(str(getattr(row, 'ticker', '-')))}</div>
              <h3>{escape(str(getattr(row, 'name', '-')))}</h3>
              <div class="chip-row">
                <span class="score-badge {'value' if tone == 'value' else 'growth'}">{escape(str(getattr(row, 'core_bucket', None) or getattr(row, 'recommendation_bucket', '-') or '-'))}</span>
                <span class="chip">{escape(str(getattr(row, 'stage', '-') or '-'))}</span>
              </div>
              <div class="memo-summary">{escape(caution)}</div>
              <div class="memo-summary">{escape(metric_line)}</div>
              <ul class="memo-points">{''.join(f'<li>{escape(reason)}</li>' for reason in reasons)}</ul>
            </article>
            """
        )
    body = "".join(cards) if cards else "<div class='subtle'>오늘 조건에 맞는 종목이 없습니다.</div>"
    return f"""
    <section class="memo-panel {tone}">
      <h2>{escape(title)}</h2>
      <p>{escape(intro_map.get(title, ''))}</p>
      {body}
    </section>
    """


def _spotlight_strip(value_frame: pd.DataFrame, growth_frame: pd.DataFrame, missed_frame: pd.DataFrame) -> str:
    configs = [
        ("Top Value", value_frame, "value", "final_score"),
        ("Top Growth", growth_frame, "growth", "growth_early_score"),
        ("Missed Leader", missed_frame, "growth", "missed_leader_score"),
    ]
    cards: list[str] = []
    for label, frame, accent, score_column in configs:
        if frame.empty:
            cards.append(
                f"""
                <article class="spotlight-card {accent}">
                  <span class="spotlight-label">{escape(label)}</span>
                  <h3>후보 없음</h3>
                  <div class="spotlight-line">오늘 조건에 맞는 종목이 아직 추려지지 않았습니다.</div>
                </article>
                """
            )
            continue
        row = next(frame.itertuples(index=False))
        reasons = _recommendation_reasons(row)
        cards.append(
            f"""
            <article class="spotlight-card {accent}">
              <span class="spotlight-label">{escape(label)}</span>
              <h3>{escape(str(getattr(row, 'name', '-')))}</h3>
              <div class="ticker">{escape(str(getattr(row, 'ticker', '-')))} · {escape(str(getattr(row, 'sector', '-') or '-'))}</div>
              <div class="chip-row">
                <span class="score-badge {accent}">score {escape(_fmt_cell(getattr(row, score_column, None)))}</span>
                <span class="chip">{escape(str(getattr(row, 'stage', '-') or '-'))}</span>
              </div>
              <div class="spotlight-line">{escape(reasons[0])}</div>
            </article>
            """
        )
    return "".join(cards)


def _memo_caution(row: object) -> str:
    core_bucket = str(getattr(row, "core_bucket", "") or "")
    bucket = str(getattr(row, "recommendation_bucket", "") or "")
    tags = str(getattr(row, "tags", "") or "")
    if core_bucket == "Value Core":
        return "싸 보여서가 아니라 실제 사업체력과 현금흐름까지 남은 가치주 후보입니다."
    if core_bucket == "Growth Core":
        return "성장률 숫자만이 아니라 실적 체력과 수급 현실성까지 통과한 성장주 후보입니다."
    if bucket == "가치함정 경고":
        return "저평가처럼 보여도 구조적 할인 가능성을 먼저 확인해야 합니다."
    if "배당 불안정" in tags:
        return "배당 반복성은 완벽하지 않아 추세 확인이 더 필요합니다."
    if getattr(row, "value_style", "") == "Turnaround Value":
        return "턴어라운드 초입 가정이 들어가 있으므로 실적 회복 확인이 중요합니다."
    return "지금은 점수보다 실제 투자 가능성 기준으로 상단에 남은 후보입니다."


def _bucket_metric_line(row: object) -> str:
    turnover_raw = getattr(row, "avg_trading_value_20d", None)
    turnover = _fmt_amount_short(turnover_raw)
    investability_raw = getattr(row, "investability_score", None)
    business_raw = getattr(row, "business_quality_score", None)
    cashflow_raw = getattr(row, "cashflow_quality_score", None)
    payout_raw = getattr(row, "payout_repeatability_score", None)
    trap_raw = getattr(row, "value_trap_risk_score", None)

    checks = [
        f"거래대금 {turnover} {'통과' if _num(turnover_raw) >= 10000000000 else '미달'}",
        f"투자가능성 {_fmt_cell(investability_raw)} {'통과' if _num(investability_raw) >= 3.0 else '미달'}",
        f"사업체력 {_fmt_cell(business_raw)} {'통과' if _num(business_raw) >= 5.0 else '미달'}",
        f"현금흐름 {_fmt_cell(cashflow_raw)} {'통과' if _num(cashflow_raw) >= 1.0 else '미달'}",
        f"배당반복 {_fmt_cell(payout_raw)} {'통과' if _num(payout_raw) >= 1.0 else '미달'}",
        f"함정위험 {_fmt_cell(trap_raw)}",
    ]
    return " | ".join(checks)


def _bucket_definitions_markdown() -> str:
    rows = [
        "- `Value Core`: 거래대금 20D 100억 이상, `investability >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`. 저평가 근거와 사업 지속성이 함께 보여야 합니다.",
        "- `Growth Core`: 거래대금 20D 100억 이상, `investability >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`. `Growth Proven`과 추정치/수급/TAM 중 최소 두 축이 확인돼야 합니다.",
        "- `Value Conviction`: `PER <= 20` 또는 `PBR <= 1.5` 또는 업종 할인 20% 이상, 사업체력/현금흐름 양호.",
        "- `Growth Conviction`: `Growth Proven`, `estimate_revision >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`, `stage != 과열`, 고PER면 정당화 태그 필요.",
        "- `소액 관찰`: 논리는 유지되지만 유동성/체급/투자가능성 중 일부 부족. 보통 `최종점수 >= 22`, `business >= 3.8`, `cashflow >= 0`.",
        "- `보류`: 재평가 신호는 있으나 핵심 게이트 일부 미달. 상단 추천보다는 추가 검증 대상입니다.",
        "- `가치함정 경고`: `value_trap_risk` 높거나 거버넌스 할인 의심. 싸 보여도 할인 이유 먼저 확인.",
        "- `제외`: 급등 제외, 최소 현실성 게이트 미통과, 현금흐름 심각 훼손 등.",
    ]
    return "\n".join(rows)


def _bucket_definitions_html() -> str:
    cards = [
        (
            "Value Core",
            "단순 저PER이 아니라 사업체력, 현금흐름, 유동성까지 함께 통과한 가치주 후보입니다.",
            [
                "20일 거래대금 100억 이상",
                "투자가능성 3.0 이상",
                "사업체력 5.0 이상",
                "현금흐름 1.0 이상",
                "업종 대비 할인 또는 자산가치 근거",
            ],
        ),
        (
            "Growth Core",
            "성장률만이 아니라 실적 체력, 수급, 산업 확장성을 함께 확인한 성장주 후보입니다.",
            [
                "20일 거래대금 100억 이상",
                "투자가능성 3.0 이상",
                "사업체력 5.0 이상",
                "Growth Proven 필요",
                "추정치 개선 + TAM/수급 확인",
            ],
        ),
        (
            "소액 관찰 / 경고 / 제외",
            "논리는 있으나 유동성이나 구조가 약하거나, 싸 보여도 할인 이유가 의심되는 그룹입니다.",
            [
                "최종점수 22 이상",
                "사업체력 3.8 이상",
                "현금흐름 0 이상",
                "관찰: 유동성/체급 일부 미달 허용",
                "경고: 가치함정·거버넌스 할인 의심",
                "제외: 급등·초저유동성·최소 현실성 미통과",
            ],
        ),
    ]
    return "".join(
        f"""
        <article class="definition-card">
          <h3>{escape(title)}</h3>
          <p>{escape(desc)}</p>
          <ul>{''.join(f'<li>{escape(item)}</li>' for item in items)}</ul>
        </article>
        """
        for title, desc, items in cards
    )


def _recommendation_reasons(row: object) -> list[str]:
    explicit = str(getattr(row, "recommendation_reasons", "") or "").strip()
    if explicit:
        return [item.strip() for item in explicit.split("|") if item.strip()][:4]

    reasons: list[str] = []
    name = str(getattr(row, "name", "") or "")

    estimate = getattr(row, "estimate_revision_score", 0) or 0
    if estimate >= 8:
        reasons.append(f"최근 이익 추정치가 강하게 상향되고 있습니다.")
    elif estimate >= 5:
        reasons.append(f"최근 영업이익/순이익 컨센서스가 개선되고 있습니다.")

    tam = getattr(row, "tam_expansion_score", 0) or 0
    if tam >= 10:
        reasons.append(f"{name}이 속한 산업의 글로벌 TAM 확대 가능성이 큽니다.")
    elif tam >= 6:
        reasons.append("산업 성장률과 수요 확장 신호가 유의미합니다.")

    valuation = getattr(row, "valuation_score", 0) or 0
    per = getattr(row, "per", None)
    industry_discount = getattr(row, "industry_per_discount_pct", None)
    if valuation >= 7 and per not in (None, ""):
        if industry_discount not in (None, "") and pd.notna(industry_discount):
            reasons.append(
                f"PER { _fmt_cell(per) }배로 업종 평균 대비 { _fmt_cell(industry_discount) }% 할인 구간입니다."
            )
        else:
            reasons.append(f"현재 PER { _fmt_cell(per) }배로 밸류에이션 부담이 낮습니다.")

    ownership = getattr(row, "ownership_flow_score", 0) or 0
    if ownership >= 8:
        reasons.append("최근 3개월 외국인·연기금 실수급이 강하게 유입되고 있습니다.")
    elif ownership >= 5:
        reasons.append("최근 수급 흐름이 우호적으로 전환되고 있습니다.")

    policy = getattr(row, "policy_score", 0) or 0
    if policy >= 8:
        reasons.append("주주환원, 정책 수혜, 지배구조 변화가 동시에 기대됩니다.")
    elif policy >= 4:
        reasons.append("주주환원 정책 변화 가능성이 점수에 반영됐습니다.")

    business = getattr(row, "business_quality_score", 0) or 0
    if business >= 7:
        reasons.append("이익 체력과 사업 지속성이 안정적인 편입니다.")

    if not reasons:
        reasons.append("여러 축에서 평균 이상 점수를 받아 관찰 우선순위가 높습니다.")
    return reasons[:4]


def _html_table(frame: pd.DataFrame, bucket: str) -> str:
    if frame.empty:
        return "<div class='subtle'>No rows</div>"
    rows: list[str] = []
    if bucket == "value":
        columns = ["ticker", "name", "recommendation_bucket", "core_bucket", "sector", "size_bucket", "prev_close", "per", "peg", "roe_pct", "pbr", "dividend_yield_trailing", "dividend_yield_normalized", "returns_6m_pct", "final_score", "value_score", "estimate_revision_score", "tam_expansion_score", "ownership_flow_score", "policy_score", "payout_repeatability_score", "cashflow_quality_score", "governance_warning_score", "investability_score", "dividend_potential_score", "business_quality_score", "liquidity_support_score", "stage", "tags", "missing_data"]
    elif bucket == "special_dividend":
        columns = ["ticker", "name", "sector", "prev_close", "dividend_yield_trailing", "dividend_yield_normalized", "dividend_gap_pct", "dividends_3y", "tags"]
    else:
        columns = ["ticker", "name", "sector", "size_bucket", "prev_close", "per", "pbr", "returns_6m_pct", "high_52w_ratio_pct", "growth_early_score", "value_score", "stage", "tags", "missing_data"]

    for row in frame[columns].itertuples(index=False, name=None):
        rendered = []
        for idx, cell in enumerate(row):
            key = columns[idx]
            if key == "stage":
                rendered.append(f"<td><span class='stage stage-{escape(str(cell or '초입'))}'>{escape(str(cell or '-'))}</span></td>")
            else:
                rendered.append(f"<td>{escape(_fmt_cell(cell, key))}</td>")
        rows.append("<tr>" + "".join(rendered) + "</tr>")
    header = "".join(f"<th>{escape(name)}</th>" for name in columns)
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _records_for_ui(frame: pd.DataFrame) -> list[dict[str, object]]:
    columns = [
        "ticker",
        "market",
        "name",
        "sector",
        "size_bucket",
        "prev_close",
        "per",
        "pbr",
        "dividend_yield",
        "dividend_yield_trailing",
        "dividend_yield_normalized",
        "returns_6m_pct",
        "final_score",
        "valuation_score",
        "value_score",
        "growth_early_score",
        "business_quality_score",
        "liquidity_support_score",
        "value_trap_risk_score",
        "estimate_revision_score",
        "tam_expansion_score",
        "flow_momentum_score",
        "shareholder_return_score",
        "ownership_flow_score",
        "policy_score",
        "payout_repeatability_score",
        "cashflow_quality_score",
        "governance_warning_score",
        "investability_score",
        "missed_leader_score",
        "recommendation_bucket",
        "core_bucket",
        "recommendation_reasons",
        "value_style",
        "growth_style",
        "stage",
        "tags",
        "missing_data",
        "repeat_top_count",
    ]
    return frame[columns].to_dict(orient="records")


def _special_dividend_watchlist(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    working = frame.copy()
    for column in ("dividend_yield_trailing", "dividend_yield_normalized"):
        if column not in working.columns:
            working[column] = pd.NA
        working[column] = pd.to_numeric(working[column], errors="coerce")

    working = working[
        working["dividend_yield_trailing"].notna()
        & working["dividend_yield_normalized"].notna()
        & (working["dividend_yield_trailing"] >= 4)
    ].copy()
    if working.empty:
        return working

    working["dividend_gap_pct"] = (
        working["dividend_yield_trailing"] - working["dividend_yield_normalized"]
    ).round(2)
    working = working[
        (working["dividend_gap_pct"] >= 2.0)
        | (
            working["dividend_yield_trailing"]
            >= working["dividend_yield_normalized"] * 1.8
        )
    ]
    if working.empty:
        return working
    return working.sort_values(
        by=["dividend_gap_pct", "dividend_yield_trailing"],
        ascending=False,
    ).head(limit)


def _fmt_cell(value: object, key: str | None = None) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return "-"
    if key in {"prev_close"}:
        return f"{float(value):,.0f}"
    if key in {"per", "pbr", "dividend_yield", "returns_6m_pct", "high_52w_ratio_pct", "value_score", "growth_early_score", "dividend_potential_score", "payout_repeatability_score", "cashflow_quality_score", "governance_warning_score", "investability_score"}:
        return f"{float(value):,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _fmt_amount_short(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    amount = float(value)
    eok = amount / 100_000_000
    return f"{eok:,.0f}억"


def _num(value: object) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("-inf")
    try:
        return float(value)
    except Exception:
        return float("-inf")
