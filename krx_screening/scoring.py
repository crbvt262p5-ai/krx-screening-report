from __future__ import annotations

from .models import EquitySnapshot

TAM_THEME_CAGR = {
    "AI Infrastructure": 18.0,
    "HBM": 22.0,
    "Advanced Packaging": 17.0,
    "PCB": 9.0,
    "Optical Communication": 14.0,
    "Power Equipment": 16.0,
    "Data Center Cooling": 19.0,
    "Defense": 12.0,
    "Shipbuilding": 8.0,
    "K-Beauty": 11.0,
    "Space / Satellite": 16.0,
    "Healthcare Diagnostics": 10.0,
    "Industrial Automation": 9.0,
}

TAM_THEME_ALIASES = {
    "AI Infrastructure": ("ai", "gpu", "데이터센터", "server", "infra"),
    "HBM": ("hbm", "고대역폭메모리", "dram", "memory"),
    "Advanced Packaging": ("advanced packaging", "첨단패키징", "패키징", "fc-bga", "coWoS", "cowos"),
    "PCB": ("pcb", "fpcb", "기판"),
    "Optical Communication": ("optical", "광통신", "광모듈", "transceiver"),
    "Power Equipment": ("power equipment", "전력기기", "변압기", "배전", "송전"),
    "Data Center Cooling": ("cooling", "냉각", "액침", "thermal"),
    "Defense": ("defense", "방산", "미사일", "탄약", "군수"),
    "Shipbuilding": ("shipbuilding", "조선", "lng선", "선박"),
    "K-Beauty": ("k-beauty", "beauty", "화장품", "cosmetic"),
    "Space / Satellite": ("space", "satellite", "우주", "위성", "발사체"),
    "Healthcare Diagnostics": ("diagnostics", "진단", "분자진단", "체외진단"),
    "Industrial Automation": ("automation", "산업자동화", "factory automation", "fa", "robotics", "로봇"),
}

THEME_PROFILES = {
    "AI Infrastructure": {
        "keywords": ("ai", "gpu", "데이터센터", "server", "infra", "가속기"),
        "sector_keywords": ("반도체", "전자", "전기전자", "it"),
        "industry_keywords": ("서버", "데이터센터", "가속기", "ai"),
        "min_score": 6.0,
    },
    "HBM": {
        "keywords": ("hbm", "고대역폭메모리", "dram", "memory", "메모리"),
        "sector_keywords": ("반도체", "전자"),
        "industry_keywords": ("메모리", "dram", "반도체"),
        "min_score": 6.0,
    },
    "Advanced Packaging": {
        "keywords": ("advanced packaging", "첨단패키징", "패키징", "fc-bga", "cowos", "반도체기판"),
        "sector_keywords": ("반도체", "전자", "it"),
        "industry_keywords": ("패키징", "기판", "pcb", "fc-bga"),
        "min_score": 6.0,
    },
    "PCB": {
        "keywords": ("pcb", "fpcb", "기판"),
        "sector_keywords": ("전자", "반도체"),
        "industry_keywords": ("pcb", "fpcb", "기판"),
        "min_score": 5.5,
    },
    "Optical Communication": {
        "keywords": ("optical", "광통신", "광모듈", "transceiver", "실리콘포토닉스"),
        "sector_keywords": ("통신", "전자"),
        "industry_keywords": ("광", "통신", "모듈"),
        "min_score": 5.5,
    },
    "Power Equipment": {
        "keywords": ("power equipment", "전력기기", "변압기", "배전", "송전", "초고압"),
        "sector_keywords": ("전기", "기계", "중공업"),
        "industry_keywords": ("전력", "변압기", "배전", "송전"),
        "min_score": 5.5,
    },
    "Data Center Cooling": {
        "keywords": ("cooling", "냉각", "액침", "thermal", "열관리"),
        "sector_keywords": ("기계", "전자", "화학"),
        "industry_keywords": ("냉각", "열관리", "hvac"),
        "min_score": 5.5,
    },
    "Defense": {
        "keywords": ("defense", "방산", "미사일", "탄약", "군수", "레이더"),
        "sector_keywords": ("기계", "항공", "우주"),
        "industry_keywords": ("방산", "항공", "군수"),
        "min_score": 5.5,
    },
    "Shipbuilding": {
        "keywords": ("shipbuilding", "조선", "lng선", "선박", "해양플랜트"),
        "sector_keywords": ("조선", "기계", "중공업"),
        "industry_keywords": ("조선", "선박", "해양"),
        "min_score": 5.5,
    },
    "K-Beauty": {
        "keywords": ("k-beauty", "beauty", "화장품", "cosmetic", "odm", "브랜드"),
        "sector_keywords": ("화장품", "생활용품", "소비재"),
        "industry_keywords": ("화장품", "미용", "odm", "cosmetic"),
        "min_score": 5.5,
    },
    "Space / Satellite": {
        "keywords": ("space", "satellite", "우주", "위성", "발사체", "안테나"),
        "sector_keywords": ("항공", "우주", "통신"),
        "industry_keywords": ("위성", "우주", "항공"),
        "min_score": 5.5,
    },
    "Healthcare Diagnostics": {
        "keywords": ("diagnostics", "진단", "분자진단", "체외진단", "시약"),
        "sector_keywords": ("의료", "헬스케어", "제약"),
        "industry_keywords": ("진단", "의료기기", "체외진단"),
        "min_score": 5.5,
    },
    "Industrial Automation": {
        "keywords": ("automation", "산업자동화", "factory automation", "fa", "robotics", "로봇", "스마트팩토리"),
        "sector_keywords": ("기계", "전자", "산업재"),
        "industry_keywords": ("자동화", "로봇", "fa", "스마트팩토리"),
        "min_score": 5.5,
    },
}


def score_equities(equities: list[EquitySnapshot]) -> None:
    for equity in equities:
        _score_value_bucket(equity)
        _score_growth_bucket(equity)
        _score_dividend_potential(equity)
        _score_valuation_framework(equity)
        _score_business_quality(equity)
        _score_liquidity_support(equity)
    _score_ownership_flow(equities)
    _score_relative_industry_value(equities)
    _score_leader_cycle(equities)
    _score_missed_leader_detector(equities)
    for equity in equities:
        _classify_theme(equity)
        _score_rerating_signals(equity)
        _apply_dividend_event_tags(equity)
        _apply_weak_profit_sector_penalty(equity)
        _score_payout_repeatability(equity)
        _score_cashflow_quality(equity)
        _score_governance_warning(equity)
        _score_investability(equity)
        _score_trend_support(equity)
        _apply_value_trap_warning(equity)
        _compute_final_score(equity)
        _classify_value_style(equity)
        _classify_growth_style(equity)
        _classify_stage(equity)
        _classify_recommendation_bucket(equity)
        _classify_leader_bucket(equity)


