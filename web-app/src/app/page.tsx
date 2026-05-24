import { HomeDashboard } from "@/components/home-dashboard";
import { getDogs } from "@/lib/repositories/dogs";
import { getFeedingLogs } from "@/lib/repositories/feeding-logs";
import { getFeaturedProducts } from "@/lib/repositories/products";

export default async function Home() {
  const dogs = await getDogs();
  const featuredProducts = await getFeaturedProducts();
  const feedingLogs = await getFeedingLogs();

  return (
    <HomeDashboard initialDogs={dogs} featuredProducts={featuredProducts} feedingLogs={feedingLogs} />
  );
}
