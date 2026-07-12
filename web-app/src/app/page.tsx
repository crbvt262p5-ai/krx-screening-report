import { HomeDashboard } from "@/components/home-dashboard";
import { getDogs } from "@/lib/repositories/dogs";
import { getFeedingLogs } from "@/lib/repositories/feeding-logs";
import { getFeaturedProducts } from "@/lib/repositories/products";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function Home() {
  const dogs = await getDogs();
  const featuredProducts = await getFeaturedProducts();
  const feedingLogs = await getFeedingLogs();

  return (
    <>
      <div className="mx-auto mt-4 flex w-full max-w-6xl justify-end px-4 sm:px-6 lg:px-8">
        <Link className="secondary-cta" href="/portfolio">
          포트 대시보드 열기
        </Link>
      </div>
      <HomeDashboard initialDogs={dogs} featuredProducts={featuredProducts} feedingLogs={feedingLogs} />
    </>
  );
}