def _score_value_bucket(equity: EquitySnapshot) -> None:
    score = 0.0
    reasons: list[str] = []
    excluded_reasons: list[str] = []
    effective_dividend_yield = _effective_dividend_yield(equity)

    if equity.per is not None and equity.per <= 10:
        score += 2.0
        score += round(max(0.0, 10 - equity.per) * 0.05, 2)
        reasons.append("PER 10 이하")

    if equity.pbr is not None and equity.pbr <= 1:
        score += 2.0
        score += round(max(0.0, 1 - equity.pbr) * 0.55, 2)
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

    if _is_downtrend(equity.net_income_3y):
        score -= 2.0
        reasons.append("EPS 감소 추세")
    elif _latest_vs_first_change(equity.net_income_3y) <= -20:
        score -= 1.2
        reasons.append("순이익 감소")

    if _is_downtrend(equity.op_income_3y):
        score -= 1.4
        reasons.append("영업이익 감소 추세")

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

    if _is_downtrend(equity.net_income_3y):
        score -= 1.3
        reasons.append("EPS 감소 추세")

    if equity.news_keyword_hits:
        score += min(4.0, len(equity.news_keyword_hits) * 1.2)
        reasons.append("산업 모멘텀 키워드 감지")

    if (
        equity.per is not None
        and equity.per >= 25
        and (equity.forecast_growth_next_year or 0.0) < 25
        and not _has_any_keyword(equity, "공급부족", "ASP 상승", "증설", "데이터센터", "AI")
    ):
        score -= 1.2
        reasons.append("고PER 대비 성장 근거 약함")

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


def _score_valuation_framework(equity: EquitySnapshot) -> None:
    score = 0.0

    if equity.per is not None:
        if equity.per <= 8:
            score += 2.5
        elif equity.per <= 12:
            score += 1.5
        elif equity.per >= 25:
            score -= 1.0

    if equity.peg is not None:
        if equity.peg <= 0.75:
            score += 3.0
        elif equity.peg <= 1.2:
            score += 2.0
        elif equity.peg <= 1.8:
            score += 0.8
        elif equity.peg >= 2.5:
            score -= 1.5

    if equity.roe is not None:
        if equity.roe >= 15:
            score += 2.5
        elif equity.roe >= 10:
            score += 1.5
        elif equity.roe >= 5:
            score += 0.5
        elif equity.roe < 3:
            score -= 1.0

    if equity.industry_per_discount_pct is not None:
        if equity.industry_per_discount_pct >= 30:
            score += 3.0
        elif equity.industry_per_discount_pct >= 20:
            score += 2.0
        elif equity.industry_per_discount_pct >= 10:
            score += 1.2

    equity.valuation_score = round(_clip(score, -10.0, 10.0), 2)


def _score_business_quality(equity: EquitySnapshot) -> None:
    score = 0.0
    profitable_years = sum(1 for value in equity.op_income_3y if (value or 0) > 0)
    net_profitable_years = sum(1 for value in equity.net_income_3y if (value or 0) > 0)

    if profitable_years >= 3:
        score += 3.0
    elif profitable_years == 2:
        score += 1.8
    elif profitable_years == 1:
        score += 0.6

    if len(equity.sales_3y) >= 3 and _sales_resilient(equity.sales_3y):
        score += 1.2
    if len(equity.op_income_3y) >= 3 and _earnings_resilient(equity.op_income_3y):
        score += 1.6
    if net_profitable_years >= 2:
        score += 0.9
    if equity.fcf is not None and equity.fcf > 0:
        score += 1.1
    if equity.debt_ratio is not None:
        if equity.debt_ratio <= 120:
            score += 0.8
        elif equity.debt_ratio >= 220:
            score -= 0.9
    if equity.op_income_volatility is not None:
        if equity.op_income_volatility <= 30:
            score += 0.9
        elif equity.op_income_volatility >= 70:
            score -= 0.7

    equity.business_quality_score = round(score, 2)


def _score_liquidity_support(equity: EquitySnapshot) -> None:
    score = 0.0
    avg_20d = equity.avg_trading_value_20d
    avg_60d = equity.avg_trading_value_60d
    reference = avg_20d or avg_60d

    if reference is not None:
        if reference >= 50_000_000_000:
            score += 3.0
        elif reference >= 10_000_000_000:
            score += 2.2
        elif reference >= 3_000_000_000:
            score += 1.4
        elif reference >= 1_000_000_000:
            score += 0.8
        elif reference >= 300_000_000:
            score += 0.2
        else:
            score -= 1.0
            if "유동성 주의" not in equity.tags:
                equity.tags.append("유동성 주의")

    if avg_20d is not None and avg_60d not in (None, 0):
        ratio = avg_20d / avg_60d
        if ratio >= 1.2:
            score += 0.6
        elif ratio <= 0.65:
            score -= 0.5

    equity.liquidity_support_score = round(score, 2)


