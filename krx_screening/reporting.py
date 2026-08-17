from __future__ import annotations

import json
import re
from datetime import date
from html import escape

import pandas as pd

from .config import Settings
from .models import EquitySnapshot
from .output_health import assess_output_health

LOW_QUALITY_ISSUE_PATTERNS = (
    "AI주식상승확률분석",
    "AI가 분석해주는",
    "주가 전망",
    "밀릴때마다",
    "저점을 줄때마다",
    "물량 모아둘 기회",
    "이후 전망 및 대응전략",
    "네이버 블로그",
    "투자분석",
    "Sonia Citron",
    "gVhDYuEzku",
    "주식민원처리반",
)

LOW_QUALITY_ISSUE_REGEXES = (
    re.compile(r"^\[[^\]]*시그널\]"),
    re.compile(r"상승확률"),
    re.compile(r"적정주가"),
    re.compile(r"상한가가 고점 신호"),
)


def write_outputs(
    settings: Settings,
    trading_date: date,
    equities: list[EquitySnapshot],
) -> tuple[str, str, bool]:
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
    health = assess_output_health(frame)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")

    markdown = _build_markdown(settings, trading_date, equities, frame)
    html = _build_html(settings, trading_date, equities, frame)
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(markdown)
    with html_path.open("w", encoding="utf-8") as handle:
        handle.write(html)
    if health.publishable:
        frame.to_csv(latest_csv_path, index=False, encoding="utf-8-sig")
        with latest_md_path.open("w", encoding="utf-8") as handle:
            handle.write(markdown)
        with latest_html_path.open("w", encoding="utf-8") as handle:
            handle.write(html)
    _write_validation_outputs(settings)

    return str(md_path), str(csv_path), health.publishable


def _write_validation_outputs(settings: Settings) -> None:
    validation = _build_validation_payload(settings)
    if validation is None:
        return

    md_path = settings.reports_dir / "validation.md"
    html_path = settings.reports_dir / "validation.html"
    md_path.write_text(_build_validation_markdown(validation), encoding="utf-8")
    html_path.write_text(_build_validation_html(validation), encoding="utf-8")


def _build_validation_payload(settings: Settings) -> dict[str, object] | None:
    files = sorted(settings.data_dir.glob("screened_*.csv"))
    snapshots: list[tuple[str, pd.DataFrame]] = []
    for path in files:
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
        except Exception:
            continue
        snapshots.append((path.stem.replace("screened_", ""), _normalize_frame(frame)))

    if len(snapshots) < 3:
        return None

    bucket_rows: list[dict[str, object]] = []
    theme_rows: list[dict[str, object]] = []
    observations: list[dict[str, object]] = []

    latest_date, latest_frame = snapshots[-1]
    latest_prices = _validation_price_map(latest_frame)

    bucket_filters = [
        ("Value Core", lambda frame: frame["core_bucket"].fillna("") == "Value Core"),
        ("Growth Core", lambda frame: frame["core_bucket"].fillna("") == "Growth Core"),
        ("Cycle Leader", lambda frame: frame["leader_bucket"].fillna("") == "Leader"),
        ("Leader Candidate", lambda frame: frame["leader_bucket"].fillna("") == "Leader Candidate"),
        ("실매수 검토", lambda frame: frame["recommendation_bucket"].fillna("") == "실매수 검토"),
        ("소액 관찰", lambda frame: frame["recommendation_bucket"].fillna("") == "소액 관찰"),
        ("가치함정 경고", lambda frame: frame["recommendation_bucket"].fillna("") == "가치함정 경고"),
    ]

    for index, (asof_date, frame) in enumerate(snapshots[:-1]):
        next_date, next_frame = snapshots[index + 1]
        next_prices = _validation_price_map(next_frame)
        source = frame.copy()
        source["theme"] = source["theme"].fillna("미분류").replace("", "미분류")
        source["sub_theme"] = source["sub_theme"].fillna("").replace("", "")
        source["theme_gate_pass"] = source["theme_gate_pass"].astype(str).str.lower().eq("true")

        benchmark = _compute_bucket_return(
            source[source["recommendation_bucket"].fillna("") != "제외"],
            next_prices,
        )
        benchmark_latest = _compute_bucket_return(
            source[source["recommendation_bucket"].fillna("") != "제외"],
            latest_prices,
        )

        for bucket_name, bucket_filter in bucket_filters:
            bucket_frame = source[bucket_filter(source)]
            next_stats = _compute_bucket_return(bucket_frame, next_prices)
            latest_stats = _compute_bucket_return(bucket_frame, latest_prices)
            bucket_rows.append(
                {
                    "asof_date": asof_date,
                    "bucket": bucket_name,
                    "count": int(len(bucket_frame)),
                    "next_date": next_date,
                    "next_return": next_stats["avg_return"],
                    "next_hit_rate": next_stats["positive_rate"],
                    "next_coverage": next_stats["coverage"],
                    "next_outperformance": next_stats["avg_return"] - benchmark["avg_return"] if next_stats["coverage"] and benchmark["coverage"] else None,
                    "latest_date": latest_date,
                    "latest_return": latest_stats["avg_return"],
                    "latest_hit_rate": latest_stats["positive_rate"],
                    "latest_coverage": latest_stats["coverage"],
                    "latest_outperformance": latest_stats["avg_return"] - benchmark_latest["avg_return"] if latest_stats["coverage"] and benchmark_latest["coverage"] else None,
                }
            )

        themed = source[
            (source["recommendation_bucket"].fillna("") != "제외")
            & (source["theme_gate_pass"])
            & (source["theme"] != "미분류")
        ]
        for theme, group in themed.groupby("theme", dropna=False):
            next_stats = _compute_bucket_return(group, next_prices)
            latest_stats = _compute_bucket_return(group, latest_prices)
            theme_rows.append(
                {
                    "asof_date": asof_date,
                    "theme": str(theme),
                    "count": int(len(group)),
                    "next_return": next_stats["avg_return"],
                    "next_hit_rate": next_stats["positive_rate"],
                    "next_outperformance": next_stats["avg_return"] - benchmark["avg_return"] if next_stats["coverage"] and benchmark["coverage"] else None,
                    "latest_return": latest_stats["avg_return"],
                    "latest_hit_rate": latest_stats["positive_rate"],
                    "latest_outperformance": latest_stats["avg_return"] - benchmark_latest["avg_return"] if latest_stats["coverage"] and benchmark_latest["coverage"] else None,
                }
            )

        top_picks = source[
            source["recommendation_bucket"].fillna("").isin(["실매수 검토", "소액 관찰"])
        ].sort_values(by=["final_score"], ascending=False).head(5)
        for row in top_picks.itertuples(index=False):
            next_close = next_prices.get(str(getattr(row, "ticker", "")))
            latest_close = latest_prices.get(str(getattr(row, "ticker", "")))
            start_close = _num(getattr(row, "prev_close", None))
            if not start_close or start_close <= 0:
                continue
            observations.append(
                {
                    "asof_date": asof_date,
                    "ticker": str(getattr(row, "ticker", "")),
                    "name": str(getattr(row, "name", "")),
                    "bucket": str(getattr(row, "core_bucket", "") or getattr(row, "recommendation_bucket", "") or "-"),
                    "theme": str(getattr(row, "theme", "") or "미분류"),
                    "sub_theme": str(getattr(row, "sub_theme", "") or ""),
                    "start_close": start_close,
                    "next_return": ((next_close / start_close) - 1) * 100 if next_close else None,
                    "latest_return": ((latest_close / start_close) - 1) * 100 if latest_close else None,
                }
            )

    bucket_summary = _aggregate_validation_rows(pd.DataFrame(bucket_rows), key="bucket")
    theme_summary = _aggregate_validation_rows(pd.DataFrame(theme_rows), key="theme", min_count=1)
    observations_frame = pd.DataFrame(observations).sort_values(by=["asof_date", "latest_return"], ascending=[False, False]).head(30)

    return {
        "snapshot_count": len(snapshots),
        "date_range": f"{snapshots[0][0]} ~ {snapshots[-1][0]}",
        "latest_date": latest_date,
        "bucket_summary": bucket_summary,
        "theme_summary": theme_summary,
        "observations": observations_frame,
        "note": "거래일이 연속적이지 않아 '다음 스냅샷' 기준 성과와 '최신 스냅샷까지 보유' 성과를 함께 봅니다.",
    }


def _validation_price_map(frame: pd.DataFrame) -> dict[str, float]:
    mapping: dict[str, float] = {}
    for row in frame.itertuples(index=False):
        ticker = str(getattr(row, "ticker", "") or "")
        close = _num(getattr(row, "prev_close", None))
        if ticker and close and close > 0:
            mapping[ticker] = close
    return mapping


def _compute_bucket_return(frame: pd.DataFrame, future_prices: dict[str, float]) -> dict[str, float]:
    returns: list[float] = []
    for row in frame.itertuples(index=False):
        ticker = str(getattr(row, "ticker", "") or "")
        start_close = _num(getattr(row, "prev_close", None))
        future_close = future_prices.get(ticker)
        if not ticker or not start_close or start_close <= 0 or not future_close:
            continue
        returns.append(((future_close / start_close) - 1) * 100)
    if not returns:
        return {"avg_return": 0.0, "positive_rate": 0.0, "coverage": 0}
    positives = sum(1 for value in returns if value > 0)
    return {
        "avg_return": round(sum(returns) / len(returns), 2),
        "positive_rate": round((positives / len(returns)) * 100, 1),
        "coverage": len(returns),
    }


