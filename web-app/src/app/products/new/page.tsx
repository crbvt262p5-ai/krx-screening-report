import { ManualProductForm } from "@/components/manual-product-form";

export const dynamic = "force-dynamic";

type ManualProductPageProps = {
  searchParams?: Promise<{
    dogId?: string;
  }>;
};

export default async function ManualProductPage({
  searchParams,
}: ManualProductPageProps) {
  const params = await searchParams;

  return <ManualProductForm initialDogId={params?.dogId} />;
}