def _score_rerating_signals(equity: EquitySnapshot) -> None:
    estimate_revision = 0.0
    tam_expansion = 0.0
    flow_momentum = 0.0
    shareholder_return = 0.0

    forecast = equity.forecast_growth_next_year or 0.0
    earnings_change = _latest_vs_first_change(equity.net_income_3y)
    op_change = _latest_vs_first_change(equity.op_income_3y)
    sales_change = _latest_vs_first_change(equity.sales_3y)
    revision_components = _revision_components(equity)
    if revision_components:
        total_weight = sum(weight for _, weight in revision_components)
        weighted_score = sum(score * weight for score, weight in revision_components)
        estimate_revision = round(weighted_score / total_weight, 2) if total_weight else 0.0
        if estimate_revision >= 5:
            _add_tag(equity, "추정치 개선")
        elif estimate_revision <= -5:
            _add_tag(equity, "추정치 하향")
    else:
        if forecast >= 40:
            estimate_revision += 3.2
        elif forecast >= 20:
            estimate_revision += 2.0
        elif forecast >= 10:
            estimate_revision += 0.8

        if earnings_change >= 50:
            estimate_revision += 1.8
        elif earnings_change >= 15:
            estimate_revision += 1.0
        elif earnings_change <= -20:
            estimate_revision -= 1.6

        if op_change >= 40:
            estimate_revision += 1.2
        elif op_change <= -15:
            estimate_revision -= 0.8

        if _has_any_keyword(equity, "실적 상향", "컨센서스 상향", "증익", "수주 증가"):
            estimate_revision += 1.8
            _add_tag(equity, "추정치 개선")

    matched_themes = _matched_tam_themes(equity)
    if matched_themes:
        theme_scores = [_cagr_band_score(TAM_THEME_CAGR[theme]) for theme in matched_themes]
        tam_expansion += max(theme_scores)
        if len(theme_scores) >= 2:
            tam_expansion += min(3.0, (sum(sorted(theme_scores, reverse=True)[1:3]) * 0.25))
    if equity.theme_gate_pass and equity.theme_score >= 8.0:
        tam_expansion += 1.0
    elif not equity.theme_gate_pass and matched_themes:
        tam_expansion -= 1.2
    if sales_change >= 30:
        tam_expansion += 1.0
    if _is_uptrend(equity.sales_3y):
        tam_expansion += 0.8
    if _has_any_keyword(equity, "공급부족", "ASP 상승", "가동률 상승", "고부가 믹스 전환", "증설", "CAPA 확대", "점유율 확대", "신규 고객"):
        tam_expansion += 1.2
    if tam_expansion >= 5.0:
        _add_tag(equity, "TAM 확대")

    avg_20d = equity.avg_trading_value_20d or 0.0
    avg_60d = equity.avg_trading_value_60d or 0.0
    if avg_20d > 0 and avg_60d > 0:
        ratio = avg_20d / avg_60d
        if ratio >= 1.35:
            flow_momentum += 2.2
        elif ratio >= 1.1:
            flow_momentum += 1.2
        elif ratio <= 0.7:
            flow_momentum -= 0.8
    if (equity.returns_1m or 0.0) > 0 and (equity.returns_3m or 0.0) > -5:
        flow_momentum += 0.7
    if equity.liquidity_support_score >= 1.4:
        flow_momentum += 0.8
    flow_momentum += equity.ownership_flow_score
    if flow_momentum >= 2.0:
        _add_tag(equity, "수급 개선")

    if _has_any_keyword(equity, "자사주", "소각", "배당 확대", "주주환원"):
        shareholder_return += 2.4
        _add_tag(equity, "주주환원 변화")
    if equity.fcf is not None and equity.fcf > 0 and equity.payout_ratio is not None and equity.payout_ratio < 35:
        shareholder_return += 1.0
    if equity.net_cash is not None and equity.net_cash > 0:
        shareholder_return += 0.8
    if "배당상향 잠재" in equity.tags:
        shareholder_return += 0.8

    dividend_tax_benefit = 0.0
    if (
        (_effective_dividend_yield(equity) or 0.0) >= 3.0
        and not equity.dividend_cut_flag
        and _has_any_keyword(equity, "분리과세", "배당 확대", "밸류업")
    ):
        dividend_tax_benefit += 2.0
        _add_tag(equity, "배당 분리과세 수혜 가능성")
    elif (_effective_dividend_yield(equity) or 0.0) >= 3.5 and not equity.dividend_cut_flag:
        dividend_tax_benefit += 0.8

    tax_exemption_benefit = 0.0
    if _has_any_keyword(equity, "익금불산입", "지주사", "밸류업"):
        tax_exemption_benefit += 1.8
        _add_tag(equity, "익금불산입 수혜 가능성")

    governance_reform = 0.0
    if _has_any_keyword(equity, "지배구조", "인적분할", "합병", "밸류업"):
        governance_reform += 2.0
        _add_tag(equity, "지배구조 개편 가능성")
    elif (equity.pbr or 9) <= 0.5 and (equity.net_cash or 0) > 0:
        governance_reform += 0.8

    commercial_code_benefit = 0.0
    if _has_any_keyword(equity, "상법 개정", "주주환원", "자사주", "소각"):
        commercial_code_benefit += 2.0
        _add_tag(equity, "상법 개정 수혜 가능성")
    elif (equity.pbr or 9) <= 0.6 and (equity.roe or 0) >= 8:
        commercial_code_benefit += 0.8

    if _has_any_keyword(equity, "자사주", "소각"):
        equity.treasury_burn_recent = True
        _add_tag(equity, "최근 자사주 소각")
        shareholder_return += 1.4

    equity.dividend_tax_benefit_score = round(dividend_tax_benefit, 2)
    equity.tax_exemption_benefit_score = round(tax_exemption_benefit, 2)
    equity.governance_reform_score = round(governance_reform, 2)
    equity.commercial_code_benefit_score = round(commercial_code_benefit, 2)

    shareholder_return += (
        dividend_tax_benefit
        + tax_exemption_benefit
        + governance_reform * 0.7
        + commercial_code_benefit * 0.8
    )

    if forecast >= 35 and tam_expansion >= 5.0 and equity.per is not None and equity.per >= 20:
        _add_tag(equity, "고PER 정당화 가능")

    equity.estimate_revision_score = round(estimate_revision, 2)
    equity.tam_expansion_score = round(tam_expansion, 2)
    equity.flow_momentum_score = round(flow_momentum, 2)
    equity.shareholder_return_score = round(shareholder_return, 2)
    equity.policy_score = round(
        shareholder_return
        + dividend_tax_benefit * 0.5
        + tax_exemption_benefit * 0.7
        + governance_reform * 0.7
        + commercial_code_benefit * 0.7,
        2,
    )

    rerating_total = estimate_revision + tam_expansion + flow_momentum + shareholder_return
    equity.value_score = round(equity.value_score + estimate_revision * 0.55 + shareholder_return * 0.45 + flow_momentum * 0.3, 2)
    equity.growth_early_score = round(
        equity.growth_early_score + estimate_revision * 0.7 + tam_expansion * 0.75 + flow_momentum * 0.4,
        2,
    )
    if rerating_total >= 5.5:
        _add_tag(equity, "재평가 후보")


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

    if (
        effective_dividend_yield >= 3
        and equity.fcf not in (None, 0)
        and profitable_years >= 2
        and equity.business_quality_score >= 3.0
        and "가치 함정 주의" not in equity.tags
        and "배당 불안정" not in equity.tags
        and equity.liquidity_support_score > -1.0
    ):
        equity.value_style = "Dividend Compounder"
    elif turnaround:
        equity.value_style = "Turnaround Value"
    elif (equity.per is not None and equity.per <= 8) or (equity.pbr is not None and equity.pbr <= 0.6):
        equity.value_style = "Deep Value"
    else:
        equity.value_style = "Balanced Value"


def _classify_growth_style(equity: EquitySnapshot) -> None:
    latest_two_op = [value for value in equity.op_income_3y[-2:] if value is not None]
    latest_two_net = [value for value in equity.net_income_3y[-2:] if value is not None]
    profitable_now = len(latest_two_op) >= 2 and all(value > 0 for value in latest_two_op)
    net_profitable_now = len(latest_two_net) >= 1 and latest_two_net[-1] > 0
    forecast = equity.forecast_growth_next_year or 0.0
    reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d or 0.0
    trend_ok = _is_uptrend(equity.sales_3y) or _is_uptrend(equity.op_income_3y)
    revision_ok = equity.estimate_revision_score >= 3.0
    theme_ok = equity.tam_expansion_score >= 5.0
    investable = (
        reference >= 10_000_000_000
        and (equity.market_cap or 0.0) >= 300_000_000_000
        and equity.investability_score >= 3.0
    )
    quality_ok = equity.business_quality_score >= 5.0 and equity.cashflow_quality_score >= 0.0
    if (
        profitable_now
        and net_profitable_now
        and quality_ok
        and investable
        and (forecast >= 15 or revision_ok or theme_ok)
        and trend_ok
        and "가치 함정 주의" not in equity.tags
    ):
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


def _apply_value_trap_warning(equity: EquitySnapshot) -> None:
    risk = 0.0
    effective_dividend_yield = _effective_dividend_yield(equity) or 0.0
    normalized = equity.dividend_yield_normalized or 0.0
    latest_op = next((value for value in reversed(equity.op_income_3y) if value is not None), None)

    if effective_dividend_yield >= 4 and "배당 불안정" in equity.tags:
        risk += 1.0
    if normalized >= 3 and "감액배당 주의" in equity.tags:
        risk += 0.9
    if equity.business_quality_score <= 1.6:
        risk += 1.1
    if equity.liquidity_support_score <= -0.5:
        risk += 1.0
    if equity.debt_ratio is not None and equity.debt_ratio >= 220:
        risk += 0.9
    if latest_op is not None and latest_op <= 0:
        risk += 0.8
    if equity.returns_12m is not None and equity.returns_12m <= -20:
        risk += 0.6
    if "이익생산 약한 섹터" in equity.tags:
        risk += 0.5
    if equity.estimate_revision_score <= -1.0:
        risk += 1.2
    if equity.shareholder_return_score <= 0 and _latest_vs_first_change(equity.net_income_3y) < -20:
        risk += 0.7
    if equity.governance_warning_score >= 3.0:
        risk += min(1.8, equity.governance_warning_score * 0.45)
    if equity.cashflow_quality_score <= -1.0:
        risk += 0.9
    if equity.payout_repeatability_score <= -1.0:
        risk += 0.7

    equity.value_trap_risk_score = round(risk, 2)
    if risk >= 2.2 and "가치 함정 주의" not in equity.tags:
        equity.tags.append("가치 함정 주의")
    if risk > 0:
        equity.value_score = round(equity.value_score - min(2.4, risk * 0.7), 2)
        equity.dividend_potential_score = round(
            equity.dividend_potential_score - min(1.2, risk * 0.25),
            2,
        )
    if equity.business_quality_score > 0:
        equity.value_score = round(equity.value_score + min(2.0, equity.business_quality_score * 0.22), 2)
    if equity.liquidity_support_score > 0:
        equity.value_score = round(equity.value_score + min(1.2, equity.liquidity_support_score * 0.2), 2)
        equity.growth_early_score = round(
            equity.growth_early_score + min(0.8, equity.liquidity_support_score * 0.12),
            2,
        )


