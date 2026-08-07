import type { PortfolioPosition } from "@/lib/portfolio-dashboard";

export type RetirementPositionMetrics = {
  evaluation: number;
  purchase: number;
  profit: number;
  returnPct: number;
  quantity: string | null;
  averagePrice: number | null;
};

function readMetric(notes: string, label: string) {
  const match = notes.match(new RegExp(`${label}\\s*(-?[0-9,.]+)원`));
  if (!match) return null;
  const value = Number(match[1].replaceAll(",", ""));
  return Number.isFinite(value) ? value : null;
}

export function parseRetirementMetrics(row: PortfolioPosition): RetirementPositionMetrics {
  const evaluation = readMetric(row.notes, "평가") ?? 0;
  const purchase = readMetric(row.notes, "매입") ?? evaluation;
  const profit = readMetric(row.notes, "손익") ?? evaluation - purchase;
  const savedReturn = row.notes.match(/수익률\s*(-?[0-9,.]+)%/);
  const quantity = row.notes.match(/수량\s*([0-9,.]+)(?:주)?/)?.[1] ?? null;

  return {
    evaluation,
    purchase,
    profit,
    returnPct: savedReturn ? Number(savedReturn[1].replaceAll(",", "")) : purchase > 0 ? profit / purchase * 100 : 0,
    quantity,
    averagePrice: readMetric(row.notes, "평균매입가"),
  };
}

export function buildRetirementSnapshot(rows: PortfolioPosition[]) {
  const positions = rows.map((row) => ({ row, metrics: parseRetirementMetrics(row) }));
  const totalEvaluation = positions.reduce((sum, item) => sum + item.metrics.evaluation, 0);
  const totalPurchase = positions.reduce((sum, item) => sum + item.metrics.purchase, 0);
  const totalProfit = totalEvaluation - totalPurchase;
  const safeAssetClasses = new Set(["예금", "MMF", "현금"]);
  const safeAssets = positions
    .filter((item) => safeAssetClasses.has(item.row.assetClass))
    .reduce((sum, item) => sum + item.metrics.evaluation, 0);
  const etfAssets = positions
    .filter((item) => item.row.assetClass === "ETF")
    .reduce((sum, item) => sum + item.metrics.evaluation, 0);
  const cash = positions
    .filter((item) => item.row.assetClass === "현금")
    .reduce((sum, item) => sum + item.metrics.evaluation, 0);
  const losses = positions
    .filter((item) => item.metrics.profit < 0)
    .sort((left, right) => left.metrics.profit - right.metrics.profit);

  return {
    positions,
    totalEvaluation,
    totalPurchase,
    totalProfit,
    totalReturnPct: totalPurchase > 0 ? totalProfit / totalPurchase * 100 : 0,
    safeAssets,
    safeAssetPct: totalEvaluation > 0 ? safeAssets / totalEvaluation * 100 : 0,
    etfAssets,
    etfPct: totalEvaluation > 0 ? etfAssets / totalEvaluation * 100 : 0,
    cash,
    cashPct: totalEvaluation > 0 ? cash / totalEvaluation * 100 : 0,
    largestLoss: losses[0] ?? null,
    largestLossContributionPct:
      losses[0] && totalProfit < 0 ? Math.abs(losses[0].metrics.profit / totalProfit) * 100 : 0,
  };
}
