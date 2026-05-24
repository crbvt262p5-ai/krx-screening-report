from __future__ import annotations

from .models import EquitySnapshot


def score_equities(equities: list[EquitySnapshot]) -> None:
    for equity in equities:
        _score_value_bucket(equity)
        _score_growth_bucket(equity)
        _score_dividend_potential(equity)
        _classify_stage(equity)


def _score_value_bucket(equity: EquitySnapshot) -> None:
    score = 0.0
    reasons: list[str] = []
    excluded_reasons: list[str] = []

    if equity.per is not None and equity.per <= 10:
        score += 3.0
        reasons.append("PER 10 이하")

    if equity.pbr is not None and equity.pbr <= 1:
        score += 3.0
        reasons.append("PBR 1 이하")

    if equity.dividend_yield is not None and equity.dividend_yield >= 2:
        score += 1.5
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
            reasons.append("순현금 비중 우수")

    if equity.cash_assets is not None and equity.market_cap not in (None, 0):
        cash_ratio = equity.cash_assets / equity.market_cap
        if cash_ratio >= 0.15:
            score += 1.0
            reasons.append("현금성 자산 비중 우수")

    if equity.op_income_volatility is not None and equity.op_income_volatility <= 35:
        score += 1.0
        reasons.append("영업이익 변동성 낮음")

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
            reasons.append("내년 예상 이익 성장률 40% 이상")
        elif equity.forecast_growth_next_year >= 20:
            score += 2.0
            reasons.append("내년 예상 이익 성장률 20% 이상")
    else:
        if "forecast_growth_unavailable" not in equity.source_notes:
            equity.source_notes.append("forecast_growth_unavailable")

    if len(equity.sales_3y) >= 3 and _is_uptrend(equity.sales_3y):
        score += 1.5
        reasons.append("최근 3년 매출 성장")
    if len(equity.op_income_3y) >= 3 and _is_uptrend(equity.op_income_3y):
        score += 2.0
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

    if equity.dividend_yield is not None:
        score += min(3.0, equity.dividend_yield / 2)

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


def _is_uptrend(values: list[float | None]) -> bool:
    cleaned = [value for value in values if value is not None]
    return len(cleaned) >= 3 and cleaned[0] < cleaned[1] < cleaned[2]