def _score_payout_repeatability(equity: EquitySnapshot) -> None:
    score = 0.0
    paid_dividends = [value for value in equity.dividends_3y if value not in (None, 0)]
    if len(paid_dividends) >= 3:
        score += 2.5
    elif len(paid_dividends) == 2:
        score += 1.0
    else:
        score -= 1.6

    if equity.dividend_cut_flag:
        score -= 1.6
        _add_tag(equity, "배당 감액 이력")
    if "배당 불안정" in equity.tags:
        score -= 1.0
    if equity.payout_ratio is not None:
        if equity.payout_ratio >= 20:
            score += 1.2
        elif equity.payout_ratio >= 10:
            score += 0.5
        elif equity.payout_ratio < 5:
            score -= 1.0
            _add_tag(equity, "낮은 배당성향")
    if equity.payout_increase_flag:
        score += 0.8
    if equity.dividend_growth_rate is not None and equity.dividend_growth_rate > 0:
        score += 0.5

    equity.payout_repeatability_score = round(score, 2)


def _score_cashflow_quality(equity: EquitySnapshot) -> None:
    score = 0.0
    positive_op_years = sum(1 for value in equity.op_income_3y if (value or 0) > 0)
    latest_op = next((value for value in reversed(equity.op_income_3y) if value is not None), None)
    latest_net = next((value for value in reversed(equity.net_income_3y) if value is not None), None)

    if equity.fcf is not None:
        if equity.fcf > 0:
            score += 2.0
        else:
            score -= 1.6

    if positive_op_years >= 3:
        score += 1.4
    elif positive_op_years <= 1:
        score -= 1.0

    if latest_op is not None and latest_op <= 0:
        score -= 1.4
    if latest_net is not None and latest_op not in (None, 0):
        earnings_gap = latest_net - latest_op
        if latest_net > 0 and earnings_gap > abs(latest_op) * 0.8:
            score -= 1.0
            _add_tag(equity, "비경상 이익 의심")
    if equity.debt_ratio is not None and equity.debt_ratio >= 180:
        score -= 0.8
    if equity.net_cash is not None and equity.net_cash > 0:
        score += 0.6

    equity.cashflow_quality_score = round(score, 2)


def _score_governance_warning(equity: EquitySnapshot) -> None:
    score = 0.0
    cheap = (equity.per is not None and equity.per <= 5) or (equity.pbr is not None and equity.pbr <= 0.5)
    cash_rich = (
        equity.market_cap not in (None, 0)
        and (
            (equity.net_cash is not None and equity.net_cash >= equity.market_cap * 0.2)
            or (equity.cash_assets is not None and equity.cash_assets >= equity.market_cap * 0.25)
        )
    )
    weak_return_policy = (
        (equity.payout_ratio is not None and equity.payout_ratio < 10)
        or equity.shareholder_return_score <= 0.5
        or equity.payout_repeatability_score < 0
    )

    if cheap and weak_return_policy:
        score += 1.8
    if cheap and cash_rich and weak_return_policy:
        score += 1.7
        _add_tag(equity, "거버넌스 할인 의심")
    if equity.treasury_stock_ratio not in (None, 0) and not equity.treasury_burn_recent:
        score += 0.6
    if "배당 감액 이력" in equity.tags:
        score += 0.5
    if "특별배당 가능성" in equity.tags and (equity.dividend_yield_normalized or 0.0) < 2.0:
        score += 0.4

    equity.governance_warning_score = round(score, 2)


def _score_investability(equity: EquitySnapshot) -> None:
    score = 0.0
    reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d
    if reference is not None:
        if reference >= 10_000_000_000:
            score += 3.0
        elif reference >= 3_000_000_000:
            score += 1.3
        else:
            score -= 2.0
    else:
        score -= 0.6

    if equity.market_cap is not None:
        if equity.market_cap >= 300_000_000_000:
            score += 1.6
        elif equity.market_cap >= 100_000_000_000:
            score += 0.6
        else:
            score -= 1.1
    if equity.cashflow_quality_score > 0:
        score += min(1.2, equity.cashflow_quality_score * 0.35)
    if equity.governance_warning_score >= 2.5:
        score -= min(2.0, equity.governance_warning_score * 0.45)
    if equity.payout_repeatability_score < 0:
        score -= 0.8

    equity.investability_score = round(score, 2)


def _score_trend_support(equity: EquitySnapshot) -> None:
    score = 0.0
    close = equity.close
    ma20 = equity.ma_20
    ma60 = equity.ma_60
    ma120 = equity.ma_120

    if close in (None, 0) or ma20 is None or ma60 is None or ma120 is None:
        equity.trend_support_score = 0.0
        return

    bullish_stack = close >= ma20 >= ma60 >= ma120
    early_bullish = close >= ma20 >= ma60 and ma120 <= ma60
    breakdown = close < ma20 and ma20 < ma60
    long_break = close < ma120 and ma60 < ma120

    if bullish_stack:
        score += 3.0
        if equity.returns_6m not in (None, 0) and (equity.returns_6m or 0.0) >= 15:
            score += 1.0
        if equity.stage in {"중간", "후반"}:
            _add_tag(equity, "조기매도 경계")
        else:
            _add_tag(equity, "추세 유지")
    elif early_bullish:
        score += 1.5
        _add_tag(equity, "추세 유지")
    elif breakdown:
        score -= 1.5
        _add_tag(equity, "단기 추세 약화")
    elif long_break:
        score -= 3.0
        _add_tag(equity, "사이클 종료 점검")

    if close >= ma120 and ma20 >= ma120:
        score += 0.5
    elif close < ma120:
        score -= 0.8

    equity.trend_support_score = round(score, 2)


