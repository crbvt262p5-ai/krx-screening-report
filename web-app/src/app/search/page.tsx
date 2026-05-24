import { SearchPanel } from "@/components/search-panel";

type SearchPageProps = {
  searchParams?: Promise<{
    dogId?: string;
    q?: string;
    kind?: "food" | "treat";
  }>;
};

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;

  return (
    <SearchPanel
      initialDogId={params?.dogId}
      initialQuery={params?.q}
      initialKind={params?.kind}
    />
  );
}
