import { PortfolioDashboard } from "@/components/portfolio-dashboard";
import { loadDefaultPortfolioRows } from "@/lib/portfolio-data";
import { loadLatestScreeningRecords } from "@/lib/portfolio-screening";

export const dynamic = "force-dynamic";

export default async function PortfolioPage() {
  const [initialRows, screeningRecords] = await Promise.all([
    loadDefaultPortfolioRows(),
    loadLatestScreeningRecords(),
  ]);

  return <PortfolioDashboard initialRows={initialRows} screeningRecords={screeningRecords} />;
}