def _classify_recommendation_bucket(equity: EquitySnapshot) -> None:
    reasons: list[str] = []
    equity.core_bucket = None
    reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d
    liquidity_gate_fail = reference is None or reference < 10_000_000_000
    micro_liquidity = reference is not None and reference < 3_000_000_000
    weak_repeatability = equity.payout_repeatability_score < 0.5
    weak_cashflow = equity.cashflow_quality_score < 0.5
    severe_cashflow = equity.cashflow_quality_score <= -1.0
    governance_warning = equity.governance_warning_score >= 2.5
    trap_warning = equity.value_trap_risk_score >= 2.8 or "가치 함정 주의" in equity.tags
    hard_gateway_fail = _fails_minimum_gateway(equity)

    if liquidity_gate_fail:
        reasons.append("일평균 거래대금 10억 미만")
    if weak_repeatability:
        reasons.append("배당 반복성 약함")
    if weak_cashflow:
        reasons.append("현금창출 질 확인 필요")
    if governance_warning:
        reasons.append("거버넌스 할인 의심")
    if trap_warning:
        reasons.append("가치함정 경고")
    if hard_gateway_fail:
        reasons.append("최소 현실성 게이트 미통과")

    growth_heat = equity.stage in {"후반", "과열"} or "추격주의" in equity.tags
    trailing_dividend = equity.dividend_yield_trailing or 0.0
    normalized_dividend = equity.dividend_yield_normalized or 0.0
    dividend_distortion = (
        "특별배당 가능성" in equity.tags
        and trailing_dividend >= 1.0
        and normalized_dividend < max(1.0, trailing_dividend * 0.45)
    )
    weak_profit_sector = "이익생산 약한 섹터" in equity.tags
    high_growth_multiple = (equity.per or 0.0) >= 25 or (equity.pbr or 0.0) >= 5.0
    premium_growth_multiple = (equity.per or 0.0) >= 40 or (equity.pbr or 0.0) >= 7.0
    strong_growth_evidence = (
        equity.estimate_revision_score >= 5.0
        and equity.tam_expansion_score >= 5.0
        and equity.business_quality_score >= 7.0
        and equity.cashflow_quality_score >= 1.4
    )

    cheap_profile = (equity.per or 99) <= 6 or (equity.pbr or 99) <= 0.6
    value_conviction = (
        (
            ((equity.per or 999) <= 12 and (equity.pbr or 999) <= 1.8)
            or ((equity.pbr or 999) <= 0.8 and (equity.per or 999) <= 20)
            or (
                (equity.industry_per_discount_pct or 0) >= 20
                and (equity.per or 999) <= 18
                and (equity.pbr or 999) <= 2.0
            )
        )
        and equity.business_quality_score >= 5.0
        and equity.cashflow_quality_score >= 1.0
        and equity.investability_score >= 3.0
        and equity.stage != "과열"
        and (equity.growth_style != "Growth Speculative" or ((equity.per or 999) <= 10 and (equity.pbr or 999) <= 1.2))
        and not governance_warning
        and not trap_warning
    )
    growth_conviction = (
        equity.growth_style == "Growth Proven"
        and equity.estimate_revision_score >= 3.0
        and equity.business_quality_score >= 5.0
        and equity.cashflow_quality_score >= 1.0
        and equity.investability_score >= 3.0
        and (equity.tam_expansion_score >= 1.8 or equity.ownership_flow_score >= 5.0)
        and (equity.per is None or equity.per <= 60 or "고PER 정당화 가능" in equity.tags)
        and not dividend_distortion
        and not (growth_heat and not strong_growth_evidence)
        and not (premium_growth_multiple and not strong_growth_evidence)
        and not (weak_profit_sector and (equity.estimate_revision_score < 5.0 or equity.business_quality_score < 6.5))
        and not (
            high_growth_multiple
            and equity.ownership_flow_score < 5.0
            and equity.tam_expansion_score < 5.0
        )
        and equity.stage != "과열"
        and not governance_warning
        and not trap_warning
    )
    turnaround_exception = (
        equity.value_style == "Turnaround Value"
        and not liquidity_gate_fail
        and equity.cashflow_quality_score >= 1.0
        and equity.business_quality_score >= 4.5
        and not governance_warning
        and not trap_warning
    )

    if equity.excluded or severe_cashflow or hard_gateway_fail:
        equity.recommendation_bucket = "제외"
    elif (trap_warning or (governance_warning and cheap_profile)) and (cheap_profile or governance_warning):
        equity.recommendation_bucket = "가치함정 경고"
    elif (
        not liquidity_gate_fail
        and (value_conviction or growth_conviction or turnaround_exception)
        and (equity.payout_repeatability_score >= 1.0 or growth_conviction or turnaround_exception)
        and (equity.cashflow_quality_score >= 1.0 or turnaround_exception)
        and (equity.final_score >= 22 or (turnaround_exception and equity.final_score >= 10))
        and (equity.business_quality_score >= 5.0 or turnaround_exception)
        and (equity.estimate_revision_score >= -1.0 or (turnaround_exception and equity.estimate_revision_score >= -3.0))
        and (equity.investability_score >= 3.0 or (turnaround_exception and equity.investability_score >= 2.0))
    ):
        equity.recommendation_bucket = "실매수 검토"
        if value_conviction and not growth_conviction:
            equity.core_bucket = "Value Core"
        elif growth_conviction and not value_conviction:
            equity.core_bucket = "Growth Core"
        elif turnaround_exception:
            equity.core_bucket = "Value Core"
        elif value_conviction and growth_conviction:
            value_side = (equity.value_score or 0.0) + (equity.valuation_score or 0.0)
            growth_side = (
                (equity.growth_early_score or 0.0)
                + (equity.estimate_revision_score or 0.0)
                + (equity.tam_expansion_score or 0.0)
            )
            equity.core_bucket = "Growth Core" if growth_side > value_side else "Value Core"
    elif (
        (micro_liquidity or liquidity_gate_fail or equity.investability_score < 3.0 or equity.business_quality_score < 5.0)
        and equity.final_score >= 22
        and equity.business_quality_score >= 3.8
        and equity.cashflow_quality_score >= 0.0
        and equity.payout_repeatability_score >= 0.5
        and not hard_gateway_fail
    ):
        equity.recommendation_bucket = "소액 관찰"
    elif equity.final_score >= 20 and equity.cashflow_quality_score >= -0.2:
        equity.recommendation_bucket = "보류"
    else:
        equity.recommendation_bucket = "제외"

    bucket_reason_order = {
        "실매수 검토": [
            "유동성 기준 통과",
            "배당 반복성 양호",
            "현금창출 질 양호",
            "거버넌스 경고 약함",
        ],
        "소액 관찰": [
            "유동성은 부족하지만 구조는 관찰 가능",
            "핵심 점수는 유지",
        ],
        "보류": [
            "재평가 요소는 있으나 확신 부족",
        ],
        "제외": reasons or ["핵심 게이트 미통과"],
        "가치함정 경고": reasons or ["저평가처럼 보이나 구조적 할인 의심"],
    }
    if equity.recommendation_bucket == "실매수 검토":
        equity.recommendation_reasons = bucket_reason_order["실매수 검토"] + reasons[:1]
        if equity.core_bucket == "Value Core":
            equity.recommendation_reasons[0] = "Value Core 기준 통과"
        elif equity.core_bucket == "Growth Core":
            equity.recommendation_reasons[0] = "Growth Core 기준 통과"
        if turnaround_exception:
            equity.recommendation_reasons[1] = "턴어라운드 예외 적용"
    elif equity.recommendation_bucket == "소액 관찰":
        equity.recommendation_reasons = bucket_reason_order["소액 관찰"] + reasons[:2]
    else:
        equity.recommendation_reasons = bucket_reason_order[equity.recommendation_bucket]


