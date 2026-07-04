from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EquitySnapshot:
    ticker: str
    market: str
    name: str
    sector: str | None = None
    industry: str | None = None
    size_bucket: str | None = None
    close: float | None = None
    market_cap: float | None = None
    per: float | None = None
    pbr: float | None = None
    dividend_yield: float | None = None
    dividend_yield_trailing: float | None = None
    dividend_yield_normalized: float | None = None
    dividend_yield_source: str | None = None
    returns_1m: float | None = None
    returns_3m: float | None = None
    returns_6m: float | None = None
    returns_12m: float | None = None
    high_52w_ratio: float | None = None
    avg_trading_value_20d: float | None = None
    avg_trading_value_60d: float | None = None
    foreign_net_buy_3m: float | None = None
    pension_net_buy_3m: float | None = None
    etf_holding_change_3m: float | None = None
    foreign_net_buy_ratio_3m: float | None = None
    pension_net_buy_ratio_3m: float | None = None
    net_buy_ratio_3m: float | None = None
    sales_3y: list[float | None] = field(default_factory=list)
    op_income_3y: list[float | None] = field(default_factory=list)
    net_income_3y: list[float | None] = field(default_factory=list)
    dividends_3y: list[float | None] = field(default_factory=list)
    op_income_volatility: float | None = None
    debt_ratio: float | None = None
    total_equity: float | None = None
    total_debt: float | None = None
    ebitda: float | None = None
    cash_assets: float | None = None
    net_cash: float | None = None
    fcf: float | None = None
    fcf_yield: float | None = None
    ev_ebitda: float | None = None
    peg: float | None = None
    industry_avg_per: float | None = None
    industry_per_discount_pct: float | None = None
    roe: float | None = None
    roic: float | None = None
    payout_ratio: float | None = None
    dividend_growth_rate: float | None = None
    dividend_cut_flag: bool = False
    special_dividend_adjusted: bool = False
    treasury_stock_ratio: float | None = None
    treasury_burn_recent: bool = False
    payout_increase_flag: bool = False
    dividend_tax_benefit_score: float = 0.0
    tax_exemption_benefit_score: float = 0.0
    governance_reform_score: float = 0.0
    commercial_code_benefit_score: float = 0.0
    forecast_growth_next_year: float | None = None
    consensus_op_income_estimate: float | None = None
    consensus_net_income_estimate: float | None = None
    consensus_eps_estimate: float | None = None
    op_income_revision_3m_pct: float | None = None
    op_income_revision_6m_pct: float | None = None
    op_income_revision_12m_pct: float | None = None
    net_income_revision_3m_pct: float | None = None
    net_income_revision_6m_pct: float | None = None
    net_income_revision_12m_pct: float | None = None
    eps_revision_3m_pct: float | None = None
    eps_revision_6m_pct: float | None = None
    eps_revision_12m_pct: float | None = None
    news_keyword_hits: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)
    excluded: bool = False
    exclusion_reasons: list[str] = field(default_factory=list)
    pass_reasons: list[str] = field(default_factory=list)
    value_score: float = 0.0
    growth_early_score: float = 0.0
    dividend_potential_score: float = 0.0
    valuation_score: float = 0.0
    business_quality_score: float = 0.0
    liquidity_support_score: float = 0.0
    value_trap_risk_score: float = 0.0
    estimate_revision_score: float = 0.0
    tam_expansion_score: float = 0.0
    flow_momentum_score: float = 0.0
    shareholder_return_score: float = 0.0
    ownership_flow_score: float = 0.0
    policy_score: float = 0.0
    payout_repeatability_score: float = 0.0
    cashflow_quality_score: float = 0.0
    governance_warning_score: float = 0.0
    investability_score: float = 0.0
    missed_leader_score: float = 0.0
    final_score: float = 0.0
    recommendation_bucket: str = "보류"
    core_bucket: str | None = None
    recommendation_reasons: list[str] = field(default_factory=list)
    value_style: str | None = None
    growth_style: str | None = None
    stage: str = "초입"
    tags: list[str] = field(default_factory=list)

    def mark_missing(self, *fields: str) -> None:
        for field_name in fields:
            if field_name not in self.missing_data:
                self.missing_data.append(field_name)

    def clear_missing(self, *fields: str) -> None:
        self.missing_data = [field for field in self.missing_data if field not in fields]

    def to_record(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "market": self.market,
            "name": self.name,
            "sector": self.sector,
            "industry": self.industry,
            "size_bucket": self.size_bucket,
            "prev_close": self.close,
            "market_cap": self.market_cap,
            "per": self.per,
            "pbr": self.pbr,
            "dividend_yield": self.dividend_yield,
            "dividend_yield_trailing": self.dividend_yield_trailing,
            "dividend_yield_normalized": self.dividend_yield_normalized,
            "dividend_yield_source": self.dividend_yield_source,
            "returns_1m_pct": self.returns_1m,
            "returns_3m_pct": self.returns_3m,
            "returns_6m_pct": self.returns_6m,
            "returns_12m_pct": self.returns_12m,
            "high_52w_ratio_pct": self.high_52w_ratio,
            "avg_trading_value_20d": self.avg_trading_value_20d,
            "avg_trading_value_60d": self.avg_trading_value_60d,
            "foreign_net_buy_3m": self.foreign_net_buy_3m,
            "pension_net_buy_3m": self.pension_net_buy_3m,
            "etf_holding_change_3m": self.etf_holding_change_3m,
            "foreign_net_buy_ratio_3m": self.foreign_net_buy_ratio_3m,
            "pension_net_buy_ratio_3m": self.pension_net_buy_ratio_3m,
            "net_buy_ratio_3m": self.net_buy_ratio_3m,
            "sales_3y": "|".join(_format_num(v) for v in self.sales_3y),
            "op_income_3y": "|".join(_format_num(v) for v in self.op_income_3y),
            "net_income_3y": "|".join(_format_num(v) for v in self.net_income_3y),
            "dividends_3y": "|".join(_format_num(v) for v in self.dividends_3y),
            "op_income_volatility_pct": self.op_income_volatility,
            "debt_ratio_pct": self.debt_ratio,
            "total_equity": self.total_equity,
            "total_debt": self.total_debt,
            "ebitda": self.ebitda,
            "cash_assets": self.cash_assets,
            "net_cash": self.net_cash,
            "fcf": self.fcf,
            "fcf_yield_pct": self.fcf_yield,
            "ev_ebitda": self.ev_ebitda,
            "peg": self.peg,
            "industry_avg_per": self.industry_avg_per,
            "industry_per_discount_pct": self.industry_per_discount_pct,
            "roe_pct": self.roe,
            "roic_pct": self.roic,
            "payout_ratio_pct": self.payout_ratio,
            "dividend_growth_rate_pct": self.dividend_growth_rate,
            "dividend_cut_flag": self.dividend_cut_flag,
            "special_dividend_adjusted": self.special_dividend_adjusted,
            "treasury_stock_ratio_pct": self.treasury_stock_ratio,
            "treasury_burn_recent": self.treasury_burn_recent,
            "payout_increase_flag": self.payout_increase_flag,
            "dividend_tax_benefit_score": self.dividend_tax_benefit_score,
            "tax_exemption_benefit_score": self.tax_exemption_benefit_score,
            "governance_reform_score": self.governance_reform_score,
            "commercial_code_benefit_score": self.commercial_code_benefit_score,
            "forecast_growth_next_year_pct": self.forecast_growth_next_year,
            "consensus_op_income_estimate": self.consensus_op_income_estimate,
            "consensus_net_income_estimate": self.consensus_net_income_estimate,
            "consensus_eps_estimate": self.consensus_eps_estimate,
            "op_income_revision_3m_pct": self.op_income_revision_3m_pct,
            "op_income_revision_6m_pct": self.op_income_revision_6m_pct,
            "op_income_revision_12m_pct": self.op_income_revision_12m_pct,
            "net_income_revision_3m_pct": self.net_income_revision_3m_pct,
            "net_income_revision_6m_pct": self.net_income_revision_6m_pct,
            "net_income_revision_12m_pct": self.net_income_revision_12m_pct,
            "eps_revision_3m_pct": self.eps_revision_3m_pct,
            "eps_revision_6m_pct": self.eps_revision_6m_pct,
            "eps_revision_12m_pct": self.eps_revision_12m_pct,
            "news_keyword_hits": "|".join(self.news_keyword_hits),
            "value_score": self.value_score,
            "growth_early_score": self.growth_early_score,
            "dividend_potential_score": self.dividend_potential_score,
            "valuation_score": self.valuation_score,
            "business_quality_score": self.business_quality_score,
            "liquidity_support_score": self.liquidity_support_score,
            "value_trap_risk_score": self.value_trap_risk_score,
            "estimate_revision_score": self.estimate_revision_score,
            "tam_expansion_score": self.tam_expansion_score,
            "flow_momentum_score": self.flow_momentum_score,
            "shareholder_return_score": self.shareholder_return_score,
            "ownership_flow_score": self.ownership_flow_score,
            "policy_score": self.policy_score,
            "payout_repeatability_score": self.payout_repeatability_score,
            "cashflow_quality_score": self.cashflow_quality_score,
            "governance_warning_score": self.governance_warning_score,
            "investability_score": self.investability_score,
            "missed_leader_score": self.missed_leader_score,
            "final_score": self.final_score,
            "recommendation_bucket": self.recommendation_bucket,
            "core_bucket": self.core_bucket,
            "recommendation_reasons": " | ".join(self.recommendation_reasons),
            "value_style": self.value_style,
            "growth_style": self.growth_style,
            "excluded": self.excluded,
            "reasons": " / ".join(self.exclusion_reasons or self.pass_reasons),
            "stage": self.stage,
            "tags": "|".join(self.tags),
            "missing_data": "|".join(self.missing_data),
            "source_notes": "|".join(self.source_notes),
        }


def _format_num(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"
