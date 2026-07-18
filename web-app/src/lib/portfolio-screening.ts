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

function mapScreeningRecord(record: RawRecord): PortfolioScreeningRecord {
  return {
    ticker: toCellString(record.ticker),
    name: toCellString(record.name),
    market: toCellString(record.market),
    sector: toCellString(record.sector),
    sizeBucket: toCellString(record.size_bucket),
    per: parseNullableNumber(record.per),
    pbr: parseNullableNumber(record.pbr),
    dividendYieldTrailing: parseNullableNumber(record.dividend_yield_trailing),
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
