import type { PortfolioPosition } from "@/lib/portfolio-dashboard";

export type PortfolioScreeningRecord = {
  ticker: string;
  name: string;
  market: string;
  sector: string;
  sizeBucket: string;
  per: number | null;
  pbr: number | null;
  dividendYieldTrailing: number | null;
  returns6mPct: number | null;
  finalScore: number | null;
  valueScore: number | null;
  valuationScore: number | null;
  dividendPotentialScore: number | null;
  businessQualityScore: number | null;
  liquiditySupportScore: number | null;
  valueTrapRiskScore: number | null;
  recommendationBucket: string;
  coreBucket: string;
  leaderBucket: string;
  recommendationReasons: string;
  stage: string;
  tags: string[];
};

export function buildScreeningLookup(records: PortfolioScreeningRecord[]) {
  const byTicker = new Map<string, PortfolioScreeningRecord>();
  const byName = new Map<string, PortfolioScreeningRecord>();

  for (const record of records) {
    if (record.ticker) {
      byTicker.set(record.ticker, record);
    }
    if (record.name) {
      byName.set(record.name, record);
    }
  }

  return { byTicker, byName };
}

export function matchScreeningRecord(
  row: PortfolioPosition,
  lookup: ReturnType<typeof buildScreeningLookup>,
) {
  return lookup.byTicker.get(row.ticker) ?? lookup.byName.get(row.name) ?? null;
}
