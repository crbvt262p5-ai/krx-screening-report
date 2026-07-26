import { readFile } from "node:fs/promises";
import path from "node:path";
import type { PortfolioScreeningRecord } from "@/lib/portfolio-screening-shared";

type RawRecord = Record<string, unknown>;

function resolveScreeningPaths() {
  return [
    path.resolve(process.cwd(), "data", "latest.csv"),
    path.resolve(process.cwd(), "..", "data", "latest.csv"),
  ];
}

function toCellString(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).trim();
}

function parseNullableNumber(value: unknown) {
  const normalized = toCellString(value).replaceAll(",", "").replaceAll("%", "");
  if (!normalized || normalized.toLowerCase() === "nan") {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function roundMetric(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return null;
  }
  return Math.round(value * 100) / 100;
}

function parseBoolean(value: unknown) {
  const normalized = toCellString(value).toLowerCase();
  return ["true", "1", "yes", "y", "예"].includes(normalized);
}

function mapScreeningRecord(record: RawRecord): PortfolioScreeningRecord {
  const prevClose = parseNullableNumber(record.prev_close);
  const trailingPer = parseNullableNumber(record.per);
  const forecastGrowthNextYearPct = parseNullableNumber(record.forecast_growth_next_year_pct);
  const derivedTrailingEps =
    prevClose !== null && trailingPer !== null && trailingPer !== 0 ? prevClose / trailingPer : null;
  const consensusEpsEstimate = parseNullableNumber(record.consensus_eps_estimate);
  const derivedForwardEps =
    derivedTrailingEps !== null &&
    forecastGrowthNextYearPct !== null &&
    forecastGrowthNextYearPct > -80 &&
    forecastGrowthNextYearPct < 150
      ? derivedTrailingEps * (1 + forecastGrowthNextYearPct / 100)
      : null;
  const resolvedEpsEstimate = roundMetric(consensusEpsEstimate ?? derivedTrailingEps);
  const forwardPer =
    prevClose !== null &&
    (consensusEpsEstimate ?? derivedForwardEps ?? derivedTrailingEps) !== null &&
    (consensusEpsEstimate ?? derivedForwardEps ?? derivedTrailingEps) !== 0
      ? Math.round((prevClose / (consensusEpsEstimate ?? derivedForwardEps ?? derivedTrailingEps)!) * 100) / 100
      : null;

  return {
    ticker: toCellString(record.ticker),
    name: toCellString(record.name),
    market: toCellString(record.market),
    sector: toCellString(record.sector),
    sizeBucket: toCellString(record.size_bucket),
    prevClose: roundMetric(prevClose),
    per: trailingPer,
    pbr: parseNullableNumber(record.pbr),
    consensusEpsEstimate: resolvedEpsEstimate,
    forwardPer: roundMetric(forwardPer),
    dividendYieldTrailing: parseNullableNumber(record.dividend_yield_trailing),
    dividendYieldNormalized: parseNullableNumber(record.dividend_yield_normalized),
    payoutRatioPct: parseNullableNumber(record.payout_ratio_pct),
    dividendGrowthRatePct: parseNullableNumber(record.dividend_growth_rate_pct),
    treasuryStockRatioPct: parseNullableNumber(record.treasury_stock_ratio_pct),
    treasuryBurnRecent: parseBoolean(record.treasury_burn_recent),
    payoutIncreaseFlag: parseBoolean(record.payout_increase_flag),
    shareholderReturnScore: parseNullableNumber(record.shareholder_return_score),
    payoutRepeatabilityScore: parseNullableNumber(record.payout_repeatability_score),
    cashflowQualityScore: parseNullableNumber(record.cashflow_quality_score),
    returns6mPct: parseNullableNumber(record.returns_6m_pct),
    finalScore: parseNullableNumber(record.final_score),
    valueScore: parseNullableNumber(record.value_score),
    valuationScore: parseNullableNumber(record.valuation_score),
    dividendPotentialScore: parseNullableNumber(record.dividend_potential_score),
    businessQualityScore: parseNullableNumber(record.business_quality_score),
    liquiditySupportScore: parseNullableNumber(record.liquidity_support_score),
    valueTrapRiskScore: parseNullableNumber(record.value_trap_risk_score),
    recommendationBucket: toCellString(record.recommendation_bucket),
    coreBucket: toCellString(record.core_bucket),
    leaderBucket: toCellString(record.leader_bucket),
    recommendationReasons: toCellString(record.recommendation_reasons),
    stage: toCellString(record.stage),
    tags: toCellString(record.tags)
      .split("|")
      .map((item) => item.trim())
      .filter(Boolean),
  };
}

export async function loadLatestScreeningRecords(): Promise<PortfolioScreeningRecord[]> {
  for (const filePath of resolveScreeningPaths()) {
    try {
      const { read, utils } = await import("xlsx");
      const buffer = await readFile(filePath);
      const workbook = read(buffer, { type: "buffer" });
      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      const records = utils.sheet_to_json<RawRecord>(sheet, { defval: "", raw: false });

      return records
        .map(mapScreeningRecord)
        .filter((row) => row.ticker && row.name);
    } catch {
      continue;
    }
  }

  return [];
}
