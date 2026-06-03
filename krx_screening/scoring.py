from __future__ import annotations

from .models import EquitySnapshot


def score_equities(equities: list[EquitySnapshot]) -> None:
    for equity in equities:
        _score_value_bucket(equity)
        _score_growth_bucket(equity)
        _score_dividend_potential(equity)
        _apply_dividend_event_tags(equity)
        _apply_weak_profit_sector_penalty(equity)
        _classify_value_style(equity)
        _classify_growth_style(equity)
        _classify_stage(equity)


def _score_value_bucket(equity: EquitySnapshot) -> None:
    score = 0.0
    reasons: list[str] = []
    excluded_reasons: list[str] = []
    effective_dividend_yield = _effective_dividend_yield(equity)

    if equity.per is not None and equity.per <= 10:
        score += 3.0
        score += round(max(0.0, 10 - equity.per) * 0.08, 2)
        reasons.append("PER 10 이하")

    if equity.pbr is not None and equity.pbr <= 1:
        score += 3.0
        score += round(max(0.0, 1 - equity.pbr) * 0.8, 2)
        reasons.append("PBR 1 이하")

    if effective_dividend_yield is not None and effective_dividend_yield >= 2:
        score += 1.5
        score += min(1.0, max(0.0, effective_dividend_yield - 2) * 0.12)
        reasons.append("배당수익률 2% 이상")

    if equity.returns_6m is not None and equity.returns_6m >= 100:
        equity.excluded = True
        excluded_reasons.append("최근 6개월 100% 이상 상승")

    if equity.returns_12m is not None and equity.returns_12m >= 200:
        equity.excluded = True
        excluded_reasons.append("최근 12개월 200% 이상 상승")

    if len(equity.op_income_3y) >= 3 and all((v or 0) > 0 for v in equity.op_income_3y):
        score += 2.0
        reasons.append("최근 3년 영업이익 연속 흑자")

    if equity.net_cash is not None and equity.market_cap not in (None, 0):
        net_cash_ratio = equity.net_cash / equity.market_cap
        if net_cash_ratio >= 0.1:
            score += 1.5
            score += min(0.8, net_cash_ratio * 2)
            reasons.append("순현금 비중 우수")

    if equity.cash_assets is not None and equity.market_cap not in (None, 0):
        cash_ratio = equity.cash_assets / equity.market_cap
        if cash_ratio >= 0.15:
            score += 1.0
            score += min(0.6, cash_ratio)
            reasons.append("현금성 자산 비중 우수")

    if equity.op_income_volatility is not None and equity.op_income_volatility <= 35:
        score += 1.0
        score += max(0.0, (35 - equity.op_income_volatility) / 50)
        reasons.append("영업이익 변동성 낮음")

    if len(equity.sales_3y) >= 3 and _is_uptrend(equity.sales_3y):
        score += 0.8
        reasons.append("최근 3년 매출 우상향")

    if any((v or 0) < 0 for v in equity.net_income_3y):
        score -= 1.5
        reasons.append("순이익 적자 연도 존재")

    if equity.debt_ratio is not None and equity.debt_ratio >= 200:
        score -= 1.5
        reasons.append("부채비율 높음")

    equity.value_score = round(score, 2)
    equity.pass_reasons.extend(reasons)
    equity.exclusion_reasons.extend(excluded_reasons)


def _score_growth_bucket(equity: EquitySnapshot) -> None:
    score = 0.0
    reasons: list[str] = []

    if equity.forecast_growth_next_year is not None:
        if equity.forecast_growth_next_year >= 40:
            score += 4.0
            score += min(2.0, (equity.forecast_growth_next_year - 40) / 20)
            reasons.append("내년 예상 이익 성장률 40% 이상")
        elif equity.forecast_growth_next_year >= 20:
            score += 2.0
            score += min(1.2, (equity.forecast_growth_next_year - 20) / 20)
            reasons.append("내년 예상 이익 성장률 20% 이상")
    else:
        if "forecast_growth_unavailable" not in equity.source_notes:
            equity.source_notes.append("forecast_growth_unavailable")

    if len(equity.sales_3y) >= 3 and _is_uptrend(equity.sales_3y):
        score += 1.5
        score += _trend_strength(equity.sales_3y, cap=1.0)
        reasons.append("최근 3년 매출 성장")
    if len(equity.op_income_3y) >= 3 and _is_uptrend(equity.op_income_3y):
        score += 2.0
        score += _trend_strength(equity.op_income_3y, cap=1.4)
        reasons.append("최근 3년 영업이익 성장")

    if equity.news_keyword_hits:
        score += min(4.0, len(equity.news_keyword_hits) * 1.2)
        reasons.append("산업 모멘텀 키워드 감지")

    if equity.returns_6m is not None and equity.returns_6m >= 100:
        equity.tags.append("이미 반영")
        reasons.append("최근 6개월 급등")
    if equity.high_52w_ratio is not None and equity.high_52w_ratio >= 95:
        equity.tags.append("추격주의")
        score -= 1.0
        reasons.append("52주 신고가 근처")
    if equity.returns_12m is not None and equity.returns_12m >= 150:
        equity.tags.append("추격주의")
        score -= 1.0
        reasons.append("최근 12개월 급등")

    equity.growth_early_score = round(score, 2)
    equity.pass_reasons.extend(reasons)


