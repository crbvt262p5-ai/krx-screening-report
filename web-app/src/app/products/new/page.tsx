import { ManualProductForm } from "@/components/manual-product-form";

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
