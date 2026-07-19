import type { PortfolioPosition } from "@/lib/portfolio-dashboard";

type ValuationOverride = {
  per: number;
  pbr: number;
  eps: number;
  forwardPer: number;
};

const OVERSEAS_VALUATION_OVERRIDES: Record<string, ValuationOverride> = {
  NVDA: { per: 31.06, pbr: 25.13, eps: 6.53, forwardPer: 20.34 },
  AAPL: { per: 39.7, pbr: 45.11, eps: 8.25, forwardPer: 35.89 },
  META: { per: 21.94, pbr: 6.28, eps: 27.49, forwardPer: 18.37 },
  GOOGL: { per: 27.43, pbr: 9.1, eps: 13.11, forwardPer: 28.41 },
  TSM: { per: 26.3, pbr: 9.0, eps: 13.44, forwardPer: 18.55 },
  SIRI: { per: 12.92, pbr: 0.87, eps: 2.35, forwardPer: 9.53 },
  C: { per: 14.06, pbr: 1.13, eps: 9.2, forwardPer: 11.24 },
  NKE: { per: 20.37, pbr: 4.27, eps: 2.1, forwardPer: 25.04 },
  "스미토모": { per: 12.14, pbr: 1.52, eps: 124.67, forwardPer: 11.19 },
  "스미토모상사": { per: 12.14, pbr: 1.52, eps: 124.67, forwardPer: 11.19 },
  "도쿄카이죠홀딩스": { per: 27.84, pbr: 1.79, eps: 279.15, forwardPer: 16.08 },
};

function buildOverrideKeys(row: Pick<PortfolioPosition, "ticker" | "name">) {
  return [row.ticker.trim().toUpperCase(), row.ticker.trim(), row.name.trim().toUpperCase(), row.name.trim()].filter(Boolean);
}

export function getValuationOverride(row: Pick<PortfolioPosition, "ticker" | "name">) {
  for (const key of buildOverrideKeys(row)) {
    const match = OVERSEAS_VALUATION_OVERRIDES[key];
    if (match) {
      return match;
    }
  }
  return null;
}

export function withValuationOverride(row: PortfolioPosition): PortfolioPosition {
  const override = getValuationOverride(row);
  if (!override) {
    return row;
  }

  return {
    ...row,
    per: row.per ?? override.per,
    pbr: row.pbr ?? override.pbr,
    eps: row.eps ?? override.eps,
    forwardPer: row.forwardPer ?? override.forwardPer,
  };
}