def _classify_leader_bucket(equity: EquitySnapshot) -> None:
    equity.leader_bucket = None
    reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d or 0.0
    market_cap = equity.market_cap or 0.0
    if reference < 3_000_000_000 or market_cap < 300_000_000_000 or equity.value_trap_risk_score >= 2.8:
        return
    trend_or_high = equity.trend_support_score >= 1.5 or (equity.high_52w_ratio or 0.0) >= 80.0

    if (
        equity.leader_cycle_score >= 8.0
        and trend_or_high
        and equity.returns_3m not in (None, 0)
        and (equity.returns_3m or 0.0) >= 25
        and reference >= 10_000_000_000
        and market_cap >= 300_000_000_000
        and equity.value_trap_risk_score < 1.5
    ):
        equity.leader_bucket = "Leader"
    elif (
        equity.leader_cycle_score >= 6.0
        and ((equity.returns_3m or 0.0) >= 10 or (equity.returns_1m or 0.0) >= 8)
        and (equity.trend_support_score >= 0.0 or (equity.high_52w_ratio or 0.0) >= 75.0)
        and equity.estimate_revision_score >= 0.8
        and reference >= 3_000_000_000
    ):
        equity.leader_bucket = "Leader Candidate"
    elif (
        (equity.returns_3m or 0.0) > 0
        and equity.leader_cycle_score >= 1.0
    ):
        equity.leader_bucket = "Follower"


def _is_uptrend(values: list[float | None]) -> bool:
    cleaned = [value for value in values if value is not None]
    return len(cleaned) >= 3 and cleaned[0] < cleaned[1] < cleaned[2]


def _trend_strength(values: list[float | None], cap: float) -> float:
    cleaned = [value for value in values if value not in (None, 0)]
    if len(cleaned) < 2 or cleaned[0] == 0:
        return 0.0
    growth = max(0.0, (cleaned[-1] / cleaned[0]) - 1)
    return round(min(cap, growth * 0.6), 2)


def _latest_vs_first_change(values: list[float | None]) -> float:
    cleaned = [value for value in values if value not in (None, 0)]
    if len(cleaned) < 2 or cleaned[0] == 0:
        return 0.0
    return round(((cleaned[-1] / cleaned[0]) - 1) * 100, 2)


def _is_downtrend(values: list[float | None]) -> bool:
    cleaned = [value for value in values if value is not None]
    return len(cleaned) >= 3 and cleaned[0] > cleaned[1] > cleaned[2]


def _sales_resilient(values: list[float | None]) -> bool:
    cleaned = [value for value in values if value not in (None, 0)]
    if len(cleaned) < 3:
        return False
    trough = min(cleaned)
    peak = max(cleaned)
    return trough >= peak * 0.72


def _earnings_resilient(values: list[float | None]) -> bool:
    cleaned = [value for value in values if value is not None]
    if len(cleaned) < 3:
        return False
    positives = [value for value in cleaned if value > 0]
    return len(positives) >= 2 and cleaned[-1] >= cleaned[0] * 0.7


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


def _theme_text_blob(equity: EquitySnapshot) -> str:
    parts = [
        equity.name or "",
        equity.sector or "",
        equity.industry or "",
        " ".join(equity.news_keyword_hits),
        " ".join(equity.important_news_items),
        " ".join(equity.important_disclosures),
    ]
    return " ".join(filter(None, parts)).lower()


def _has_any_keyword(equity: EquitySnapshot, *keywords: str) -> bool:
    hits = {item.lower() for item in equity.news_keyword_hits}
    return any(keyword.lower() in hits for keyword in keywords)


def _add_tag(equity: EquitySnapshot, tag: str) -> None:
    if tag not in equity.tags:
        equity.tags.append(tag)


def _compute_final_score(equity: EquitySnapshot) -> None:
    valuation = _scale_component(equity.valuation_score, positive_scale=10.0, negative_scale=10.0)
    estimate_revision = _scale_component(equity.estimate_revision_score, positive_scale=10.0, negative_scale=10.0)
    tam_expansion = _scale_component(equity.tam_expansion_score, positive_scale=13.0, negative_scale=10.0)
    ownership = _scale_component(equity.ownership_flow_score, positive_scale=10.0, negative_scale=5.0)
    policy = _scale_component(equity.policy_score, positive_scale=12.0, negative_scale=8.0)
    business_quality = _scale_component(equity.business_quality_score, positive_scale=8.5, negative_scale=5.0)
    investability = _scale_component(equity.investability_score, positive_scale=6.0, negative_scale=6.0)
    trend_support = _scale_component(equity.trend_support_score, positive_scale=4.5, negative_scale=4.5)

    base_score = (
        valuation * 0.20
        + estimate_revision * 0.25
        + tam_expansion * 0.20
        + ownership * 0.15
        + policy * 0.10
        + business_quality * 0.10
        + investability * 0.10
        + trend_support * 0.08
    )
    final_score = base_score - _realism_penalty(equity)
    equity.final_score = round(final_score, 2)
    if equity.final_score >= 70:
        _add_tag(equity, "High Conviction")
    elif equity.final_score >= 55:
        _add_tag(equity, "Core Watch")


def _score_ownership_flow(equities: list[EquitySnapshot]) -> None:
    scored = [
        equity for equity in equities
        if equity.net_buy_ratio_3m is not None
    ]
    if not scored:
        return

    ranked = sorted(scored, key=lambda item: item.net_buy_ratio_3m or 0.0, reverse=True)
    count = len(ranked)
    for index, equity in enumerate(ranked, start=1):
        percentile = index / count
        if percentile <= 0.05:
            score = 10.0
        elif percentile <= 0.10:
            score = 8.0
        elif percentile <= 0.20:
            score = 5.0
        elif percentile >= 0.80:
            score = -5.0
        else:
            score = 0.0
        if equity.etf_holding_change_3m not in (None, 0):
            score += min(2.0, equity.etf_holding_change_3m * 0.5)
        equity.ownership_flow_score = round(score, 2)
        if score >= 8:
            _add_tag(equity, "강한 실수급")
        elif score <= -5:
            _add_tag(equity, "실수급 약세")


def _score_relative_industry_value(equities: list[EquitySnapshot]) -> None:
    industry_map: dict[str, list[float]] = {}
    for equity in equities:
        industry = (equity.industry or equity.sector or "").strip()
        if not industry or equity.per in (None, 0) or equity.per <= 0:
            continue
        industry_map.setdefault(industry, []).append(equity.per)

    industry_avg_map: dict[str, float] = {}
    for industry, pers in industry_map.items():
        if len(pers) < 4:
            continue
        industry_avg_map[industry] = round(sum(pers) / len(pers), 2)

    for equity in equities:
        industry = (equity.industry or equity.sector or "").strip()
        avg_per = industry_avg_map.get(industry)
        equity.industry_avg_per = avg_per
        if avg_per in (None, 0) or equity.per in (None, 0) or equity.per <= 0:
            continue
        discount_pct = round((1 - (equity.per / avg_per)) * 100, 2)
        equity.industry_per_discount_pct = discount_pct

        if discount_pct >= 30:
            score = 10.0
        elif discount_pct >= 20:
            score = 7.0
        elif discount_pct >= 10:
            score = 5.0
        else:
            score = 0.0

        if score > 0:
            equity.value_score = round(equity.value_score + score * 0.4, 2)
            if "산업 대비 저평가" not in equity.tags:
                equity.tags.append("산업 대비 저평가")


