import { readFile } from "node:fs/promises";
import path from "node:path";
import { isVercelRuntime } from "@/lib/env";
import { normalizePortfolioRecords, type PortfolioPosition } from "@/lib/portfolio-dashboard";
import { enrichPortfolioRows } from "@/lib/portfolio-enrichment";
import { getPortfolioPositions } from "@/lib/repositories/portfolio";
import { portfolioSeedRecords } from "@/lib/portfolio-seed";

function resolvePortfolioPaths() {
  return [
    path.resolve(process.cwd(), "data", "portfolio_positions.csv"),
    path.resolve(process.cwd(), "..", "data", "portfolio_positions.csv"),
  ];
}

function needsValuationHydration(rows: PortfolioPosition[]) {
  return rows.some(
    (row) =>
      row.assetClass !== "ETF" &&
      (row.per === null || row.pbr === null || row.eps === null || row.forwardPer === null),
  );
}

async function hydrateValuationRows(rows: PortfolioPosition[]) {
  if (!needsValuationHydration(rows)) {
    return rows;
  }

  try {
    const result = await enrichPortfolioRows(rows);
    return result.rows;
  } catch {
    return rows;
  }
}

export async function loadDefaultPortfolioRows(): Promise<PortfolioPosition[]> {
  const portfolioRows = await getPortfolioPositions();
  if (portfolioRows.length > 0) {
    return hydrateValuationRows(portfolioRows);
  }

  if (isVercelRuntime()) {
    return hydrateValuationRows(normalizePortfolioRecords([...portfolioSeedRecords]));
  }

  for (const filePath of resolvePortfolioPaths()) {
    try {
      const { read, utils } = await import("xlsx");
      const buffer = await readFile(filePath);
      const workbook = read(buffer, { type: "buffer" });
      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      const records = utils.sheet_to_json<Record<string, unknown>>(sheet, {
        defval: "",
        raw: false,
      });

      return hydrateValuationRows(normalizePortfolioRecords(records));
    } catch {
      continue;
    }
  }

  return hydrateValuationRows(normalizePortfolioRecords([...portfolioSeedRecords]));
}