def _aggregate_validation_rows(frame: pd.DataFrame, key: str, min_count: int = 1) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    grouped = (
        frame.groupby(key, dropna=False)
        .agg(
            observations=("count", "sum"),
            next_return=("next_return", "mean"),
            next_hit_rate=("next_hit_rate", "mean"),
            next_outperformance=("next_outperformance", "mean"),
            latest_return=("latest_return", "mean"),
            latest_hit_rate=("latest_hit_rate", "mean"),
            latest_outperformance=("latest_outperformance", "mean"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["observations"] >= min_count]
    grouped = grouped.sort_values(by=["latest_outperformance", "latest_return", "observations"], ascending=[False, False, False])
    return grouped


def _build_validation_markdown(payload: dict[str, object]) -> str:
    bucket_summary = payload["bucket_summary"]
    theme_summary = payload["theme_summary"]
    observations = payload["observations"]
    lines = [
        "# KRX Screening Validation",
        "",
        f"- 검증 스냅샷 수: {payload['snapshot_count']}",
        f"- 검증 구간: {payload['date_range']}",
        f"- 최신 기준일: {payload['latest_date']}",
        f"- 주의: {payload['note']}",
        "",
        "## Bucket Validation",
        _frame_to_markdown_table(bucket_summary) if not bucket_summary.empty else "데이터 없음",
        "",
        "## Theme Validation",
        _frame_to_markdown_table(theme_summary.head(20)) if not theme_summary.empty else "데이터 없음",
        "",
        "## Sample Observations",
        _frame_to_markdown_table(observations) if not observations.empty else "데이터 없음",
    ]
    return "\n".join(lines)


def _build_validation_html(payload: dict[str, object]) -> str:
    bucket_summary: pd.DataFrame = payload["bucket_summary"]  # type: ignore[assignment]
    theme_summary: pd.DataFrame = payload["theme_summary"]  # type: ignore[assignment]
    observations: pd.DataFrame = payload["observations"]  # type: ignore[assignment]
    bucket_table = bucket_summary.to_html(index=False, classes="data-table", border=0, justify="left") if not bucket_summary.empty else "<div class='empty'>데이터 없음</div>"
    theme_table = theme_summary.head(20).to_html(index=False, classes="data-table", border=0, justify="left") if not theme_summary.empty else "<div class='empty'>데이터 없음</div>"
    observation_table = observations.to_html(index=False, classes="data-table", border=0, justify="left") if not observations.empty else "<div class='empty'>데이터 없음</div>"
    bucket_cards = _validation_stat_cards_html(bucket_summary, key_column="bucket")
    theme_cards = _validation_stat_cards_html(theme_summary.head(10), key_column="theme")
    metric_cards = _validation_metric_cards_html(bucket_summary, theme_summary)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KRX Validation</title>
  <style>
    body {{
      margin: 0;
      font-family: "Pretendard", "SUIT", "Apple SD Gothic Neo", sans-serif;
      background: #f7f4ee;
      color: #1f1a14;
    }}
    .shell {{ width: min(1280px, calc(100vw - 32px)); margin: 24px auto 48px; }}
    .hero {{
      background: #fffaf3;
      border: 1px solid rgba(44,36,27,0.10);
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 24px 60px rgba(58,42,24,0.10);
    }}
    h1 {{ margin: 0 0 8px; font-size: 38px; }}
    p, li {{ color: #6b6257; line-height: 1.6; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .chip {{
      display: inline-flex; padding: 8px 12px; border-radius: 999px;
      background: #fff; border: 1px solid rgba(44,36,27,0.10); font-size: 13px;
    }}
    .section {{ margin-top: 22px; background: rgba(255,255,255,0.82); border: 1px solid rgba(44,36,27,0.08); border-radius: 22px; padding: 22px; }}
    .section h2 {{ margin: 0 0 10px; font-size: 22px; }}
    .stat-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .stat-card {{
      border-radius: 18px;
      border: 1px solid rgba(44,36,27,0.08);
      background: #fff;
      padding: 16px;
    }}
    .stat-card strong {{
      display: block;
      font-size: 24px;
      margin-top: 6px;
    }}
    .stat-card .label {{
      font-size: 12px;
      text-transform: uppercase;
      color: #8b7e71;
      letter-spacing: 0.08em;
    }}
    .score-up {{ color: #0f766e; }}
    .score-down {{ color: #b91c1c; }}
    .score-flat {{ color: #6b6257; }}
    .split-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-top: 14px;
    }}
    .mini-card {{
      border-radius: 18px;
      border: 1px solid rgba(44,36,27,0.08);
      background: #fffdf8;
      padding: 18px;
    }}
    .mini-card h3 {{
      margin: 0 0 10px;
      font-size: 18px;
    }}
    .mini-list {{
      margin: 0;
      padding-left: 18px;
      color: #3a3128;
    }}
    .mini-list li {{
      margin-bottom: 8px;
    }}
    .data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .data-table th, .data-table td {{ padding: 10px 12px; border-bottom: 1px solid rgba(44,36,27,0.08); text-align: left; }}
    .data-table th {{ background: #f3eadb; position: sticky; top: 0; }}
    .table-wrap {{ overflow: auto; }}
    .empty {{ color: #6b6257; }}
    a {{ color: #0f766e; text-decoration: none; }}
    @media (max-width: 1000px) {{
      .stat-grid, .split-grid {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (max-width: 720px) {{
      .shell {{ width: min(100vw - 20px, 100%); margin: 12px auto 28px; }}
      .hero, .section {{ padding: 18px; border-radius: 20px; }}
      .stat-grid, .split-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div><a href="latest.html">스크리닝으로 돌아가기</a></div>
      <h1>KRX Validation</h1>
      <p>스크리닝이 실제로 이후 스냅샷에서 얼마나 먹혔는지 버킷과 테마별로 확인하는 페이지입니다.</p>
      <div class="meta">
        <span class="chip">검증 스냅샷 {escape(str(payload['snapshot_count']))}개</span>
        <span class="chip">검증 구간 {escape(str(payload['date_range']))}</span>
        <span class="chip">최신 기준 {escape(str(payload['latest_date']))}</span>
      </div>
      <p>{escape(str(payload['note']))}</p>
      <div class="stat-grid">{metric_cards}</div>
    </section>
    <section class="section">
      <h2>Quick Read</h2>
      <div class="split-grid">
        <div class="mini-card">
          <h3>Bucket 상위/하위</h3>
          {bucket_cards}
        </div>
        <div class="mini-card">
          <h3>Theme 상위/하위</h3>
          {theme_cards}
        </div>
      </div>
    </section>
    <section class="section">
      <h2>Bucket Validation</h2>
      <div class="table-wrap">{bucket_table}</div>
    </section>
    <section class="section">
      <h2>Theme Validation</h2>
      <div class="table-wrap">{theme_table}</div>
    </section>
    <section class="section">
      <h2>Sample Observations</h2>
      <div class="table-wrap">{observation_table}</div>
    </section>
    </div>
</body>
</html>"""


def _validation_metric_cards_html(bucket_summary: pd.DataFrame, theme_summary: pd.DataFrame) -> str:
    cards: list[tuple[str, str, str]] = []
    best_bucket = _best_validation_row(bucket_summary)
    worst_bucket = _worst_validation_row(bucket_summary)
    best_theme = _best_validation_row(theme_summary)
    total_themes = str(len(theme_summary.index)) if not theme_summary.empty else "0"

    if best_bucket is not None:
        cards.append(("Best Bucket", str(best_bucket.iloc[0]), _fmt_signed(best_bucket.get("latest_outperformance"))))
    if worst_bucket is not None:
        cards.append(("Weakest Bucket", str(worst_bucket.iloc[0]), _fmt_signed(worst_bucket.get("latest_outperformance"))))
    if best_theme is not None:
        cards.append(("Best Theme", str(best_theme.iloc[0]), _fmt_signed(best_theme.get("latest_outperformance"))))
    cards.append(("Tracked Themes", total_themes, "관측 테마 수"))

    rendered = []
    for label, primary, secondary in cards:
        cls = "score-flat"
        if secondary.startswith("+"):
            cls = "score-up"
        elif secondary.startswith("-"):
            cls = "score-down"
        rendered.append(
            f'<article class="stat-card"><span class="label">{escape(label)}</span><strong>{escape(primary)}</strong><span class="{cls}">{escape(secondary)}</span></article>'
        )
    return "".join(rendered)


def _validation_stat_cards_html(frame: pd.DataFrame, key_column: str) -> str:
    if frame.empty:
        return "<div class='empty'>데이터 없음</div>"
    best = _best_validation_row(frame)
    worst = _worst_validation_row(frame)
    items: list[str] = []
    if best is not None:
        items.append(
            f"<div><strong>상위</strong><ol class='mini-list'><li>{escape(str(best.iloc[0]))} · 초과수익 {escape(_fmt_signed(best.get('latest_outperformance')))} · 적중률 {escape(_fmt_percent(best.get('latest_hit_rate')))}</li></ol></div>"
        )
    if worst is not None and (best is None or str(best.iloc[0]) != str(worst.iloc[0])):
        items.append(
            f"<div style='margin-top:12px;'><strong>하위</strong><ol class='mini-list'><li>{escape(str(worst.iloc[0]))} · 초과수익 {escape(_fmt_signed(worst.get('latest_outperformance')))} · 적중률 {escape(_fmt_percent(worst.get('latest_hit_rate')))}</li></ol></div>"
        )
    top_rows = frame.head(3)
    extra = [
        f"<li>{escape(str(getattr(row, key_column)))} · 최신수익률 {escape(_fmt_signed(getattr(row, 'latest_return', None)))} · 관측 {escape(str(int(getattr(row, 'observations', 0))))}회</li>"
        for row in top_rows.itertuples(index=False)
    ]
    items.append(f"<div style='margin-top:12px;'><strong>Top 3</strong><ol class='mini-list'>{''.join(extra)}</ol></div>")
    return "".join(items)


def _best_validation_row(frame: pd.DataFrame) -> pd.Series | None:
    if frame.empty:
        return None
    return frame.sort_values(by=["latest_outperformance", "latest_return", "observations"], ascending=[False, False, False]).iloc[0]


def _worst_validation_row(frame: pd.DataFrame) -> pd.Series | None:
    if frame.empty:
        return None
    return frame.sort_values(by=["latest_outperformance", "latest_return", "observations"], ascending=[True, True, False]).iloc[0]


def _fmt_signed(value: object) -> str:
    numeric = _num(value)
    if numeric == 0:
        return "0.0%"
    sign = "+" if numeric > 0 else ""
    return f"{sign}{numeric:.1f}%"


def _fmt_percent(value: object) -> str:
    numeric = _num(value)
    return f"{numeric:.1f}%"


def _frame_to_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "데이터 없음"
    render = frame.copy()
    for column in render.columns:
        render[column] = render[column].apply(_markdown_cell)
    header = "| " + " | ".join(str(column) for column in render.columns) + " |"
    divider = "| " + " | ".join("---" for _ in render.columns) + " |"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in render.itertuples(index=False, name=None)
    ]
    return "\n".join([header, divider, *rows])


def _markdown_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _build_markdown(
    settings: Settings,
    trading_date: date,
    equities: list[EquitySnapshot],
    frame: pd.DataFrame,
) -> str:
    working = _normalize_frame(frame)
    portfolio = _load_portfolio_frame(settings, working)
    history = _load_recent_top_counts(settings, trading_date)
    summary = _summary_metrics(equities, working)
    buy_review = working[working["recommendation_bucket"] == "실매수 검토"].sort_values(
        by=["final_score", "estimate_revision_score", "business_quality_score"],
        ascending=False,
    )
    value_core = buy_review[buy_review["core_bucket"].fillna("") == "Value Core"]
    growth_core = buy_review[buy_review["core_bucket"].fillna("") == "Growth Core"]
    leader_top = working[working["leader_bucket"].fillna("") == "Leader"].sort_values(
        by=["leader_cycle_score", "returns_3m_pct", "trend_support_score"],
        ascending=False,
    )
    leader_candidate = working[working["leader_bucket"].fillna("") == "Leader Candidate"].sort_values(
        by=["leader_cycle_score", "estimate_revision_score", "trend_support_score"],
        ascending=False,
    )
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
    issue_focus = _issue_focus_rows(working, limit=12)
    special_dividend_watch = _special_dividend_watchlist(working, limit=12)
    portfolio_markdown = _portfolio_section_markdown(portfolio)

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
        f"- Cycle Leader: {summary['leader_count']} 종목",
        f"- Leader Candidate: {summary['leader_candidate_count']} 종목",
        f"- 소액 관찰: {summary['small_watch']} 종목",
        f"- 가치함정 경고: {summary['trap_watch']} 종목",
        f"- Historical cache assists: {summary['cache_rows']} 종목",
    ]
    if portfolio_markdown:
        parts.extend(["", portfolio_markdown])
    parts.extend([
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
        "### Cycle Leader",
        _bullet_summary(leader_top.head(10), score_column="leader_cycle_score"),
        "",
        "### Leader Candidate",
        _bullet_summary(leader_candidate.head(10), score_column="leader_cycle_score"),
        "",
        "### 소액 관찰",
        _bullet_summary(small_watch.head(10), score_column="final_score"),
        "",
        "### 가치함정 경고",
        _bullet_summary(trap_watch.head(10), score_column="value_trap_risk_score"),
        "",
        "## Today's Important Issues",
        _issue_digest_markdown(issue_focus),
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
    ])
    return "\n".join(parts)


def _build_html(
    settings: Settings,
    trading_date: date,
    equities: list[EquitySnapshot],
    frame: pd.DataFrame,
) -> str:
    working = _normalize_frame(frame)
    portfolio = _load_portfolio_frame(settings, working)
    history = _load_recent_top_counts(settings, trading_date)
    summary = _summary_metrics(equities, working)
    buy_review = working[working["recommendation_bucket"] == "실매수 검토"].sort_values(
        by=["final_score", "estimate_revision_score", "business_quality_score"],
        ascending=False,
    )
    value_core = buy_review[buy_review["core_bucket"].fillna("") == "Value Core"]
    growth_core = buy_review[buy_review["core_bucket"].fillna("") == "Growth Core"]
    leader_top = working[working["leader_bucket"].fillna("") == "Leader"].sort_values(
        by=["leader_cycle_score", "returns_3m_pct", "trend_support_score"],
        ascending=False,
    )
    leader_candidate = working[working["leader_bucket"].fillna("") == "Leader Candidate"].sort_values(
        by=["leader_cycle_score", "estimate_revision_score", "trend_support_score"],
        ascending=False,
    )
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
    issue_focus = _issue_focus_rows(working, limit=8)
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
        ("Cycle Leader", f"{summary['leader_count']:,}"),
        ("Leader Cand.", f"{summary['leader_candidate_count']:,}"),
        ("소액 관찰", f"{summary['small_watch']:,}"),
        ("가치함정 경고", f"{summary['trap_watch']:,}"),
        ("핵심 데이터 부족", f"{summary['core_missing']:,}"),
        ("캐시 보강 종목", f"{summary['cache_rows']:,}"),
        ("급등 제외 종목", f"{summary['excluded']:,}"),
    ]

    missing_counts = _top_missing_counts(working)
    definitions_html = _bucket_definitions_html()
    conviction_html = _conviction_grid(pd.concat([leader_top.head(2), value_core.head(1), growth_core.head(1)], ignore_index=True))
    quick_review = _card_grid(buy_review.head(8), "final_score", accent="value")
    quick_leader = _card_grid(leader_top.head(8), "leader_cycle_score", accent="growth")
    quick_leader_candidate = _card_grid(leader_candidate.head(8), "leader_cycle_score", accent="growth")
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
    issue_focus_html = _issue_digest_html(issue_focus)
    special_watch_html = _html_table(special_dividend_watch, bucket="special_dividend")
    spotlight_html = _spotlight_strip(value_top, growth_top, leader_top)
    portfolio_html = _portfolio_section_html(portfolio)
    universe_json = json.dumps(_records_for_ui(full_list), ensure_ascii=False)
    explorer_theme_chips = _explorer_theme_chips_html(full_list)
    value_table = _html_table(value_top, bucket="value")
    growth_table = _html_table(growth_top, bucket="growth")
    summary_html = "".join(
        f'<div class="metric-card"><span class="metric-label">{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in summary_cards[:6]
    )
    missing_html = "".join(
        f'<span class="chip">{escape(name)} {count}</span>' for name, count in missing_counts
    )
    dashboard_html = _summary_dashboard_html(
        working=working,
        summary=summary,
        buy_review=buy_review,
        value_core=value_core,
        growth_core=growth_core,
        leader_top=leader_top,
        leader_candidate=leader_candidate,
        small_watch=small_watch,
        trap_watch=trap_watch,
    )
    detail_focus = _build_detail_focus_rows(
        value_core=value_core,
        growth_core=growth_core,
        leader_top=leader_top,
        leader_candidate=leader_candidate,
        small_watch=small_watch,
        trap_watch=trap_watch,
    )
    detail_deck_html = _detail_deck_html(detail_focus)

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
    .jump-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}
    .jump-link {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.78);
      color: var(--text);
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
    }}
    .tab-nav {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }}
    .tab-button {{
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,0.74);
      color: var(--muted);
      padding: 10px 16px;
      font: inherit;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }}
    .tab-button.active {{
      background: linear-gradient(135deg, rgba(15,118,110,0.12), rgba(255,255,255,0.95));
      color: var(--text);
      border-color: rgba(15,118,110,0.22);
      box-shadow: inset 0 0 0 1px rgba(15,118,110,0.10);
    }}
    .tab-panels {{
      margin-top: 20px;
    }}
    .tab-panel {{
      display: none;
    }}
    .tab-panel.active {{
      display: block;
    }}
    .section-stack {{
      display: grid;
      gap: 20px;
    }}
    .keyword-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }}
    .subtab-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }}
    .subtab-button {{
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,0.68);
      color: var(--muted);
      padding: 8px 12px;
      font: inherit;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }}
    .subtab-button.active {{
      background: rgba(28,26,24,0.92);
      color: #fff;
      border-color: rgba(28,26,24,0.92);
    }}
    .subtab-panel {{
      display: none;
    }}
    .subtab-panel.active {{
      display: block;
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
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 16px;
    }}
    .dashboard-panel {{
      border-radius: 20px;
      padding: 18px;
      background: rgba(255,255,255,0.72);
      border: 1px solid var(--line);
    }}
    .dashboard-panel h3 {{
      margin: 0 0 12px;
      font-size: 18px;
    }}
    .bar-list {{
      display: grid;
      gap: 10px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 110px 1fr 48px;
      gap: 10px;
      align-items: center;
      font-size: 13px;
    }}
    .bar-track {{
      width: 100%;
      height: 10px;
      border-radius: 999px;
      background: rgba(28,26,24,0.08);
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--value), #14b8a6);
    }}
    .bar-fill.growth {{ background: linear-gradient(90deg, var(--growth), #f59e0b); }}
    .bar-fill.danger {{ background: linear-gradient(90deg, var(--danger), #ef4444); }}
    .mini-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .mini-table th, .mini-table td {{
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
    }}
    .mini-table th {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background: transparent;
      position: static;
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
    .issue-line {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
      border-top: 1px dashed rgba(44, 36, 27, 0.10);
      padding-top: 10px;
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
    a.stock-link {{
      color: inherit;
      text-decoration: none;
      border-bottom: 1px dashed rgba(44, 36, 27, 0.18);
    }}
    a.stock-link:hover {{
      color: var(--value);
      border-bottom-color: var(--value);
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
    .detail-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .detail-card {{
      border-radius: 20px;
      padding: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.76);
    }}
    .detail-card:target {{
      outline: 2px solid rgba(15, 118, 110, 0.24);
      box-shadow: 0 0 0 6px rgba(15, 118, 110, 0.08);
    }}
    .detail-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: start;
    }}
    .detail-facts {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .detail-facts div {{
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(255,255,255,0.88);
      border: 1px solid var(--line);
      font-size: 13px;
      color: var(--muted);
    }}
    .detail-facts strong {{
      display: block;
      color: var(--text);
      margin-top: 4px;
      font-size: 17px;
    }}
    @media (max-width: 1100px) {{
      .metric-grid, .memo-grid, .card-grid, .definition-grid, .detail-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .dashboard-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 720px) {{
      .shell {{ width: min(100vw - 20px, 100%); margin: 12px auto 28px; }}
      .hero, .section {{ padding: 18px; border-radius: 20px; }}
      .metric-grid, .memo-grid, .card-grid, .definition-grid, .detail-grid {{ grid-template-columns: 1fr; }}
      .controls input, .controls select {{ width: 100%; min-width: 0; }}
      .bar-row {{ grid-template-columns: 88px 1fr 40px; }}
      .detail-facts {{ grid-template-columns: 1fr 1fr; }}
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
          <div class="hero-note">먼저 `Cycle Leader`와 `Leader Candidate`를 보고, 그 다음 `Value Core`와 `Growth Core`를 확인하면 됩니다. 점수보다 이번 사이클에서 누가 실제로 앞서가는지 먼저 읽는 구조입니다.</div>
          <div class="jump-row">
            <a class="jump-link" href="#tab-main" data-tab-link="main">메인 읽기</a>
            <a class="jump-link" href="#tab-keywords" data-tab-link="keywords">키워드 파고들기</a>
            <a class="jump-link" href="#tab-detail" data-tab-link="detail">상세 보기</a>
            <a class="jump-link" href="#candidate-explorer" data-tab-link="detail">탐색기 열기</a>
            <a class="jump-link" href="validation.html">검증 보기</a>
          </div>
          <div class="tab-nav" role="tablist" aria-label="리포트 탭">
            <button class="tab-button active" type="button" data-tab="main" role="tab" aria-selected="true">메인</button>
            <button class="tab-button" type="button" data-tab="keywords" role="tab" aria-selected="false">키워드</button>
            <button class="tab-button" type="button" data-tab="detail" role="tab" aria-selected="false">상세</button>
          </div>
        </div>
      </div>
      <div class="metric-grid">{summary_html}</div>
    </section>
      <div class="tab-panels">
      <div class="tab-panel active" id="tab-main" data-tab-panel="main">
        <section class="section">
          <div class="section-head">
            <h2>메인 뷰</h2>
            <span>오늘 결론을 네 개 시야로 나눠서 봅니다.</span>
          </div>
          <div class="subtab-nav" data-subtab-nav="main">
            <button class="subtab-button active" type="button" data-subtab-group="main" data-subtab="dashboard">요약 보드</button>
            <button class="subtab-button" type="button" data-subtab-group="main" data-subtab="spotlight">대표 축</button>
            <button class="subtab-button" type="button" data-subtab-group="main" data-subtab="memo">행동 메모</button>
            <button class="subtab-button" type="button" data-subtab-group="main" data-subtab="conviction">컨빅션</button>
          </div>
          <div class="subtab-panel active" data-subtab-panel="main" data-subtab-name="dashboard" id="summary-dashboard">
            <div class="section-head">
              <h2>한눈에 보기</h2>
              <span>오늘 무엇을 먼저 읽어야 하는지 메인 흐름만 남겼습니다.</span>
            </div>
            {dashboard_html}
          </div>
          <div class="subtab-panel" data-subtab-panel="main" data-subtab-name="spotlight">
            <div class="section-head">
              <h2>오늘의 대표 축</h2>
              <span>주도주, 재평가 후보, 핵심 매수축을 먼저 봅니다.</span>
            </div>
            <div class="card-grid">{spotlight_html}</div>
          </div>
          <div class="subtab-panel" data-subtab-panel="main" data-subtab-name="memo">
            <div class="section-head">
              <h2>오늘의 메모</h2>
              <span>실제 행동 기준으로 네 그룹만 읽으면 됩니다.</span>
            </div>
            {portfolio_html}
            <div class="memo-grid">
              {memo_value_core_html}
              {memo_growth_core_html}
              {memo_watch_html}
              {memo_trap_html}
            </div>
          </div>
          <div class="subtab-panel" data-subtab-panel="main" data-subtab-name="conviction">
            <div class="section-head">
              <h2>컨빅션 노트</h2>
              <span>왜 상단에 남았는지 점수축과 추천 이유를 같이 보여줍니다.</span>
            </div>
            <div class="card-grid">{conviction_html}</div>
          </div>
        </section>
      </div>
      <div class="tab-panel" id="tab-keywords" data-tab-panel="keywords">
        <section class="section">
          <div class="section-head">
            <h2>키워드 탐색</h2>
            <span>정의, 이슈, 렌즈, 표를 분리해서 바로 들어갑니다.</span>
          </div>
          <div class="subtab-nav" data-subtab-nav="keywords">
            <button class="subtab-button active" type="button" data-subtab-group="keywords" data-subtab="definitions">분류 정의</button>
            <button class="subtab-button" type="button" data-subtab-group="keywords" data-subtab="issues">중요 이슈</button>
            <button class="subtab-button" type="button" data-subtab-group="keywords" data-subtab="lenses">렌즈 카드</button>
            <button class="subtab-button" type="button" data-subtab-group="keywords" data-subtab="tables">핵심 표</button>
            <button class="subtab-button" type="button" data-subtab-group="keywords" data-subtab="health">운영 상태</button>
          </div>
          <div class="subtab-panel active" data-subtab-panel="keywords" data-subtab-name="definitions" id="keyword-definitions">
            <div class="definition-grid">
              {definitions_html}
            </div>
          </div>
          <div class="subtab-panel" data-subtab-panel="keywords" data-subtab-name="issues" id="keyword-issues">
            <div class="section-head">
              <h2>오늘의 중요 이슈</h2>
              <span>뉴스와 공시에서 종목명 기준으로 걸러낸 핵심 변화입니다.</span>
            </div>
            <div class="card-grid">{issue_focus_html}</div>
          </div>
          <div class="subtab-panel" data-subtab-panel="keywords" data-subtab-name="lenses" id="keyword-lenses">
            <div class="section-head">
              <h2>렌즈 카드</h2>
              <span>같은 종목군을 다른 프레임으로 다시 읽습니다.</span>
            </div>
            <div class="section-head" style="margin-top:6px;">
              <h2>Core 카드</h2>
              <span>실매수 후보와 리더 축을 먼저 정리했습니다.</span>
            </div>
            <div class="card-grid">{quick_review}</div>
            <div class="section-head" style="margin-top:22px;">
              <h2>Cycle Leader / Candidate</h2>
              <span>이번 사이클의 실제 리더와 진입 후보입니다.</span>
            </div>
            <div class="card-grid">{quick_leader}</div>
            <div class="card-grid" style="margin-top:14px;">{quick_leader_candidate}</div>
            <div class="section-head" style="margin-top:22px;">
              <h2>Value / Growth Lenses</h2>
              <span>스타일별로 다시 압축했습니다.</span>
            </div>
            <div class="card-grid">{deep_value_html}{dividend_compounder_html}{turnaround_value_html}{growth_proven_html}{growth_speculative_html}{missed_leader_html}{quick_watch}{trap_watch_html}</div>
          </div>
          <div class="subtab-panel" data-subtab-panel="keywords" data-subtab-name="tables" id="keyword-tables">
            <div class="section-head">
              <h2>핵심 표</h2>
              <span>숫자로 직접 비교할 때 보는 표입니다.</span>
            </div>
            <div class="section-head" style="margin-top:6px;">
              <h2>Top Value 20</h2>
              <span>압축한 가치주 표</span>
            </div>
            <div class="table-wrap">{value_table}</div>
            <div class="section-head" style="margin-top:22px;">
              <h2>Top Growth 20</h2>
              <span>과열 여부와 52주 위치를 함께 봅니다.</span>
            </div>
            <div class="table-wrap">{growth_table}</div>
            <div class="section-head" style="margin-top:22px;">
              <h2>Special Dividend Watch</h2>
              <span>최근 배당 착시 가능성이 있는 종목입니다.</span>
            </div>
            <div class="table-wrap">{special_watch_html}</div>
          </div>
          <div class="subtab-panel" data-subtab-panel="keywords" data-subtab-name="health" id="keyword-health">
            <div class="section-head">
              <h2>운영 상태</h2>
              <span>가장 많이 비는 항목과 시스템 상태를 봅니다.</span>
            </div>
            <div class="chip-row">{missing_html}</div>
          </div>
        </section>
      </div>
      <div class="tab-panel" id="tab-detail" data-tab-panel="detail">
        <section class="section">
          <div class="section-head">
            <h2>상세 뷰</h2>
            <span>탐색과 종목 상세를 분리해 한 번에 한 작업만 하게 했습니다.</span>
          </div>
          <div class="subtab-nav" data-subtab-nav="detail">
            <button class="subtab-button active" type="button" data-subtab-group="detail" data-subtab="explorer">탐색기</button>
            <button class="subtab-button" type="button" data-subtab-group="detail" data-subtab="cards">상세 카드</button>
          </div>
          <div class="subtab-panel active" data-subtab-panel="detail" data-subtab-name="explorer">
            <div class="section-head">
              <h2 id="candidate-explorer">Candidate Explorer</h2>
              <span>상위 200개 비제외 종목을 검색하고 상세 카드로 이동합니다.</span>
            </div>
            <div class="explorer-summary">
              <span class="chip strong">탐색 대상 {len(full_list):,}개</span>
              <span class="chip">정렬 기준 최종점수</span>
              <span class="chip">기본값은 실매수·관찰·경고만 표시</span>
            </div>
            <div class="chip-row" id="themeQuickFilters">{explorer_theme_chips}</div>
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
              <select id="themeFilter">
                <option value="">테마 전체</option>
              </select>
              <select id="subThemeFilter">
                <option value="">하위테마 전체</option>
              </select>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>종목</th>
                    <th>시장</th>
                    <th>업종</th>
                    <th>테마 / 하위테마</th>
                    <th>신뢰도</th>
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
                    <th>Leader</th>
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
          <div class="subtab-panel" data-subtab-panel="detail" data-subtab-name="cards">
            <div class="section-head">
              <h2 id="detail-deck">종목 상세 카드</h2>
              <span>메인과 키워드 탭에서 고른 종목을 여기서 자세히 읽습니다.</span>
            </div>
            <div class="detail-grid">{detail_deck_html}</div>
          </div>
        </section>
      </div>
    </div>
  </div>
  <script>
    const universeRows = {universe_json};
    const body = document.getElementById("universeBody");
    const searchInput = document.getElementById("searchInput");
    const bucketFilter = document.getElementById("bucketFilter");
    const marketFilter = document.getElementById("marketFilter");
    const stageFilter = document.getElementById("stageFilter");
    const themeFilter = document.getElementById("themeFilter");
    const subThemeFilter = document.getElementById("subThemeFilter");
    const tabButtons = Array.from(document.querySelectorAll("[data-tab]"));
    const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
    const subtabButtons = Array.from(document.querySelectorAll("[data-subtab-group]"));
    const subtabPanels = Array.from(document.querySelectorAll("[data-subtab-panel]"));
    const themeQuickButtons = Array.from(document.querySelectorAll("[data-theme-filter]"));

    function activateTab(tabName, updateHash = false) {{
      tabButtons.forEach((button) => {{
        const active = button.dataset.tab === tabName;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
      }});
      tabPanels.forEach((panel) => {{
        panel.classList.toggle("active", panel.dataset.tabPanel === tabName);
      }});
      if (updateHash) {{
        const targetHash = `tab-${{tabName}}`;
        if (window.location.hash !== `#${{targetHash}}`) {{
          history.replaceState(null, "", `#${{targetHash}}`);
        }}
      }}
    }}

    function activateSubtab(groupName, subtabName) {{
      subtabButtons.forEach((button) => {{
        const active = button.dataset.subtabGroup === groupName && button.dataset.subtab === subtabName;
        if (button.dataset.subtabGroup === groupName) {{
          button.classList.toggle("active", active);
        }}
      }});
      subtabPanels.forEach((panel) => {{
        const active = panel.dataset.subtabPanel === groupName && panel.dataset.subtabName === subtabName;
        if (panel.dataset.subtabPanel === groupName) {{
          panel.classList.toggle("active", active);
        }}
      }});
    }}

    function tabForHash(hash) {{
      if (!hash) return "main";
      if (hash === "#tab-keywords") return "keywords";
      if (hash === "#tab-detail") return "detail";
      if (hash.startsWith("#detail-") || hash === "#detail-deck" || hash === "#candidate-explorer") return "detail";
      if (hash.startsWith("#keyword-")) return "keywords";
      return "main";
    }}

    function stageBadge(stage) {{
      return `<span class="stage stage-${{stage || '초입'}}">${{stage || '-'}}</span>`;
    }}

    function fmt(value, suffix = "") {{
      if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "-";
      return `${{Number(value).toLocaleString("ko-KR", {{ maximumFractionDigits: 2 }})}}${{suffix}}`;
    }}

    function detailHref(row) {{
      return row.ticker ? `#detail-${{row.ticker}}` : "#detail-deck";
    }}

    function populateThemeFilters() {{
      const themes = Array.from(new Set(universeRows.map((row) => row.theme || "미분류"))).sort((a, b) => a.localeCompare(b, "ko"));
      const subThemes = Array.from(
        new Set(
          universeRows
            .map((row) => row.sub_theme || "")
            .filter((value) => value)
        )
      ).sort((a, b) => a.localeCompare(b, "ko"));

      themeFilter.innerHTML = ['<option value="">테마 전체</option>']
        .concat(themes.map((theme) => `<option value="${{theme}}">${{theme}}</option>`))
        .join("");
      subThemeFilter.innerHTML = ['<option value="">하위테마 전체</option>']
        .concat(subThemes.map((theme) => `<option value="${{theme}}">${{theme}}</option>`))
        .join("");
    }}

    function renderUniverse() {{
      const q = searchInput.value.trim().toLowerCase();
      const bucket = bucketFilter.value;
      const market = marketFilter.value;
      const stage = stageFilter.value;
      const theme = themeFilter.value;
      const subTheme = subThemeFilter.value;
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
        const matchTheme = !theme || (row.theme || "미분류") === theme;
        const matchSubTheme = !subTheme || (row.sub_theme || "") === subTheme;
        return matchQuery && matchBucket && matchMarket && matchStage && matchTheme && matchSubTheme;
      }});

      body.innerHTML = filtered.map((row) => `
        <tr>
          <td><strong><a class="stock-link" href="${{detailHref(row)}}">${{row.name}}</a></strong><div class="subtle">${{row.ticker}}</div></td>
          <td>${{row.market || "-"}}</td>
          <td>${{row.sector || "-"}}</td>
          <td><strong>${{row.theme || "미분류"}}</strong><div class="subtle">${{row.sub_theme || "-"}}</div></td>
          <td>${{row.theme_confidence || "-"}}</td>
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
          <td>${{row.leader_bucket || "-"}}</td>
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
    themeFilter.addEventListener("change", renderUniverse);
    subThemeFilter.addEventListener("change", renderUniverse);
    themeQuickButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const theme = button.getAttribute("data-theme-filter") || "";
        themeFilter.value = theme;
        subThemeFilter.value = "";
        activateTab("detail", false);
        activateSubtab("detail", "explorer");
        renderUniverse();
      }});
    }});
    tabButtons.forEach((button) => {{
      button.addEventListener("click", () => activateTab(button.dataset.tab, true));
    }});
    document.querySelectorAll("[data-tab-link]").forEach((link) => {{
      link.addEventListener("click", () => {{
        const tabName = link.getAttribute("data-tab-link");
        if (tabName) activateTab(tabName, false);
      }});
    }});
    subtabButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        activateSubtab(button.dataset.subtabGroup, button.dataset.subtab);
      }});
    }});
    window.addEventListener("hashchange", () => {{
      activateTab(tabForHash(window.location.hash), false);
      if (window.location.hash === "#candidate-explorer") activateSubtab("detail", "explorer");
      if (window.location.hash === "#detail-deck" || window.location.hash.startsWith("#detail-")) activateSubtab("detail", "cards");
      if (window.location.hash.startsWith("#keyword-definitions")) activateSubtab("keywords", "definitions");
      if (window.location.hash.startsWith("#keyword-issues")) activateSubtab("keywords", "issues");
      if (window.location.hash.startsWith("#keyword-lenses")) activateSubtab("keywords", "lenses");
      if (window.location.hash.startsWith("#keyword-tables")) activateSubtab("keywords", "tables");
      if (window.location.hash.startsWith("#keyword-health")) activateSubtab("keywords", "health");
    }});
    activateTab(tabForHash(window.location.hash), false);
    activateSubtab("main", "dashboard");
    activateSubtab("keywords", "definitions");
    activateSubtab("detail", "explorer");
    if (window.location.hash === "#candidate-explorer") activateSubtab("detail", "explorer");
    if (window.location.hash === "#detail-deck" || window.location.hash.startsWith("#detail-")) activateSubtab("detail", "cards");
    if (window.location.hash.startsWith("#keyword-issues")) activateSubtab("keywords", "issues");
    if (window.location.hash.startsWith("#keyword-lenses")) activateSubtab("keywords", "lenses");
    if (window.location.hash.startsWith("#keyword-tables")) activateSubtab("keywords", "tables");
    if (window.location.hash.startsWith("#keyword-health")) activateSubtab("keywords", "health");
    populateThemeFilters();
    renderUniverse();
  </script>
</body>
</html>"""


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    defaults = (
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
        ("trend_support_score", 0),
        ("missed_leader_score", 0),
        ("final_score", 0),
        ("important_news_items", ""),
        ("important_disclosures", ""),
        ("theme", "미분류"),
        ("sub_theme", ""),
        ("theme_score", 0),
        ("theme_confidence", "낮음"),
        ("theme_gate_pass", False),
        ("theme_evidence", ""),
        ("recommendation_bucket", ""),
        ("core_bucket", ""),
        ("leader_bucket", ""),
        ("recommendation_reasons", ""),
        ("value_style", ""),
        ("growth_style", ""),
        ("tags", ""),
        ("missing_data", ""),
        ("source_notes", ""),
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
        ("leader_bucket", ""),
        ("recommendation_reasons", ""),
        ("repeat_top_count", 0),
        ("source_notes", ""),
        ("missing_data", ""),
        ("tags", ""),
    )
    for column, default in defaults:
        if column not in working.columns:
            working[column] = default
        elif isinstance(default, str):
            working[column] = working[column].fillna("").astype(str)
            working.loc[working[column].str.lower() == "nan", column] = ""
        elif isinstance(default, bool):
            working[column] = working[column].fillna(False)
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
        "trend_support_score",
        "missed_leader_score",
        "leader_cycle_score",
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
    leader_count = int((working["leader_bucket"].fillna("") == "Leader").sum()) if "leader_bucket" in working.columns else 0
    leader_candidate_count = int((working["leader_bucket"].fillna("") == "Leader Candidate").sum()) if "leader_bucket" in working.columns else 0
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
        "leader_count": leader_count,
        "leader_candidate_count": leader_candidate_count,
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


def _load_portfolio_frame(settings: Settings, working: pd.DataFrame) -> pd.DataFrame | None:
    if not settings.portfolio_overlay_enabled:
        return None

    path = settings.data_dir / "portfolio_positions.csv"
    if not path.exists():
        return None

    try:
        portfolio = pd.read_csv(path, encoding="utf-8-sig", dtype={"ticker": str})
    except Exception:
        return None
    if portfolio.empty or "ticker" not in portfolio.columns:
        return None

    portfolio = portfolio.rename(columns=lambda value: str(value).strip())
    portfolio["ticker"] = (
        portfolio["ticker"]
        .fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )
    digit_mask = portfolio["ticker"].str.fullmatch(r"\d+")
    portfolio.loc[digit_mask, "ticker"] = portfolio.loc[digit_mask, "ticker"].str.zfill(6)
    portfolio = portfolio[portfolio["ticker"] != ""].copy()
    if portfolio.empty:
        return None

    text_defaults = {
        "name": "",
        "market_scope": "",
        "asset_class": "",
        "country": "",
        "theme": "미분류",
        "sub_theme": "",
        "strategy": "",
        "style_bucket": "",
        "trend_view": "",
        "cycle_view": "",
        "conviction": "",
        "fx_exposure": "",
        "timing_view": "",
        "planned_action": "",
        "notes": "",
    }
    for column, default in text_defaults.items():
        if column not in portfolio.columns:
            portfolio[column] = default
        portfolio[column] = portfolio[column].fillna(default).astype(str).str.strip()
        portfolio.loc[portfolio[column] == "", column] = default

    for column in ("actual_weight_pct", "target_weight_pct", "avg_buy_price"):
        if column not in portfolio.columns:
            portfolio[column] = pd.NA
        portfolio[column] = pd.to_numeric(portfolio[column], errors="coerce")

    market_columns = [
        "ticker",
        "name",
        "market",
        "sector",
        "size_bucket",
        "prev_close",
        "returns_6m_pct",
        "final_score",
        "core_bucket",
        "leader_bucket",
        "recommendation_bucket",
        "stage",
        "tags",
        "important_news_items",
        "important_disclosures",
        "missing_data",
        "excluded",
    ]
    available_columns = [column for column in market_columns if column in working.columns]
    screen_lookup = working[available_columns].copy()
    merged = portfolio.merge(
        screen_lookup.drop_duplicates(subset=["ticker"]),
        on="ticker",
        how="left",
        suffixes=("", "_screen"),
    )
    if "name" in screen_lookup.columns:
        missing_match = merged["market"].isna() if "market" in merged.columns else pd.Series(False, index=merged.index)
        if missing_match.any():
            by_name = screen_lookup.drop_duplicates(subset=["name"]).add_suffix("_by_name")
            merged = merged.merge(
                by_name,
                left_on="name",
                right_on="name_by_name",
                how="left",
            )
            for column in available_columns:
                if column == "name":
                    continue
                base = column
                fallback = f"{column}_by_name"
                if base in merged.columns and fallback in merged.columns:
                    merged.loc[missing_match, base] = merged.loc[missing_match, base].where(
                        merged.loc[missing_match, base].notna(),
                        merged.loc[missing_match, fallback],
                    )
            drop_columns = [f"{column}_by_name" for column in available_columns if f"{column}_by_name" in merged.columns]
            merged = merged.drop(columns=drop_columns, errors="ignore")
    merged["display_name"] = merged["name"].where(merged["name"].ne(""), merged.get("name_screen", ""))
    merged["display_name"] = merged["display_name"].fillna(merged.get("name_screen", "")).replace("", "-")
    derived = merged.apply(_derive_portfolio_classification, axis=1, result_type="expand")
    for column in derived.columns:
        empty_mask = merged[column].fillna("").astype(str).str.strip().eq("")
        merged.loc[empty_mask, column] = derived.loc[empty_mask, column]
    merged["theme"] = merged["theme"].replace("", "미분류")
    merged["rebalance_gap_pct"] = merged["target_weight_pct"] - merged["actual_weight_pct"]
    merged["action_bucket"] = merged.apply(_portfolio_action_bucket, axis=1)
    merged["review_priority"] = merged["action_bucket"].map(
        {
            "정리 검토": 0,
            "비중축소 검토": 1,
            "추가매수 검토": 2,
            "보유/관찰": 3,
            "정보 확인": 4,
            "보유 유지": 5,
        }
    ).fillna(9)
    merged["review_signal"] = merged.apply(_portfolio_review_signal, axis=1)
    return merged.sort_values(
        by=["review_priority", "actual_weight_pct", "final_score"],
        ascending=[True, False, False],
        na_position="last",
    ).reset_index(drop=True)


def _portfolio_action_bucket(row: pd.Series) -> str:
    planned = str(row.get("planned_action", "") or "").strip()
    if planned:
        return planned

    recommendation_bucket = str(row.get("recommendation_bucket", "") or "")
    core_bucket = str(row.get("core_bucket", "") or "")
    stage = str(row.get("stage", "") or "")
    gap = row.get("rebalance_gap_pct", pd.NA)
    excluded = bool(row.get("excluded", False))

    if recommendation_bucket == "제외" or excluded:
        return "정리 검토"
    if recommendation_bucket == "가치함정 경고" or stage == "과열":
        return "비중축소 검토"
    if pd.notna(gap):
        if gap >= 1.0:
            return "추가매수 검토"
        if gap <= -1.0:
            return "비중축소 검토"
    if core_bucket in {"Value Core", "Growth Core"} and stage in {"초입", "중간"}:
        return "추가매수 검토"
    if recommendation_bucket == "소액 관찰":
        return "보유/관찰"
    if recommendation_bucket in {"보류", ""}:
        return "정보 확인"
    return "보유 유지"


def _portfolio_review_signal(row: pd.Series) -> str:
    parts: list[str] = []
    gap = row.get("rebalance_gap_pct", pd.NA)
    if pd.notna(gap) and abs(float(gap)) >= 1.0:
        direction = "언더" if float(gap) > 0 else "오버"
        parts.append(f"목표 대비 {direction}웨이트 {abs(float(gap)):.1f}%p")

    core_bucket = str(row.get("core_bucket", "") or "")
    recommendation_bucket = str(row.get("recommendation_bucket", "") or "")
    leader_bucket = str(row.get("leader_bucket", "") or "")
    stage = str(row.get("stage", "") or "")
    if leader_bucket == "Leader":
        parts.append("사이클 선도주")
    elif leader_bucket == "Leader Candidate":
        parts.append("리더 후보")
    elif core_bucket:
        parts.append(core_bucket)
    elif recommendation_bucket:
        parts.append(recommendation_bucket)
    if stage:
        parts.append(f"stage {stage}")
    trend_view = str(row.get("trend_view", "") or "").strip()
    if trend_view and trend_view not in {"-", ""}:
        parts.append(trend_view)

    note = str(row.get("notes", "") or "").strip()
    if note and note != "-":
        parts.append(note)
    return " / ".join(parts[:3])


def _derive_portfolio_classification(row: pd.Series) -> pd.Series:
    ticker = str(row.get("ticker", "") or "").strip()
    name = str(row.get("display_name", row.get("name", "")) or "").strip()
    market = str(row.get("market", "") or "").strip()
    stage = str(row.get("stage", "") or "").strip()
    strategy = str(row.get("strategy", "") or "").strip()
    theme = str(row.get("theme", "") or "").strip()
    market_scope = str(row.get("market_scope", "") or "").strip()
    asset_class = str(row.get("asset_class", "") or "").strip()
    country = str(row.get("country", "") or "").strip()
    style_bucket = str(row.get("style_bucket", "") or "").strip()
    cycle_view = str(row.get("cycle_view", "") or "").strip()
    trend_view = str(row.get("trend_view", "") or "").strip()
    conviction = str(row.get("conviction", "") or "").strip()
    fx_exposure = str(row.get("fx_exposure", "") or "").strip()

    etf_keywords = ("KODEX", "TIGER", "KOACT", "KoAct", "KIWOOM", "ACE", "ARIRANG", "SOL", "TIMEFOLIO")
    if not market_scope:
        if any(keyword in name for keyword in etf_keywords):
            market_scope = "국내"
        elif market in {"KOSPI", "KOSDAQ"} or ticker.isdigit():
            market_scope = "국내"
        else:
            market_scope = "해외"
    if not asset_class:
        asset_class = "ETF" if any(keyword in name for keyword in etf_keywords) else "주식"
    if not country:
        if market_scope == "국내":
            country = "한국"
        elif ticker in {"AAPL", "NVDA", "GOOGL", "META", "SIRI", "TSM", "C", "NKE"}:
            country = "미국"
        else:
            country = "기타해외"
    if not fx_exposure:
        fx_exposure = "높음" if market_scope == "해외" else "낮음"
    if not trend_view:
        trend_view = {
            "초입": "추세 초기",
            "중간": "추세 진행",
            "후반": "추세 후반",
            "과열": "과열 경계",
        }.get(stage, "추세 확인 필요")
    if not cycle_view:
        if str(row.get("leader_bucket", "") or "") == "Leader":
            cycle_view = "주도"
        elif str(row.get("leader_bucket", "") or "") == "Leader Candidate":
            cycle_view = "리더 후보"
        elif stage in {"초입", "중간"}:
            cycle_view = "상승 사이클"
        elif stage == "과열":
            cycle_view = "과열 구간"
        else:
            cycle_view = "중립"
    if not conviction:
        actual = _num(row.get("actual_weight_pct", None))
        conviction = "핵심" if actual >= 4.0 else "중간" if actual >= 2.0 else "위성"
    if not style_bucket:
        if asset_class == "ETF":
            style_bucket = "패시브"
        elif "배당" in strategy or "금융" in theme:
            style_bucket = "인컴"
        elif "Growth" in str(row.get("core_bucket", "") or "") or "엔비디아" in name:
            style_bucket = "성장"
        else:
            style_bucket = "혼합"

    return pd.Series(
        {
            "market_scope": market_scope,
            "asset_class": asset_class,
            "country": country,
            "style_bucket": style_bucket,
            "trend_view": trend_view,
            "cycle_view": cycle_view,
            "conviction": conviction,
            "fx_exposure": fx_exposure,
        }
    )


def _portfolio_summary(portfolio: pd.DataFrame) -> dict[str, object]:
    actual_sum = float(portfolio["actual_weight_pct"].dropna().sum()) if "actual_weight_pct" in portfolio.columns else 0.0
    target_sum = float(portfolio["target_weight_pct"].dropna().sum()) if "target_weight_pct" in portfolio.columns else 0.0
    themes = portfolio["theme"].fillna("미분류").replace("", "미분류")
    theme_mix = (
        portfolio.assign(theme=themes)
        .groupby("theme", dropna=False)[["actual_weight_pct", "target_weight_pct"]]
        .sum(min_count=1)
        .fillna(0.0)
        .sort_values("actual_weight_pct", ascending=False)
    )
    action_counts = portfolio["action_bucket"].value_counts().to_dict()
    region_mix = _portfolio_dimension_mix(portfolio, "market_scope")
    asset_mix = _portfolio_dimension_mix(portfolio, "asset_class")
    trend_mix = _portfolio_dimension_mix(portfolio, "trend_view")
    top_themes = []
    for theme, row in theme_mix.head(3).iterrows():
        top_themes.append(f"{theme} {row['actual_weight_pct']:.1f}%")
    return {
        "count": len(portfolio),
        "theme_count": int(themes.nunique()),
        "actual_sum": actual_sum,
        "target_sum": target_sum,
        "top3_theme_weight": float(theme_mix["actual_weight_pct"].head(3).sum()) if not theme_mix.empty else 0.0,
        "top_themes": top_themes,
        "action_counts": action_counts,
        "theme_table": theme_mix.reset_index(),
        "region_table": region_mix.reset_index(),
        "asset_table": asset_mix.reset_index(),
        "trend_table": trend_mix.reset_index(),
    }


def _portfolio_dimension_mix(portfolio: pd.DataFrame, column: str) -> pd.DataFrame:
    label_series = portfolio[column].fillna("미분류").replace("", "미분류")
    return (
        portfolio.assign(**{column: label_series})
        .groupby(column, dropna=False)[["actual_weight_pct", "target_weight_pct"]]
        .sum(min_count=1)
        .fillna(0.0)
        .sort_values("actual_weight_pct", ascending=False)
    )


def _portfolio_section_markdown(portfolio: pd.DataFrame | None) -> str:
    if portfolio is None or portfolio.empty:
        return ""

    summary = _portfolio_summary(portfolio)
    action_counts = summary["action_counts"]
    lines = [
        "## Portfolio Overlay",
        f"- 보유 종목: {summary['count']}개",
        f"- 실제 비중 합계: {summary['actual_sum']:.1f}%",
        f"- 목표 비중 합계: {summary['target_sum']:.1f}%",
        f"- 테마 수: {summary['theme_count']}개",
        f"- 상위 3개 테마 집중도: {summary['top3_theme_weight']:.1f}%",
    ]
    if summary["top_themes"]:
        lines.append(f"- 상위 테마: {', '.join(summary['top_themes'])}")
    if action_counts:
        lines.append(
            "- 액션 버킷: "
            + ", ".join(f"{label} {count}개" for label, count in action_counts.items())
        )

    theme_table = summary["theme_table"].copy()
    theme_table["gap_pct"] = theme_table["target_weight_pct"] - theme_table["actual_weight_pct"]
    region_table = summary["region_table"].copy()
    region_table["gap_pct"] = region_table["target_weight_pct"] - region_table["actual_weight_pct"]
    asset_table = summary["asset_table"].copy()
    asset_table["gap_pct"] = asset_table["target_weight_pct"] - asset_table["actual_weight_pct"]
    trend_table = summary["trend_table"].copy()
    trend_table["gap_pct"] = trend_table["target_weight_pct"] - trend_table["actual_weight_pct"]

    review_columns = [
        "ticker",
        "display_name",
        "market_scope",
        "asset_class",
        "theme",
        "style_bucket",
        "strategy",
        "trend_view",
        "cycle_view",
        "conviction",
        "actual_weight_pct",
        "target_weight_pct",
        "rebalance_gap_pct",
        "action_bucket",
        "core_bucket",
        "recommendation_bucket",
        "stage",
        "review_signal",
    ]
    review_table = portfolio[review_columns].head(15).rename(
        columns={
            "display_name": "name",
            "market_scope": "scope",
            "asset_class": "asset",
            "actual_weight_pct": "actual_weight_pct",
            "target_weight_pct": "target_weight_pct",
            "rebalance_gap_pct": "gap_pct",
            "action_bucket": "action",
            "core_bucket": "core",
            "recommendation_bucket": "screening",
            "review_signal": "signal",
        }
    )
    lines.extend(
        [
            "",
            "### Theme Mix",
            theme_table.to_markdown(index=False),
            "",
            "### Region Mix",
            region_table.to_markdown(index=False),
            "",
            "### Asset / Trend Mix",
            asset_table.to_markdown(index=False),
            "",
            trend_table.to_markdown(index=False),
            "",
            "### Review Queue",
            review_table.to_markdown(index=False),
        ]
    )
    return "\n".join(lines)


def _portfolio_section_html(portfolio: pd.DataFrame | None) -> str:
    if portfolio is None or portfolio.empty:
        return ""

    summary = _portfolio_summary(portfolio)
    metric_cards = [
        ("보유 종목", f"{summary['count']}개"),
        ("실제 비중 합계", f"{summary['actual_sum']:.1f}%"),
        ("목표 비중 합계", f"{summary['target_sum']:.1f}%"),
        ("테마 수", f"{summary['theme_count']}개"),
        ("상위 3테마 집중도", f"{summary['top3_theme_weight']:.1f}%"),
        ("추가/축소/정리", f"{summary['action_counts'].get('추가매수 검토', 0)}/{summary['action_counts'].get('비중축소 검토', 0)}/{summary['action_counts'].get('정리 검토', 0)}"),
    ]
    cards_html = "".join(
        f'<div class="metric-card"><span class="metric-label">{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in metric_cards
    )
    theme_chips = "".join(
        f'<span class="chip">{escape(label)}</span>' for label in summary["top_themes"]
    )
    action_chips = "".join(
        f'<span class="chip strong">{escape(action)} {count}개</span>'
        for action, count in summary["action_counts"].items()
    )

    theme_rows: list[str] = []
    for row in summary["theme_table"].head(8).itertuples(index=False):
        gap = (_num(getattr(row, "target_weight_pct", 0)) - _num(getattr(row, "actual_weight_pct", 0)))
        theme_rows.append(
            f"""
            <tr>
              <td><strong>{escape(str(getattr(row, "theme", "-") or "-"))}</strong></td>
              <td>{escape(_fmt_cell(getattr(row, "actual_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(getattr(row, "target_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(gap))}%p</td>
            </tr>
            """
        )

    region_rows: list[str] = []
    for row in summary["region_table"].head(6).itertuples(index=False):
        gap = (_num(getattr(row, "target_weight_pct", 0)) - _num(getattr(row, "actual_weight_pct", 0)))
        region_rows.append(
            f"""
            <tr>
              <td><strong>{escape(str(getattr(row, "market_scope", "-") or "-"))}</strong></td>
              <td>{escape(_fmt_cell(getattr(row, "actual_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(getattr(row, "target_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(gap))}%p</td>
            </tr>
            """
        )

    asset_rows: list[str] = []
    for row in summary["asset_table"].head(6).itertuples(index=False):
        gap = (_num(getattr(row, "target_weight_pct", 0)) - _num(getattr(row, "actual_weight_pct", 0)))
        asset_rows.append(
            f"""
            <tr>
              <td><strong>{escape(str(getattr(row, "asset_class", "-") or "-"))}</strong></td>
              <td>{escape(_fmt_cell(getattr(row, "actual_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(getattr(row, "target_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(gap))}%p</td>
            </tr>
            """
        )

    trend_rows: list[str] = []
    for row in summary["trend_table"].head(8).itertuples(index=False):
        gap = (_num(getattr(row, "target_weight_pct", 0)) - _num(getattr(row, "actual_weight_pct", 0)))
        trend_rows.append(
            f"""
            <tr>
              <td><strong>{escape(str(getattr(row, "trend_view", "-") or "-"))}</strong></td>
              <td>{escape(_fmt_cell(getattr(row, "actual_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(getattr(row, "target_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(gap))}%p</td>
            </tr>
            """
        )

    review_rows: list[str] = []
    for row in portfolio.head(12).itertuples(index=False):
        review_rows.append(
            f"""
            <tr>
              <td><strong>{escape(str(getattr(row, "display_name", "-") or "-"))}</strong><div class="subtle">{escape(str(getattr(row, "ticker", "-") or "-"))}</div></td>
              <td>{escape(str(getattr(row, "market_scope", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "asset_class", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "theme", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "style_bucket", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "strategy", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "trend_view", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "cycle_view", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "conviction", "-") or "-"))}</td>
              <td>{escape(_fmt_cell(getattr(row, "actual_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(getattr(row, "target_weight_pct", None)))}%</td>
              <td>{escape(_fmt_cell(getattr(row, "rebalance_gap_pct", None)))}%p</td>
              <td>{escape(str(getattr(row, "action_bucket", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "core_bucket", "") or getattr(row, "recommendation_bucket", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "stage", "-") or "-"))}</td>
              <td>{escape(str(getattr(row, "review_signal", "-") or "-"))}</td>
            </tr>
            """
        )

    return f"""
      <div class="section-head" style="margin-top:4px;">
        <h2>포트폴리오 오버레이</h2>
        <span>`data/portfolio_positions.csv`가 있을 때만 보입니다.</span>
      </div>
      <div class="metric-grid">{cards_html}</div>
      <div class="hero-note" style="margin-top:16px;">
        스크리닝 결과를 내 보유 종목에 다시 덮어서, 무엇을 더 사고 줄이고 정리할지 한 번에 보이도록 정리했습니다.
      </div>
      <div class="chip-row" style="margin-top:14px;">{theme_chips}{action_chips}</div>
      <div class="section-head" style="margin-top:22px;">
        <h2>테마 비중</h2>
        <span>실제 비중과 목표 비중 차이</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>테마</th>
              <th>실제 비중</th>
              <th>목표 비중</th>
              <th>갭</th>
            </tr>
          </thead>
          <tbody>{''.join(theme_rows)}</tbody>
        </table>
      </div>
      <div class="section-head" style="margin-top:22px;">
        <h2>지역 / 자산 분류</h2>
        <span>국장/해외, 주식/ETF 기준으로 쪼갠 비중</span>
      </div>
      <div class="memo-grid">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>지역</th>
                <th>실제 비중</th>
                <th>목표 비중</th>
                <th>갭</th>
              </tr>
            </thead>
            <tbody>{''.join(region_rows)}</tbody>
          </table>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>자산</th>
                <th>실제 비중</th>
                <th>목표 비중</th>
                <th>갭</th>
              </tr>
            </thead>
            <tbody>{''.join(asset_rows)}</tbody>
          </table>
        </div>
      </div>
      <div class="section-head" style="margin-top:22px;">
        <h2>추세 분류</h2>
        <span>초기/진행/과열 같은 운영용 추세 뷰</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>추세</th>
              <th>실제 비중</th>
              <th>목표 비중</th>
              <th>갭</th>
            </tr>
          </thead>
          <tbody>{''.join(trend_rows)}</tbody>
        </table>
      </div>
      <div class="section-head" style="margin-top:22px;">
        <h2>리뷰 큐</h2>
        <span>비중 조절과 매수 타이밍을 먼저 점검할 종목</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>종목</th>
              <th>지역</th>
              <th>자산</th>
              <th>테마</th>
              <th>스타일</th>
              <th>전략</th>
              <th>추세</th>
              <th>사이클</th>
              <th>확신도</th>
              <th>실제</th>
              <th>목표</th>
              <th>갭</th>
              <th>액션</th>
              <th>스크리닝</th>
              <th>Stage</th>
              <th>시그널</th>
            </tr>
          </thead>
          <tbody>{''.join(review_rows)}</tbody>
        </table>
      </div>
    """


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
        recommendation_bucket = _bucket_label(row)
        score_text = f"{score:.1f}" if pd.notna(score) else "-"
        returns_text = f"{returns_6m:.1f}%" if pd.notna(returns_6m) else "-"
        tag_text = f" / {tags}" if tags else ""
        issue_text = _issue_summary(row)
        issue_suffix = f" / {issue_text}" if issue_text else ""
        lines.append(
            f"- {row.name} ({row.ticker}) [{sector} {size_bucket}] {recommendation_bucket} / score {score_text}, 6M {returns_text}, stage {stage}{tag_text}{issue_suffix}"
        )
    return "\n".join(lines)


def _issue_digest_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No important issues_"

    lines = []
    for row in frame.itertuples(index=False):
        issue_text = _issue_summary(row)
        if not issue_text:
            continue
        score_text = _fmt_cell(getattr(row, "final_score", None))
        bucket_text = _bucket_label(row)
        lines.append(
            f"- {row.name} ({row.ticker}) [{bucket_text}] score {score_text}: {issue_text}"
        )
    return "\n".join(lines) if lines else "_No important issues_"


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
        issue_text = _issue_summary(row)
        cards.append(
            f"""
            <article class="pick-card {accent}">
              <div class="ticker">{escape(str(row.ticker))}</div>
              <h3><a class="stock-link" href="#{escape(_detail_anchor(getattr(row, 'ticker', '')))}">{escape(str(row.name))}</a></h3>
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
              {f'<div class="issue-line"><strong>이슈</strong> {escape(issue_text)}</div>' if issue_text else ""}
            </article>
            """
        )
    return "".join(cards)


def _issue_digest_html(frame: pd.DataFrame) -> str:
    cards: list[str] = []
    for row in frame.itertuples(index=False):
        issue_text = _issue_summary(row)
        if not issue_text:
            continue
        accent = "growth" if (getattr(row, "growth_early_score", 0) or 0) >= (getattr(row, "value_score", 0) or 0) else "value"
        returns_6m = getattr(row, "returns_6m_pct", None)
        returns_text = f"{returns_6m:.1f}%" if pd.notna(returns_6m) else "-"
        bucket_text = _bucket_label(row)
        cards.append(
            f"""
            <article class="pick-card {accent}">
              <div class="ticker">{escape(str(getattr(row, 'ticker', '-')))}</div>
              <h3><a class="stock-link" href="#{escape(_detail_anchor(getattr(row, 'ticker', '')))}">{escape(str(getattr(row, 'name', '-')))}</a></h3>
              <span class="score-badge {accent}">{escape(bucket_text)}</span>
              <div class="meta">
                <div><strong>업종</strong><br>{escape(_fmt_cell(getattr(row, 'sector', None)))}</div>
                <div><strong>Stage</strong><br>{escape(str(getattr(row, 'stage', '-') or '-'))}</div>
                <div><strong>최종점수</strong><br>{escape(_fmt_cell(getattr(row, 'final_score', None)))}</div>
                <div><strong>6M</strong><br>{escape(returns_text)}</div>
              </div>
              <div class="issue-line"><strong>이슈</strong> {escape(issue_text)}</div>
            </article>
            """
        )
    return "".join(cards) if cards else "<div class='subtle'>오늘 포착된 중요 이슈가 없습니다.</div>"


def _detail_anchor(ticker: object) -> str:
    return f"detail-{str(ticker or '').strip()}"


def _summary_dashboard_html(
    working: pd.DataFrame,
    summary: dict[str, int],
    buy_review: pd.DataFrame,
    value_core: pd.DataFrame,
    growth_core: pd.DataFrame,
    leader_top: pd.DataFrame,
    leader_candidate: pd.DataFrame,
    small_watch: pd.DataFrame,
    trap_watch: pd.DataFrame,
) -> str:
    bucket_rows = [
        ("Value Core", len(value_core), "value"),
        ("Growth Core", len(growth_core), "growth"),
        ("Cycle Leader", len(leader_top), "growth"),
        ("Leader Candidate", len(leader_candidate), "growth"),
        ("소액 관찰", len(small_watch), "growth"),
        ("가치함정 경고", len(trap_watch), "danger"),
    ]
    bucket_total = max(1, max(count for _, count, _ in bucket_rows))
    bucket_bars = "".join(
        f"""
        <div class="bar-row">
          <span>{escape(label)}</span>
          <div class="bar-track"><div class="bar-fill {tone}" style="width:{(count / bucket_total) * 100:.1f}%"></div></div>
          <strong>{count}</strong>
        </div>
        """
        for label, count, tone in bucket_rows
    )

    stage_series = (
        working["stage"].fillna("").astype(str).value_counts()
        if "stage" in working.columns
        else pd.Series(dtype=int)
    )
    stage_order = ["초입", "중간", "후반", "과열"]
    stage_total = max(1, int(stage_series.max()) if not stage_series.empty else 1)
    stage_bars = "".join(
        f"""
        <div class="bar-row">
          <span>{escape(stage)}</span>
          <div class="bar-track"><div class="bar-fill {'danger' if stage == '과열' else 'growth' if stage == '후반' else 'value'}" style="width:{(int(stage_series.get(stage, 0)) / stage_total) * 100:.1f}%"></div></div>
          <strong>{int(stage_series.get(stage, 0))}</strong>
        </div>
        """
        for stage in stage_order
    )

    actionable = working[
        working["recommendation_bucket"].fillna("").isin(["실매수 검토", "소액 관찰", "가치함정 경고"])
        | working["core_bucket"].fillna("").isin(["Value Core", "Growth Core"])
        | working["leader_bucket"].fillna("").isin(["Leader", "Leader Candidate"])
    ].copy()
    sector_table_html = "<tr><td colspan='3' class='subtle'>No actionable sectors</td></tr>"
    if not actionable.empty:
        sector_counts = (
            actionable.assign(sector=actionable["sector"].fillna("").replace("", "미분류"))
            .groupby("sector", dropna=False)
            .agg(
                candidates=("ticker", "count"),
                avg_score=("final_score", "mean"),
                core_count=("core_bucket", lambda s: int(s.fillna("").isin(["Value Core", "Growth Core"]).sum())),
            )
            .sort_values(["candidates", "avg_score"], ascending=False)
            .head(6)
            .reset_index()
        )
        sector_table_html = "".join(
            f"<tr><td>{escape(str(row.sector))}</td><td>{int(row.candidates)}</td><td>{float(row.avg_score):.1f}</td></tr>"
            for row in sector_counts.itertuples(index=False)
        )

    health_rows = [
        ("실매수 검토", summary["buy_review"]),
        ("핵심 데이터 부족", summary["core_missing"]),
        ("급등 제외", summary["excluded"]),
        ("캐시 보강", summary["cache_rows"]),
    ]
    health_table_html = "".join(
        f"<tr><td>{escape(label)}</td><td>{count:,}</td></tr>" for label, count in health_rows
    )

    return f"""
    <div class="dashboard-grid">
      <div class="dashboard-panel">
        <h3>행동 버킷 분포</h3>
        <div class="bar-list">{bucket_bars}</div>
      </div>
      <div class="dashboard-panel">
        <h3>Stage 분포</h3>
        <div class="bar-list">{stage_bars}</div>
      </div>
      <div class="dashboard-panel">
        <h3>Actionable 업종 상위</h3>
        <table class="mini-table">
          <thead><tr><th>업종</th><th>후보수</th><th>평균점수</th></tr></thead>
          <tbody>{sector_table_html}</tbody>
        </table>
      </div>
      <div class="dashboard-panel">
        <h3>운영 체크</h3>
        <table class="mini-table">
          <thead><tr><th>항목</th><th>수</th></tr></thead>
          <tbody>{health_table_html}</tbody>
        </table>
      </div>
    </div>
    """


def _build_detail_focus_rows(
    value_core: pd.DataFrame,
    growth_core: pd.DataFrame,
    leader_top: pd.DataFrame,
    leader_candidate: pd.DataFrame,
    small_watch: pd.DataFrame,
    trap_watch: pd.DataFrame,
) -> pd.DataFrame:
    ordered = pd.concat(
        [
            value_core.head(4),
            growth_core.head(3),
            leader_top.head(3),
            leader_candidate.head(3),
            small_watch.head(2),
            trap_watch.head(2),
        ],
        ignore_index=True,
    )
    if ordered.empty:
        return ordered
    return ordered.drop_duplicates(subset=["ticker"], keep="first").head(12)


def _detail_deck_html(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "<div class='subtle'>상세 카드로 내릴 종목이 아직 없습니다.</div>"
    cards: list[str] = []
    for row in frame.itertuples(index=False):
        reasons = _recommendation_reasons(row)
        issue_text = _issue_summary(row)
        cards.append(
            f"""
            <article class="detail-card" id="{escape(_detail_anchor(getattr(row, 'ticker', '')))}">
              <div class="detail-head">
                <div>
                  <div class="ticker">{escape(str(getattr(row, 'ticker', '-')))}</div>
                  <h3 style="margin:4px 0 0;">{escape(str(getattr(row, 'name', '-')))}</h3>
                </div>
                <div class="chip-row">
                  <span class="score-badge {'value' if str(getattr(row, 'core_bucket', '') or '').startswith('Value') else 'growth'}">{escape(_bucket_label(row))}</span>
                  <span class="chip">{escape(str(getattr(row, 'stage', '-') or '-'))}</span>
                </div>
              </div>
              <div class="detail-facts">
                <div>테마<strong>{escape(str(getattr(row, 'theme', '미분류') or '미분류'))}</strong></div>
                <div>최종점수<strong>{escape(_fmt_cell(getattr(row, 'final_score', None)))}</strong></div>
                <div>PER / PBR<strong>{escape(_fmt_cell(getattr(row, 'per', None)))}/{escape(_fmt_cell(getattr(row, 'pbr', None)))}</strong></div>
                <div>6M 수익률<strong>{escape(_fmt_cell(getattr(row, 'returns_6m_pct', None)))}%</strong></div>
                <div>EPS Revision<strong>{escape(_fmt_cell(getattr(row, 'estimate_revision_score', None)))}</strong></div>
                <div>TAM Expansion<strong>{escape(_fmt_cell(getattr(row, 'tam_expansion_score', None)))}</strong></div>
                <div>Ownership<strong>{escape(_fmt_cell(getattr(row, 'ownership_flow_score', None)))}</strong></div>
              </div>
              <div class="memo-summary" style="margin-top:14px;">{escape(_memo_caution(row))}</div>
              <div class="memo-summary">{escape(_bucket_metric_line(row))}</div>
              <div class="memo-summary">{escape(_theme_metric_line(row))}</div>
              {f'<div class="issue-line"><strong>이슈</strong> {escape(issue_text)}</div>' if issue_text else ''}
              {f'<div class="issue-line"><strong>테마 근거</strong> {escape(_theme_evidence_line(row))}</div>' if _theme_evidence_line(row) else ''}
              <ol class="reason-list">{''.join(f'<li>{escape(reason)}</li>' for reason in reasons[:4])}</ol>
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
        issue_text = _issue_summary(row)
        bucket_text = _bucket_label(row)
        cards.append(
            f"""
            <article class="memo-card">
              <div class="ticker">{escape(str(getattr(row, 'ticker', '-')))}</div>
              <h3><a class="stock-link" href="#{escape(_detail_anchor(getattr(row, 'ticker', '')))}">{escape(str(getattr(row, 'name', '-')))}</a></h3>
              <div class="chip-row">
                <span class="score-badge {'value' if tone == 'value' else 'growth'}">{escape(bucket_text)}</span>
                <span class="chip">{escape(str(getattr(row, 'stage', '-') or '-'))}</span>
              </div>
              <div class="memo-summary">{escape(caution)}</div>
              <div class="memo-summary">{escape(metric_line)}</div>
              <div class="memo-summary">{escape(_theme_metric_line(row))}</div>
              {f'<div class="memo-summary">중요 이슈: {escape(issue_text)}</div>' if issue_text else ''}
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


def _spotlight_strip(value_frame: pd.DataFrame, growth_frame: pd.DataFrame, leader_frame: pd.DataFrame) -> str:
    configs = [
        ("Top Value", value_frame, "value", "final_score"),
        ("Top Growth", growth_frame, "growth", "growth_early_score"),
        ("Cycle Leader", leader_frame, "growth", "leader_cycle_score"),
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
        issue_text = _issue_summary(row)
        cards.append(
            f"""
            <article class="spotlight-card {accent}">
              <span class="spotlight-label">{escape(label)}</span>
              <h3><a class="stock-link" href="#{escape(_detail_anchor(getattr(row, 'ticker', '')))}">{escape(str(getattr(row, 'name', '-')))}</a></h3>
              <div class="ticker">{escape(str(getattr(row, 'ticker', '-')))} · {escape(str(getattr(row, 'sector', '-') or '-'))}</div>
              <div class="chip-row">
                <span class="score-badge {accent}">score {escape(_fmt_cell(getattr(row, score_column, None)))}</span>
                <span class="chip">{escape(str(getattr(row, 'stage', '-') or '-'))}</span>
              </div>
              <div class="spotlight-line">{escape(reasons[0])}</div>
              {f'<div class="spotlight-line">{escape(issue_text)}</div>' if issue_text else ''}
            </article>
            """
        )
    return "".join(cards)


def _memo_caution(row: object) -> str:
    leader_bucket = str(getattr(row, "leader_bucket", "") or "")
    core_bucket = str(getattr(row, "core_bucket", "") or "")
    bucket = str(getattr(row, "recommendation_bucket", "") or "")
    tags = str(getattr(row, "tags", "") or "")
    if leader_bucket == "Leader":
        return "이번 사이클에서 업종과 종목 수급이 가장 먼저 붙고 있는 실제 주도주 축입니다."
    if leader_bucket == "Leader Candidate":
        return "상대강도와 정배열이 살아 있어 다음 주도주군 진입을 점검할 후보입니다."
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


def _theme_metric_line(row: object) -> str:
    theme = str(getattr(row, "theme", "") or "").strip() or "미분류"
    sub_theme = str(getattr(row, "sub_theme", "") or "").strip()
    theme_score = getattr(row, "theme_score", None)
    confidence = str(getattr(row, "theme_confidence", "") or "").strip() or "낮음"
    gate_pass = bool(getattr(row, "theme_gate_pass", False))
    label = theme if not sub_theme or sub_theme == theme else f"{theme} / {sub_theme}"
    return (
        f"테마 {label} | 적합도 {_fmt_cell(theme_score)} | 신뢰도 {confidence} | "
        f"{'테마 확정' if gate_pass else '테마 보류'}"
    )


def _theme_evidence_line(row: object) -> str:
    explicit = str(getattr(row, "theme_evidence", "") or "").strip()
    if not explicit:
        return ""
    evidence = [item.strip() for item in explicit.split("|") if item.strip()]
    return " / ".join(evidence[:4])


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
        f"추세 {_fmt_cell(getattr(row, 'trend_support_score', None))}",
        f"함정위험 {_fmt_cell(trap_raw)}",
    ]
    return " | ".join(checks)


def _bucket_definitions_markdown() -> str:
    rows = [
        "- `Value Core`: 거래대금 20D 100억 이상, `investability >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`. 저평가 근거와 사업 지속성이 함께 보여야 합니다.",
        "- `Growth Core`: 거래대금 20D 100억 이상, `investability >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`. `Growth Proven`과 추정치/수급/TAM 중 최소 두 축이 확인돼야 합니다.",
        "- `Cycle Leader`: 최근 3개월 시장 대비 초과수익, 업종 내 상위 상대강도, 정배열, 거래대금, 수급이 동시에 붙는 종목입니다.",
        "- `Leader Candidate`: 업종은 강하고 정배열/추정치가 살아 있으나, 아직 완전한 리더 확신까지는 아닌 후보입니다.",
        "- `Value Conviction`: `PER <= 20` 또는 `PBR <= 1.5` 또는 업종 할인 20% 이상, 사업체력/현금흐름 양호.",
        "- `Growth Conviction`: `Growth Proven`, `estimate_revision >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`, `stage != 과열`, 고PER면 정당화 태그 필요.",
        "- `정배열 추세`: `종가 >= 20일선 >= 60일선 >= 120일선`이면 `조기매도 경계` 또는 `추세 유지` 태그를 붙여, 가치 해소 뒤에도 추세 지속 여부를 확인합니다.",
        "- `테마 판정`: 업종명만으로 붙이지 않습니다. 업종/세부산업 + 뉴스/공시 + 체급/유동성 게이트를 통과해야 확정되고, 아니면 `미분류` 또는 `테마 보류`로 둡니다.",
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
                "정배열이면 조기매도 경계",
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
                "정배열 유지면 추세 보유 우선",
            ],
        ),
        (
            "Cycle Leader / Candidate",
            "이번 사이클에서 누가 실제 선도주인지와, 누가 그 뒤를 따라 리더군에 진입 중인지를 분리합니다.",
            [
                "시장 대비 3개월 초과수익",
                "업종 내 상위 상대강도",
                "20/60/120일선 정배열",
                "거래대금과 수급 동반",
                "Leader와 Candidate 분리",
            ],
        ),
        (
            "테마 판정",
            "테마는 업종명만으로 붙이지 않고 업종, 뉴스, 공시, 키워드, 체급 게이트를 함께 확인한 뒤에만 확정합니다.",
            [
                "업종/세부산업 키워드 확인",
                "뉴스 또는 공시로 외부 확인",
                "시총·거래대금 최소 게이트",
                "사업체력 부족 시 미분류",
                "증거 약하면 테마 보류",
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
    theme = str(getattr(row, "theme", "") or "").strip()
    theme_gate_pass = bool(getattr(row, "theme_gate_pass", False))
    evidence = _theme_evidence_line(row)
    if tam >= 10 and theme_gate_pass and theme and theme != "미분류":
        reasons.append(f"{name}은 {theme} 테마 근거가 확인돼 산업 TAM 확대 수혜 후보로 분류했습니다.")
    elif tam >= 6 and theme_gate_pass and theme and theme != "미분류":
        reasons.append(f"{theme} 관련 수요 확장 신호가 점수에 반영됐습니다.")
    elif tam >= 6:
        reasons.append("산업 성장률과 수요 확장 신호가 유의미하지만, 테마 증거는 추가 확인이 필요합니다.")

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

    leader_cycle = getattr(row, "leader_cycle_score", 0) or 0
    leader_bucket = str(getattr(row, "leader_bucket", "") or "")
    if leader_bucket == "Leader":
        reasons.append("이번 사이클에서 시장과 업종을 동시에 앞서는 상대강도를 보이고 있습니다.")
    elif leader_bucket == "Leader Candidate" and leader_cycle >= 6:
        reasons.append("업종 리더군으로 진입하는 초기 흐름이 포착됩니다.")

    policy = getattr(row, "policy_score", 0) or 0
    if policy >= 8:
        reasons.append("주주환원, 정책 수혜, 지배구조 변화가 동시에 기대됩니다.")
    elif policy >= 4:
        reasons.append("주주환원 정책 변화 가능성이 점수에 반영됐습니다.")

    business = getattr(row, "business_quality_score", 0) or 0
    if business >= 7:
        reasons.append("이익 체력과 사업 지속성이 안정적인 편입니다.")

    trend_support = getattr(row, "trend_support_score", 0) or 0
    tags = str(getattr(row, "tags", "") or "")
    if "조기매도 경계" in tags and trend_support > 0:
        reasons.append("이동평균선 정배열이 유지돼, 밸류 해소 뒤에도 추세가 이어질 가능성을 시사합니다.")
    elif "사이클 종료 점검" in tags:
        reasons.append("장기 이동평균선 아래로 약해져 사이클 종료 여부를 다시 점검할 구간입니다.")

    if not reasons:
        reasons.append("여러 축에서 평균 이상 점수를 받아 관찰 우선순위가 높습니다.")
    if evidence and len(reasons) < 4 and theme_gate_pass:
        reasons.append(f"테마 근거: {evidence}")
    return reasons[:4]


def _html_table(frame: pd.DataFrame, bucket: str) -> str:
    if frame.empty:
        return "<div class='subtle'>No rows</div>"
    rows: list[str] = []
    if bucket == "value":
        columns = ["ticker", "name", "recommendation_bucket", "core_bucket", "theme", "theme_confidence", "sector", "size_bucket", "prev_close", "per", "peg", "roe_pct", "pbr", "dividend_yield_trailing", "dividend_yield_normalized", "returns_6m_pct", "final_score", "value_score", "estimate_revision_score", "tam_expansion_score", "ownership_flow_score", "policy_score", "payout_repeatability_score", "cashflow_quality_score", "governance_warning_score", "investability_score", "dividend_potential_score", "business_quality_score", "liquidity_support_score", "stage", "tags", "missing_data"]
    elif bucket == "special_dividend":
        columns = ["ticker", "name", "sector", "prev_close", "dividend_yield_trailing", "dividend_yield_normalized", "dividend_gap_pct", "dividends_3y", "tags"]
    else:
        columns = ["ticker", "name", "theme", "theme_confidence", "sector", "size_bucket", "prev_close", "per", "pbr", "returns_6m_pct", "high_52w_ratio_pct", "growth_early_score", "value_score", "stage", "tags", "missing_data"]

    for row in frame[columns].itertuples(index=False, name=None):
        rendered = []
        for idx, cell in enumerate(row):
            key = columns[idx]
            if key == "stage":
                rendered.append(f"<td><span class='stage stage-{escape(str(cell or '초입'))}'>{escape(str(cell or '-'))}</span></td>")
            elif key == "name":
                ticker = row[0] if row else ""
                rendered.append(f"<td><a class='stock-link' href='#{escape(_detail_anchor(ticker))}'>{escape(_fmt_cell(cell, key))}</a></td>")
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
        "theme",
        "sub_theme",
        "theme_score",
        "theme_confidence",
        "theme_gate_pass",
        "theme_evidence",
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
        "leader_cycle_score",
        "recommendation_bucket",
        "core_bucket",
        "leader_bucket",
        "recommendation_reasons",
        "important_news_items",
        "important_disclosures",
        "value_style",
        "growth_style",
        "stage",
        "tags",
        "missing_data",
        "repeat_top_count",
    ]
    return frame.reindex(columns=columns, fill_value="").to_dict(orient="records")


def _explorer_theme_chips_html(frame: pd.DataFrame, limit: int = 8) -> str:
    if frame.empty or "theme" not in frame.columns:
        return ""
    working = frame.copy()
    working["theme"] = working["theme"].fillna("미분류").replace("", "미분류")
    ranked = (
        working[working["theme"] != "미분류"]["theme"]
        .value_counts()
        .head(limit)
    )
    chips = [
        '<button class="jump-link" type="button" data-theme-filter="">전체</button>'
    ]
    chips.extend(
        f'<button class="jump-link" type="button" data-theme-filter="{escape(str(theme))}">{escape(str(theme))} {int(count)}</button>'
        for theme, count in ranked.items()
    )
    return "".join(chips)


def _issue_focus_rows(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    working = frame.copy()
    if "important_news_items" not in working.columns:
        working["important_news_items"] = ""
    if "important_disclosures" not in working.columns:
        working["important_disclosures"] = ""

    working["issue_count"] = (
        working["important_news_items"].fillna("").astype(str).apply(lambda value: len(_split_issue_values(value)))
        + working["important_disclosures"].fillna("").astype(str).apply(lambda value: len(_split_issue_values(value)))
    )
    working = working[(working["issue_count"] > 0)].copy()
    if working.empty:
        return working
    working["is_actionable_issue"] = (
        (~working["excluded"])
        | (working["core_bucket"].fillna("") != "")
        | (working["leader_bucket"].fillna("").isin(["Leader", "Leader Candidate"]))
    )
    return working.sort_values(
        by=["is_actionable_issue", "issue_count", "final_score", "estimate_revision_score", "returns_3m_pct"],
        ascending=False,
    ).head(limit)


def _issue_summary(row: object) -> str:
    news = _split_issue_values(getattr(row, "important_news_items", ""))
    disclosures = _split_issue_values(getattr(row, "important_disclosures", ""))
    parts: list[str] = []
    if disclosures:
        parts.append(f"공시 {', '.join(disclosures[:2])}")
    if news:
        parts.append(f"뉴스 {', '.join(news[:2])}")
    return " / ".join(parts)


def _bucket_label(row: object) -> str:
    for field in ("core_bucket", "leader_bucket", "recommendation_bucket"):
        value = getattr(row, field, None)
        if value is None:
            continue
        if isinstance(value, float) and pd.isna(value):
            continue
        text = str(value).strip()
        if not text or text.lower() == "nan":
            continue
        return text
    return "-"


def _split_issue_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(" | ") if part.strip()]
        return _filter_issue_parts(parts)
    if isinstance(value, list):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return _filter_issue_parts(parts)
    return []


def _filter_issue_parts(parts: list[str]) -> list[str]:
    filtered: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if _is_low_quality_issue(part):
            continue
        if part in seen:
            continue
        seen.add(part)
        filtered.append(part)
    return filtered


def _is_low_quality_issue(text: str) -> bool:
    if not text:
        return True
    if any(pattern in text for pattern in LOW_QUALITY_ISSUE_PATTERNS):
        return True
    return any(regex.search(text) for regex in LOW_QUALITY_ISSUE_REGEXES)


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