def _score_missed_leader_detector(equities: list[EquitySnapshot]) -> None:
    for equity in equities:
        score = 0.0

        if equity.estimate_revision_score >= 5:
            score += 2.5
        if equity.tam_expansion_score >= 5:
            score += 2.5
        if equity.ownership_flow_score >= 5:
            score += 2.0
        if equity.high_52w_ratio is not None:
            discount_from_high = 100 - equity.high_52w_ratio
            if 15 <= discount_from_high <= 35:
                score += 1.5
        if (
            equity.per is not None
            and equity.industry_avg_per not in (None, 0)
            and equity.per <= equity.industry_avg_per
        ):
            score += 1.5

        equity.missed_leader_score = round(score, 2)
        if score >= 8.5:
            _add_tag(equity, "Missed Leader")


def _score_leader_cycle(equities: list[EquitySnapshot]) -> None:
    market_returns_3m: dict[str, list[float]] = {}
    sector_returns_3m: dict[str, list[float]] = {}
    sector_returns_1m: dict[str, list[float]] = {}

    for equity in equities:
        if equity.returns_3m is not None:
            market_returns_3m.setdefault(equity.market, []).append(equity.returns_3m)
            sector = (equity.industry or equity.sector or "").strip()
            if sector:
                sector_returns_3m.setdefault(sector, []).append(equity.returns_3m)
        if equity.returns_1m is not None:
            sector = (equity.industry or equity.sector or "").strip()
            if sector:
                sector_returns_1m.setdefault(sector, []).append(equity.returns_1m)

    market_baseline = {
        market: _median(values) for market, values in market_returns_3m.items() if values
    }

    for equity in equities:
        score = 0.0
        sector = (equity.industry or equity.sector or "").strip()
        market_baseline_3m = market_baseline.get(equity.market, 0.0)
        rel_3m = (equity.returns_3m or 0.0) - market_baseline_3m
        rel_1m = equity.returns_1m or 0.0
        reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d or 0.0
        market_cap = equity.market_cap or 0.0

        sector_top_3m = max(sector_returns_3m.get(sector, [0.0])) if sector else 0.0
        sector_top_1m = max(sector_returns_1m.get(sector, [0.0])) if sector else 0.0
        near_sector_leader_3m = sector_top_3m > 0 and (equity.returns_3m or 0.0) >= sector_top_3m * 0.8
        near_sector_leader_1m = sector_top_1m > 0 and (equity.returns_1m or 0.0) >= sector_top_1m * 0.8

        if rel_3m >= 25:
            score += 3.5
        elif rel_3m >= 15:
            score += 2.5
        elif rel_3m >= 7:
            score += 1.5
        elif rel_3m <= -10:
            score -= 2.0

        if rel_1m >= 8:
            score += 1.0
        elif rel_1m <= -8:
            score -= 0.8

        if near_sector_leader_3m:
            score += 2.0
        if near_sector_leader_1m:
            score += 1.2

        if equity.trend_support_score >= 3.0:
            score += 2.0
        elif equity.trend_support_score >= 1.5:
            score += 1.0
        elif equity.trend_support_score < 0:
            score -= 1.5

        if equity.high_52w_ratio is not None:
            if equity.high_52w_ratio >= 92:
                score += 1.6
            elif equity.high_52w_ratio >= 82:
                score += 0.8
            elif equity.high_52w_ratio <= 70:
                score -= 1.0

        if (equity.avg_trading_value_20d or 0.0) >= 20_000_000_000:
            score += 1.2
        elif (equity.avg_trading_value_20d or 0.0) >= 10_000_000_000:
            score += 0.7

        if equity.ownership_flow_score >= 5.0:
            score += 1.8
        elif equity.ownership_flow_score <= -5.0:
            score -= 1.0

        if equity.estimate_revision_score >= 5.0:
            score += 1.4
        elif equity.estimate_revision_score <= -3.0:
            score -= 1.0

        if reference < 3_000_000_000:
            score -= 2.2
        elif reference < 10_000_000_000:
            score -= 1.0
        if market_cap < 100_000_000_000:
            score -= 2.0
        elif market_cap < 300_000_000_000:
            score -= 1.0

        if "추격주의" in equity.tags and equity.trend_support_score < 3.5:
            score -= 1.5
        if "이익생산 약한 섹터" in equity.tags and equity.business_quality_score < 6.5:
            score -= 1.0
        if equity.value_trap_risk_score >= 1.5:
            score -= 1.5
        if equity.business_quality_score < 5.0:
            score -= 1.2
        if equity.cashflow_quality_score < 0:
            score -= 1.2

        equity.leader_cycle_score = round(score, 2)
        if score >= 8.5:
            _add_tag(equity, "Cycle Leader")
        elif score >= 6.0:
            _add_tag(equity, "Leader Candidate")
        elif score <= 1.0 and rel_3m > 0:
            _add_tag(equity, "Follower")


def _matched_tam_themes(equity: EquitySnapshot) -> list[str]:
    if equity.theme_gate_pass and equity.theme:
        matches = [equity.theme]
        if equity.sub_theme and equity.sub_theme != equity.theme:
            matches.append(equity.sub_theme)
        return [theme for theme in matches if theme in TAM_THEME_CAGR]

    label_text = _theme_text_blob(equity)
    matched: list[str] = []
    for theme, aliases in TAM_THEME_ALIASES.items():
        hits = sum(1 for alias in aliases if alias.lower() in label_text)
        if hits >= 2:
            matched.append(theme)
    return matched


def _cagr_band_score(cagr: float) -> float:
    if cagr >= 15:
        return 10.0
    if cagr >= 10:
        return 7.0
    if cagr >= 5:
        return 5.0
    if cagr >= 0:
        return 2.0
    return -5.0


def _realism_penalty(equity: EquitySnapshot) -> float:
    penalty = 0.0
    reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d or 0.0
    market_cap = equity.market_cap or 0.0

    if reference < 1_000_000_000:
        penalty += 4.0
    elif reference < 3_000_000_000:
        penalty += 2.5
    elif reference < 10_000_000_000:
        penalty += 1.2

    if market_cap < 100_000_000_000:
        penalty += 2.4
    elif market_cap < 300_000_000_000:
        penalty += 1.1

    speculative_growth = (
        equity.tam_expansion_score >= 8.0
        and ((equity.market_cap or 0.0) < 300_000_000_000 or reference < 10_000_000_000)
    )
    if speculative_growth:
        penalty += 1.0
    if "이익생산 약한 섹터" in equity.tags and equity.business_quality_score < 6.0:
        penalty += 0.8
    if "가치 함정 주의" in equity.tags:
        penalty += min(2.0, max(0.8, equity.value_trap_risk_score * 0.45))
    if equity.cashflow_quality_score < 0:
        penalty += min(1.5, abs(equity.cashflow_quality_score) * 0.5)

    return round(penalty, 2)


def _fails_minimum_gateway(equity: EquitySnapshot) -> bool:
    reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d or 0.0
    market_cap = equity.market_cap or 0.0
    has_core_value = equity.close is not None and equity.per is not None and equity.pbr is not None
    weak_quality = equity.business_quality_score < 3.5 or equity.cashflow_quality_score < 0.0
    speculative_theme = equity.tam_expansion_score >= 8.0 and market_cap < 300_000_000_000

    if not has_core_value and market_cap < 300_000_000_000:
        return True
    if reference < 1_000_000_000 and market_cap < 100_000_000_000:
        return True
    if speculative_theme and reference < 10_000_000_000:
        return True
    if equity.theme and not equity.theme_gate_pass and equity.tam_expansion_score >= 6.0 and market_cap < 300_000_000_000:
        return True
    if "가치 함정 주의" in equity.tags and weak_quality and market_cap < 300_000_000_000:
        return True
    return False


