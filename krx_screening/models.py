from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EquitySnapshot:
    ticker: str
    market: str
    name: str
    close: float | None = None
    market_cap: float | None = None
    per: float | None = None
    pbr: float | None = None
    dividend_yield: float | None = None
    returns_1m: float | None = None
    returns_3m: float | None = None
    returns_6m: float | None = None
    returns_12m: float | None = None
    high_52w_ratio: float | None = None
    sales_3y: list[float | None] = field(default_factory=list)
    op_income_3y: list[float | None] = field(default_factory=list)
    net_income_3y: list[float | None] = field(default_factory=list)
    dividends_3y: list[float | None] = field(default_factory=list)
    op_income_volatility: float | None = None
    debt_ratio: float | None = None
    cash_assets: float | None = None
    net_cash: float | None = None
    fcf: float | None = None
    payout_ratio: float | None = None
    forecast_growth_next_year: float | None = None
    news_keyword_hits: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)
    excluded: bool = False
    exclusion_reasons: list[str] = field(default_factory=list)
    pass_reasons: list[str] = field(default_factory=list)
    value_score: float = 0.0
    growth_early_score: float = 0.0
    dividend_potential_score: float = 0.0
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
            "prev_close": self.close,
            "market_cap": self.market_cap,
            "per": self.per,
            "pbr": self.pbr,
            "dividend_yield": self.dividend_yield,
            "returns_1m_pct": self.returns_1m,
            "returns_3m_pct": self.returns_3m,
            "returns_6m_pct": self.returns_6m,
            "returns_12m_pct": self.returns_12m,
            "high_52w_ratio_pct": self.high_52w_ratio,
            "sales_3y": "|".join(_format_num(v) for v in self.sales_3y),
            "op_income_3y": "|".join(_format_num(v) for v in self.op_income_3y),
            "net_income_3y": "|".join(_format_num(v) for v in self.net_income_3y),
            "dividends_3y": "|".join(_format_num(v) for v in self.dividends_3y),
            "op_income_volatility_pct": self.op_income_volatility,
            "debt_ratio_pct": self.debt_ratio,
            "cash_assets": self.cash_assets,
            "net_cash": self.net_cash,
            "fcf": self.fcf,
            "payout_ratio_pct": self.payout_ratio,
            "forecast_growth_next_year_pct": self.forecast_growth_next_year,
            "news_keyword_hits": "|".join(self.news_keyword_hits),
            "value_score": self.value_score,
            "growth_early_score": self.growth_early_score,
            "dividend_potential_score": self.dividend_potential_score,
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