def _score_dividend_potential(equity: EquitySnapshot) -> None:
    score = 0.0
    effective_dividend_yield = _effective_dividend_yield(equity)

    if effective_dividend_yield is not None:
        score += min(3.0, effective_dividend_yield / 2)

    if equity.fcf is not None and equity.fcf > 0:
        score += 2.5

    if equity.payout_ratio is not None and equity.payout_ratio < 30 and equity.fcf not in (None, 0):
        score += 2.5
        if "배당상향 잠재" not in equity.tags:
            equity.tags.append("배당상향 잠재")

    if equity.net_cash is not None and equity.net_cash > 0:
        score += 1.5

    equity.dividend_potential_score = round(score, 2)


def _classify_stage(equity: EquitySnapshot) -> None:
    equity.size_bucket = _classify_size_bucket(equity.market_cap)
    returns_6m = equity.returns_6m or 0
    returns_12m = equity.returns_12m or 0
    high_ratio = equity.high_52w_ratio or 0

    if returns_6m >= 100 or returns_12m >= 200 or high_ratio >= 97:
        equity.stage = "과열"
    elif returns_6m >= 50 or high_ratio >= 88:
        equity.stage = "후반"
    elif returns_6m >= 20 or high_ratio >= 70:
        equity.stage = "중간"
    else:
        equity.stage = "초입"


def _classify_value_style(equity: EquitySnapshot) -> None:
    effective_dividend_yield = _effective_dividend_yield(equity) or 0.0
    profitable_years = sum(1 for value in equity.op_income_3y if (value or 0) > 0)
    latest_op = next((value for value in reversed(equity.op_income_3y) if value is not None), None)
    prior_ops = [value for value in equity.op_income_3y[:-1] if value is not None]
    turnaround = (
        latest_op is not None
        and latest_op > 0
        and any((value or 0) <= 0 for value in prior_ops)
    )

    if effective_dividend_yield >= 3 and equity.fcf not in (None, 0) and profitable_years >= 2:
        equity.value_style = "Dividend Compounder"
    elif turnaround:
        equity.value_style = "Turnaround Value"
    elif (equity.per is not None and equity.per <= 8) or (equity.pbr is not None and equity.pbr <= 0.6):
        equity.value_style = "Deep Value"
    else:
        equity.value_style = "Balanced Value"


def _classify_growth_style(equity: EquitySnapshot) -> None:
    profitable_now = any((value or 0) > 0 for value in equity.op_income_3y[-2:])
    forecast = equity.forecast_growth_next_year or 0.0
    trend_ok = _is_uptrend(equity.sales_3y) or _is_uptrend(equity.op_income_3y)
    if profitable_now and (forecast >= 20 or trend_ok):
        equity.growth_style = "Growth Proven"
    else:
        equity.growth_style = "Growth Speculative"


def _apply_dividend_event_tags(equity: EquitySnapshot) -> None:
    dividends = [value for value in equity.dividends_3y if value not in (None, 0)]
    if len(dividends) < 2:
        return

    trailing = equity.dividend_yield_trailing
    normalized = equity.dividend_yield_normalized
    if (
        trailing is not None
        and normalized is not None
        and trailing >= normalized * 1.8
        and "특별배당 가능성" not in equity.tags
    ):
        equity.tags.append("특별배당 가능성")

    if len(dividends) >= 2 and dividends[-1] < dividends[-2] * 0.7 and "감액배당 주의" not in equity.tags:
        equity.tags.append("감액배당 주의")

    if max(dividends) >= min(dividends) * 1.8 and "배당 불안정" not in equity.tags:
        equity.tags.append("배당 불안정")


def _apply_weak_profit_sector_penalty(equity: EquitySnapshot) -> None:
    sector_label = " ".join(filter(None, [equity.sector, equity.industry])).lower()
    name_label = (equity.name or "").lower()
    weak_sector_keywords = (
        "바이오",
        "제약",
        "게임",
        "콘텐츠",
        "엔터",
        "플랫폼",
        "인터넷",
        "소프트웨어",
        "로봇",
        "ai",
    )
    weak_name_keywords = (
        "바이오",
        "제약",
        "게임",
        "엔터",
        "로봇",
    )
    sector_hit = any(keyword.lower() in sector_label for keyword in weak_sector_keywords)
    name_hit = any(keyword.lower() in name_label for keyword in weak_name_keywords)
    if not sector_hit and not name_hit:
        return

    if "이익생산 약한 섹터" not in equity.tags:
        equity.tags.append("이익생산 약한 섹터")
    equity.value_score = round(equity.value_score - (0.7 if sector_hit else 0.4), 2)
    equity.growth_early_score = round(equity.growth_early_score - (0.4 if sector_hit else 0.2), 2)


def _is_uptrend(values: list[float | None]) -> bool:
    cleaned = [value for value in values if value is not None]
    return len(cleaned) >= 3 and cleaned[0] < cleaned[1] < cleaned[2]


def _trend_strength(values: list[float | None], cap: float) -> float:
    cleaned = [value for value in values if value not in (None, 0)]
    if len(cleaned) < 2 or cleaned[0] == 0:
        return 0.0
    growth = max(0.0, (cleaned[-1] / cleaned[0]) - 1)
    return round(min(cap, growth * 0.6), 2)


def _classify_size_bucket(market_cap: float | None) -> str | None:
    if market_cap is None:
        return None
    if market_cap >= 10_000_000_000_000:
        return "Mega"
    if market_cap >= 2_000_000_000_000:
        return "Large"
    if market_cap >= 300_000_000_000:
        return "Mid"
    return "Small"


def _effective_dividend_yield(equity: EquitySnapshot) -> float | None:
    if equity.dividend_yield_normalized is not None:
        return equity.dividend_yield_normalized
    if equity.dividend_yield_trailing is not None:
        return equity.dividend_yield_trailing
    return equity.dividend_yield