def _classify_theme(equity: EquitySnapshot) -> None:
    text_blob = _theme_text_blob(equity)
    news_text = " ".join(equity.important_news_items).lower()
    disclosure_text = " ".join(equity.important_disclosures).lower()
    sector_text = " ".join(filter(None, [equity.sector or "", equity.industry or ""])).lower()
    scored: list[tuple[float, str, list[str], list[str]]] = []

    for theme, profile in THEME_PROFILES.items():
        score = 0.0
        evidence: list[str] = []
        raw_hits: list[str] = []

        sector_hits = [keyword for keyword in profile["sector_keywords"] if keyword.lower() in sector_text]
        if sector_hits:
            score += 2.6 + min(1.0, (len(sector_hits) - 1) * 0.4)
            evidence.append(f"업종 정합: {', '.join(sector_hits[:2])}")
            raw_hits.extend(sector_hits[:2])

        industry_hits = [keyword for keyword in profile["industry_keywords"] if keyword.lower() in sector_text]
        if industry_hits:
            score += 2.8 + min(1.2, (len(industry_hits) - 1) * 0.5)
            evidence.append(f"세부 산업: {', '.join(industry_hits[:2])}")
            raw_hits.extend(industry_hits[:2])

        keyword_hits = [keyword for keyword in profile["keywords"] if keyword.lower() in text_blob]
        if keyword_hits:
            keyword_score = min(4.2, 1.6 + len(keyword_hits) * 0.95)
            score += keyword_score
            evidence.append(f"키워드 근거: {', '.join(keyword_hits[:3])}")
            raw_hits.extend(keyword_hits[:3])

        news_hits = [keyword for keyword in profile["keywords"] if keyword.lower() in news_text]
        if news_hits:
            score += min(2.2, 1.0 + len(news_hits) * 0.4)
            evidence.append(f"뉴스 확인: {', '.join(news_hits[:2])}")
            raw_hits.extend(news_hits[:2])

        disclosure_hits = [keyword for keyword in profile["keywords"] if keyword.lower() in disclosure_text]
        if disclosure_hits:
            score += min(2.0, 1.0 + len(disclosure_hits) * 0.35)
            evidence.append(f"공시 확인: {', '.join(disclosure_hits[:2])}")
            raw_hits.extend(disclosure_hits[:2])

        if score > 0:
            scored.append((round(score, 2), theme, evidence, raw_hits))

    if not scored:
        equity.theme = "미분류"
        equity.sub_theme = ""
        equity.theme_score = 0.0
        equity.theme_confidence = "낮음"
        equity.theme_gate_pass = False
        equity.theme_evidence = ["테마 근거 부족"]
        return

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_theme, best_evidence, best_hits = scored[0]
    second_theme = scored[1][1] if len(scored) > 1 and scored[1][0] >= max(5.0, best_score - 1.2) else ""
    profile = THEME_PROFILES[best_theme]
    sector_hits = [keyword for keyword in profile["sector_keywords"] if keyword.lower() in sector_text]
    industry_hits = [keyword for keyword in profile["industry_keywords"] if keyword.lower() in sector_text]
    keyword_hits = [keyword for keyword in profile["keywords"] if keyword.lower() in text_blob]
    news_hits = [keyword for keyword in profile["keywords"] if keyword.lower() in news_text]
    disclosure_hits = [keyword for keyword in profile["keywords"] if keyword.lower() in disclosure_text]

    evidence_count = len(best_hits)
    reference = equity.avg_trading_value_20d or equity.avg_trading_value_60d or 0.0
    market_cap = equity.market_cap or 0.0
    quality_ok = equity.business_quality_score >= 3.8
    liquidity_ok = reference >= 3_000_000_000
    scale_ok = market_cap >= 100_000_000_000
    external_confirmation = any(item.startswith(("뉴스 확인", "공시 확인")) for item in best_evidence)
    tech_theme = best_theme in {
        "AI Infrastructure",
        "HBM",
        "Advanced Packaging",
        "PCB",
        "Optical Communication",
        "Data Center Cooling",
        "Industrial Automation",
    }
    weak_structural_fit = (
        tech_theme
        and not industry_hits
        and len(keyword_hits) <= 1
        and len(news_hits) + len(disclosure_hits) <= 1
    )

    gate_pass = (
        best_score >= profile["min_score"]
        and evidence_count >= 2
        and (external_confirmation or evidence_count >= 3)
        and liquidity_ok
        and scale_ok
        and quality_ok
        and not weak_structural_fit
    )
    if best_theme in {"K-Beauty", "Shipbuilding", "Defense", "Power Equipment"} and best_score >= 6.0:
        gate_pass = gate_pass or (liquidity_ok and scale_ok and quality_ok and evidence_count >= 2)

    if gate_pass:
        equity.theme = best_theme
        equity.sub_theme = second_theme
        equity.theme_score = best_score
        equity.theme_gate_pass = True
        equity.theme_confidence = "높음" if best_score >= 8.5 and evidence_count >= 3 else "중간"
        equity.theme_evidence = best_evidence[:4]
    else:
        equity.theme = "미분류"
        equity.sub_theme = ""
        equity.theme_score = best_score
        equity.theme_gate_pass = False
        equity.theme_confidence = "낮음"
        failure_reasons = []
        if not liquidity_ok:
            failure_reasons.append("거래대금 부족")
        if not scale_ok:
            failure_reasons.append("시가총액 부족")
        if not quality_ok:
            failure_reasons.append("사업체력 부족")
        if not external_confirmation and evidence_count < 3:
            failure_reasons.append("외부 확인 부족")
        equity.theme_evidence = best_evidence[:3] + [f"테마 보류: {', '.join(failure_reasons[:2]) or '근거 부족'}"]


def _scale_component(value: float | None, positive_scale: float, negative_scale: float) -> float:
    raw = value or 0.0
    if raw >= 0:
        return _clip((raw / positive_scale) * 100, 0.0, 100.0)
    return _clip((raw / negative_scale) * 100, -100.0, 0.0)


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _revision_components(equity: EquitySnapshot) -> list[tuple[float, float]]:
    metric_weights = {
        "eps": 1.0,
        "net_income": 0.75,
        "op_income": 0.55,
    }
    horizon_weights = {
        "3m": 1.0,
        "6m": 0.75,
        "12m": 0.55,
    }
    components: list[tuple[float, float]] = []
    for metric, metric_weight in metric_weights.items():
        for horizon, horizon_weight in horizon_weights.items():
            value = getattr(equity, f"{metric}_revision_{horizon}_pct", None)
            if value is None:
                continue
            components.append((_revision_band_score(value), metric_weight * horizon_weight))
    return components


def _revision_band_score(change_pct: float) -> float:
    if change_pct >= 20:
        return 10.0
    if change_pct >= 10:
        return 7.0
    if change_pct >= 5:
        return 5.0
    if change_pct <= -20:
        return -10.0
    if change_pct <= -10:
        return -8.0
    if change_pct <= -5:
        return -5.0
    return 0.0
