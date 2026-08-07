import { readFile } from "node:fs/promises";
import path from "node:path";
import { isVercelRuntime } from "@/lib/env";
import { normalizePortfolioRecords, type PortfolioPosition } from "@/lib/portfolio-dashboard";
import { enrichPortfolioRows } from "@/lib/portfolio-enrichment";
import { withValuationOverride } from "@/lib/portfolio-valuation-overrides";
import { getPortfolioPositions } from "@/lib/repositories/portfolio";
import { portfolioSeedRecords } from "@/lib/portfolio-seed";

function resolvePortfolioDirectories() {
  return [
    path.resolve(process.cwd(), "data"),
    path.resolve(process.cwd(), "..", "data"),
  ];
}

async function readPortfolioCsv(filePath: string) {
  const { read, utils } = await import("xlsx");
  const buffer = await readFile(filePath);
  const workbook = read(buffer, { type: "buffer" });
  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  return utils.sheet_to_json<Record<string, unknown>>(sheet, {
    defval: "",
    raw: false,
  });
}

function needsValuationHydration(rows: PortfolioPosition[]) {
  return rows.some(
    (row) =>
      row.assetClass !== "ETF" &&
      (row.per === null || row.pbr === null || row.eps === null || row.forwardPer === null),
  );
}

async function hydrateValuationRows(rows: PortfolioPosition[]) {
  const retirementRows = rows.filter((row) => row.accountSection === "dc");
  const rowsWithOverrides = rows
    .filter((row) => row.accountSection !== "dc")
    .map(withValuationOverride);

  if (!needsValuationHydration(rowsWithOverrides)) {
    return [...rowsWithOverrides, ...retirementRows];
  }

  try {
    const result = await enrichPortfolioRows(rowsWithOverrides);
    return [...result.rows.map(withValuationOverride), ...retirementRows];
  } catch {
    return [...rowsWithOverrides, ...retirementRows];
  }
}

export async function loadDefaultPortfolioRows(): Promise<PortfolioPosition[]> {
  const portfolioRows = await getPortfolioPositions();
  if (portfolioRows.length > 0) {
    return hydrateValuationRows(portfolioRows);
  }

  for (const directory of resolvePortfolioDirectories()) {
    try {
      const records = await readPortfolioCsv(path.join(directory, "portfolio_positions.csv"));
      try {
        records.push(...(await readPortfolioCsv(path.join(directory, "dc_positions.csv"))));
      } catch {
        // The DC file is optional until a retirement account has been added.
      }

      return hydrateValuationRows(normalizePortfolioRecords(records));
    } catch {
      continue;
    }
  }

  if (isVercelRuntime()) {
    return hydrateValuationRows(normalizePortfolioRecords([...portfolioSeedRecords]));
  }

  return hydrateValuationRows(normalizePortfolioRecords([...portfolioSeedRecords]));
}
