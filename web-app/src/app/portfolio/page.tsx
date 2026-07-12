import { PortfolioDashboard } from "@/components/portfolio-dashboard";
import { loadDefaultPortfolioRows } from "@/lib/portfolio-data";

export const dynamic = "force-dynamic";

export default async function PortfolioPage() {
  const initialRows = await loadDefaultPortfolioRows();

  return <PortfolioDashboard initialRows={initialRows} />;
}
