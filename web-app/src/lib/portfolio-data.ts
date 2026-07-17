import { readFile } from "node:fs/promises";
import path from "node:path";
import { isVercelRuntime } from "@/lib/env";
import { normalizePortfolioRecords, type PortfolioPosition } from "@/lib/portfolio-dashboard";
import { getPortfolioPositions } from "@/lib/repositories/portfolio";
import { portfolioSeedRecords } from "@/lib/portfolio-seed";

function resolvePortfolioPaths() {
  return [
    path.resolve(process.cwd(), "data", "portfolio_positions.csv"),
    path.resolve(process.cwd(), "..", "data", "portfolio_positions.csv"),
  ];
}

export async function loadDefaultPortfolioRows(): Promise<PortfolioPosition[]> {
  const portfolioRows = await getPortfolioPositions();
  if (portfolioRows.length > 0) {
    return portfolioRows;
  }

  if (isVercelRuntime()) {
    return normalizePortfolioRecords([...portfolioSeedRecords]);
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

      return normalizePortfolioRecords(records);
    } catch {
      continue;
    }
  }

  return normalizePortfolioRecords([...portfolioSeedRecords]);
}
