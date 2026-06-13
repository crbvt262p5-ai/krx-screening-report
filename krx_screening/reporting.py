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
        by=["value_score", "growth_early_score", "dividend_potential_score"],
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
    value_top = _select_featured_rows(
        working[~working["excluded"]],
        score_column="value_score",
        history_counts=history["value"],
        weekly_counts=history["value_weekly"],
        limit=20,
    )
    growth_top = _select_featured_rows(
        working,
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
    special_dividend_watch = _special_dividend_watchlist(working, limit=12)

    parts = [
        f"# KRX Daily Screening Report ({trading_date.isoformat()})",
        "",
        "## Summary",
        f"- Universe: {summary['total']} 종목",
        f"- Excluded by momentum rules: {summary['excluded']} 종목",
        f"- Missing finance/data flags: {summary['missing']} 종목",
        f"- Core missing fields: {summary['core_missing']} 종목",
        f"- Non-excluded early-stage names: {summary['early_stage']} 종목",
        f"- Non-excluded overheated names: {summary['value_heat']} 종목",
        f"- Historical cache assists: {summary['cache_rows']} 종목",
        "",
        "## Quick Picks",
        "### Value Top 10",
        _bullet_summary(value_top.head(10), score_column="value_score"),
        "",
        "### Growth Top 10",
        _bullet_summary(growth_top.head(10), score_column="growth_early_score"),
        "",
        "## Value Lenses",
        "### Deep Value",
        _bullet_summary(deep_value, score_column="value_score"),
        "",
        "### Dividend Compounder",
        _bullet_summary(dividend_compounder, score_column="value_score"),
        "",
        "### Turnaround Value",
        _bullet_summary(turnaround_value, score_column="value_score"),
        "",
        "## Growth Lenses",
        "### Growth Proven",
        _bullet_summary(growth_proven, score_column="growth_early_score"),
        "",
        "### Growth Speculative",
        _bullet_summary(growth_speculative, score_column="growth_early_score"),
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
    value_top = _select_featured_rows(
        working[~working["excluded"]],
        score_column="value_score",
        history_counts=history["value"],
        weekly_counts=history["value_weekly"],
        limit=20,
    )
    growth_top = _select_featured_rows(
        working,
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
    special_dividend_watch = _special_dividend_watchlist(working, limit=12)
    full_list = _rank_for_explorer(
        working[~working["excluded"]],
        score_column="value_score",
        history_counts=history["value"],
        weekly_counts=history["value_weekly"],
    ).head(200)

    summary_cards = [
        ("전체 스캔 종목", f"{summary['total']:,}"),
        ("급등 제외 종목", f"{summary['excluded']:,}"),
        ("핵심 데이터 부족", f"{summary['core_missing']:,}"),
        ("캐시 보강 종목", f"{summary['cache_rows']:,}"),
        ("초입 후보", f"{summary['early_stage']:,}"),
        ("과열 후보", f"{summary['value_heat']:,}"),
    ]

    missing_counts = _top_missing_counts(working)
    quick_value = _card_grid(value_top.head(8), "value_score", accent="value")
    quick_growth = _card_grid(growth_top.head(8), "growth_early_score", accent="growth")
    deep_value_html = _card_grid(deep_value, "value_score", accent="value")
    dividend_compounder_html = _card_grid(dividend_compounder, "value_score", accent="value")
    turnaround_value_html = _card_grid(turnaround_value, "value_score", accent="value")
    growth_proven_html = _card_grid(growth_proven, "growth_early_score", accent="growth")
    growth_speculative_html = _card_grid(growth_speculative, "growth_early_score", accent="growth")
    special_watch_html = _html_table(special_dividend_watch, bucket="special_dividend")
    universe_json = json.dumps(_records_for_ui(full_list), ensure_ascii=False)
    value_table = _html_table(value_top, bucket="value")
    growth_table = _html_table(growth_top, bucket="growth")
    summary_html = "".join(
        f'<div class="metric-card"><span class="metric-label">{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in summary_cards
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
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
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
    .metric-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
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
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}
    .pick-card {{
      border-radius: 20px;
      padding: 16px;
      border: 1px solid var(--line);
      background: var(--panel-strong);
      min-height: 190px;
    }}
    .pick-card.value {{ box-shadow: inset 0 0 0 1px rgba(15,118,110,0.08); }}
    .pick-card.growth {{ box-shadow: inset 0 0 0 1px rgba(180,83,9,0.08); }}
    .pick-card h3 {{
      margin: 0 0 8px;
      font-size: 20px;
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
      .metric-grid, .card-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 720px) {{
      .shell {{ width: min(100vw - 20px, 100%); margin: 12px auto 28px; }}
      .hero, .section {{ padding: 18px; border-radius: 20px; }}
      .metric-grid, .card-grid {{ grid-template-columns: 1fr; }}
      .controls input, .controls select {{ width: 100%; min-width: 0; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">KRX Automated Screening</div>
      <h1>{escape(trading_date.isoformat())}</h1>
      <p>수동 종목코드 입력 없이 KOSPI/KOSDAQ 전체 종목을 스캔한 결과입니다. Value와 Growth Early 후보를 분리해서 보고, 최근 급등 및 데이터 결측은 시각적으로 구분했습니다.</p>
      <div class="metric-grid">{summary_html}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Snapshot</h2>
        <span>가장 많이 비는 항목과 운영 상태를 먼저 확인합니다.</span>
      </div>
      <div class="chip-row">{missing_html}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Value Quick Picks</h2>
        <span>낮은 밸류와 현금성, 배당, 이익 안정성 중심의 다변화 추천</span>
      </div>
      <div class="card-grid">{quick_value}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Growth Early Quick Picks</h2>
        <span>내년 성장률과 업황 시그널 중심의 다변화 추천</span>
      </div>
      <div class="card-grid">{quick_growth}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Value Lenses</h2>
        <span>저평가, 배당복리, 턴어라운드를 분리해서 봅니다.</span>
      </div>
      <div class="section-head">
        <h2>Deep Value</h2>
        <span>낮은 PER/PBR 중심</span>
      </div>
      <div class="card-grid">{deep_value_html}</div>
      <div class="section-head">
        <h2>Dividend Compounder</h2>
        <span>배당 반복성과 현금흐름 중심</span>
      </div>
      <div class="card-grid">{dividend_compounder_html}</div>
      <div class="section-head">
        <h2>Turnaround Value</h2>
        <span>실적 회복 초기 저평가</span>
      </div>
      <div class="card-grid">{turnaround_value_html}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Growth Lenses</h2>
        <span>검증형 성장과 투기형 초기 성장을 분리합니다.</span>
      </div>
      <div class="section-head">
        <h2>Growth Proven</h2>
        <span>흑자/성장 검증형</span>
      </div>
      <div class="card-grid">{growth_proven_html}</div>
      <div class="section-head">
        <h2>Growth Speculative</h2>
        <span>적자 포함 초기 성장형</span>
      </div>
      <div class="card-grid">{growth_speculative_html}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Top Value 20</h2>
        <span>보관용 Markdown보다 읽기 쉽게 압축한 표</span>
      </div>
      <div class="table-wrap">{value_table}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Top Growth 20</h2>
        <span>과열 여부와 52주 위치를 함께 표시</span>
      </div>
      <div class="table-wrap">{growth_table}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Special Dividend Watch</h2>
        <span>최근 실제 배당이 높아 보여도 평년 배당력은 낮을 수 있는 종목입니다.</span>
      </div>
      <div class="table-wrap">{special_watch_html}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Candidate Explorer</h2>
        <span>상위 200개 비제외 종목을 검색/필터링할 수 있습니다. 최근 반복 노출 횟수도 함께 봅니다.</span>
      </div>
      <div class="controls">
        <input id="searchInput" type="search" placeholder="종목명 또는 티커 검색">
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
              <th>최근반복</th>
              <th>Stage</th>
              <th>태그</th>
              <th>결측</th>
            </tr>
          </thead>
          <tbody id="universeBody"></tbody>
        </table>
      </div>
    </section>
  </div>
  <script>
    const universeRows = {universe_json};
    const body = document.getElementById("universeBody");
    const searchInput = document.getElementById("searchInput");
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
      const market = marketFilter.value;
      const stage = stageFilter.value;
      const filtered = universeRows.filter((row) => {{
        const matchQuery = !q || `${{row.name}} ${{row.ticker}}`.toLowerCase().includes(q);
        const matchMarket = !market || row.market === market;
        const matchStage = !stage || row.stage === stage;
        return matchQuery && matchMarket && matchStage;
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
          <td>${{fmt(row.repeat_top_count)}}</td>
          <td>${{stageBadge(row.stage)}}</td>
          <td>${{row.tags || "-"}}</td>
          <td>${{row.missing_data || "-"}}</td>
        </tr>
      `).join("");
    }}

    searchInput.addEventListener("input", renderUniverse);
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
        ("value_style", ""),
        ("growth_style", ""),
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
    ):
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")
    if "excluded" in working.columns:
        working["excluded"] = working["excluded"].astype(str).str.lower().eq("true")
    return working


def _summary_metrics(equities: list[EquitySnapshot], working: pd.DataFrame) -> dict[str, int]:
    total = len(equities)
    excluded = sum(1 for equity in equities if equity.excluded)
    missing = sum(1 for equity in equities if equity.missing_data)
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
    core_missing = sum(
        1 for equity in equities if any(field in core_fields for field in equity.missing_data)
    )
    value_heat = sum(1 for equity in equities if equity.stage == "과열" and not equity.excluded)
    early_stage = sum(1 for equity in equities if equity.stage == "초입" and not equity.excluded)
    cache_rows = int(working["source_notes"].fillna("").str.contains("cache:historical_csv").sum())
    return {
        "total": total,
        "excluded": excluded,
        "missing": missing,
        "core_missing": core_missing,
        "value_heat": value_heat,
        "early_stage": early_stage,
        "cache_rows": cache_rows,
    }


def _top_missing_counts(working: pd.DataFrame) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for value in working["missing_data"].fillna(""):
        for item in filter(None, str(value).split("|")):
            counts[item] = counts.get(item, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:8]


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
        value_top = working[~working["excluded"]].nlargest(20, "value_score")["ticker"].astype(str).tolist()
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
        adjusted_scores.append(float(base_score) + stage_bonus - data_penalty - repeat_penalty - weekly_penalty)
    working["repeat_top_count"] = repeat_counts
    working["display_score"] = adjusted_scores
    return working.sort_values(
        by=["display_score", score_column, "dividend_potential_score"],
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
            "sector",
            "size_bucket",
            "prev_close",
            "per",
            "pbr",
            "dividend_yield_trailing",
            "dividend_yield_normalized",
            "returns_6m_pct",
            "value_score",
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
        score_text = f"{score:.1f}" if pd.notna(score) else "-"
        returns_text = f"{returns_6m:.1f}%" if pd.notna(returns_6m) else "-"
        tag_text = f" / {tags}" if tags else ""
        lines.append(
            f"- {row.name} ({row.ticker}) [{sector} {size_bucket}] score {score_text}, 6M {returns_text}, stage {stage}{tag_text}"
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


def _html_table(frame: pd.DataFrame, bucket: str) -> str:
    if frame.empty:
        return "<div class='subtle'>No rows</div>"
    rows: list[str] = []
    if bucket == "value":
        columns = ["ticker", "name", "sector", "size_bucket", "prev_close", "per", "pbr", "dividend_yield_trailing", "dividend_yield_normalized", "returns_6m_pct", "value_score", "dividend_potential_score", "business_quality_score", "liquidity_support_score", "stage", "tags", "missing_data"]
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
        "value_score",
        "growth_early_score",
        "business_quality_score",
        "liquidity_support_score",
        "value_trap_risk_score",
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
    if key in {"per", "pbr", "dividend_yield", "returns_6m_pct", "high_52w_ratio_pct", "value_score", "growth_early_score", "dividend_potential_score"}:
        return f"{float(value):,.2f}".rstrip("0").rstrip(".")
    return str(value)
