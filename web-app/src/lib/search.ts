import { products as mockProducts } from "@/lib/mock-data";
import { searchStoredProducts } from "@/lib/repositories/products";
import { Product, ProductKind } from "@/lib/types";

const SEARCH_ENDPOINT = "https://world.openfoodfacts.org/cgi/search.pl";
const USER_AGENT = "DogFoodApp/0.1 (local-prototype@example.com)";

function normalizeText(value: string) {
  return value.toLowerCase().trim();
}

function matchesKind(product: Product, kind: ProductKind) {
  return product.kind === kind;
}

export async function searchLocalProducts(query: string, kind: ProductKind) {
  const normalized = normalizeText(query);
  if (!normalized) {
    return [];
  }

  const storedProducts = await searchStoredProducts(query, kind);
  const fallbackProducts = mockProducts
    .filter((product) => matchesKind(product, kind))
    .filter((product) => {
      const searchable = [product.name, product.brand, ...product.aliases]
        .join(" ")
        .toLowerCase();
      return searchable.includes(normalized);
    });

  const merged = [...storedProducts, ...fallbackProducts];

  return merged.filter(
    (product, index, array) =>
      array.findIndex(
        (candidate) => candidate.name === product.name && candidate.brand === product.brand,
      ) === index,
  );
}

function buildExternalSearchQueries(query: string) {
  const normalized = normalizeText(query);
  if (!normalized) {
    return [];
  }

  const queries = [query];
  if (!/dog|pet|강아지|반려견|애견/.test(normalized)) {
    queries.push(`${query} dog`);
    queries.push(`${query} 강아지`);
  }

  return Array.from(new Set(queries));
}

type OpenFoodFactsProduct = {
  code?: string;
  product_name?: string;
  generic_name?: string;
  brands?: string;
  quantity?: string;
  categories?: string;
  image_url?: string;
  image_front_small_url?: string;
  nutriments?: {
    ["energy-kcal_100g"]?: number | string;
    ["energy-kcal"]?: number | string;
  };
};

function safeNumber(value: unknown) {
  if (typeof value === "number") {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  return undefined;
}

function parseQuantityToGrams(value?: string) {
  if (!value) {
    return undefined;
  }

  const normalized = value.toLowerCase().replace(",", ".").replace(/\s+/g, "");
  const multiMatch = normalized.match(/(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)(kg|g|mg)/);
  if (multiMatch) {
    const multiplier = Number(multiMatch[1]);
    const amount = Number(multiMatch[2]);
    const unit = multiMatch[3];
    const total = multiplier * amount;
    if (unit === "kg") {
      return total * 1000;
    }
    if (unit === "mg") {
      return total / 1000;
    }
    return total;
  }

  const singleMatch = normalized.match(/(\d+(?:\.\d+)?)(kg|g|mg)/);
  if (!singleMatch) {
    return undefined;
  }

  const amount = Number(singleMatch[1]);
  const unit = singleMatch[2];
  if (unit === "kg") {
    return amount * 1000;
  }
  if (unit === "mg") {
    return amount / 1000;
  }
  return amount;
}

function mapExternalProduct(product: OpenFoodFactsProduct, kind: ProductKind): Product {
  const totalWeightG = parseQuantityToGrams(product.quantity);
  const kcalPer100g =
    safeNumber(product.nutriments?.["energy-kcal_100g"]) ??
    safeNumber(product.nutriments?.["energy-kcal"]);

  return {
    id: product.code ?? crypto.randomUUID(),
    kind,
    sourceType: "open_pet_food_facts",
    name: product.product_name || product.generic_name || "이름 없는 제품",
    brand: product.brands || "-",
    aliases: [],
    totalWeightG,
    kcalPer100g,
    totalKcal:
      kcalPer100g && totalWeightG ? Math.round((kcalPer100g * totalWeightG) / 100) : undefined,
    verified: false,
  };
}

async function fetchExternalQuery(query: string, kind: ProductKind) {
  const params = new URLSearchParams({
    search_terms: query,
    search_simple: "1",
    action: "process",
    json: "1",
    page_size: "8",
    nocache: "1",
  });

  const response = await fetch(`${SEARCH_ENDPOINT}?${params.toString()}`, {
    headers: {
      "User-Agent": USER_AGENT,
    },
    next: { revalidate: 3600 },
  });

  if (!response.ok) {
    throw new Error("외부 제품 검색에 실패했습니다.");
  }

  const payload = (await response.json()) as { products?: OpenFoodFactsProduct[] };
  return (payload.products ?? []).map((product) => mapExternalProduct(product, kind));
}

export async function searchExternalProducts(query: string, kind: ProductKind) {
  const queries = buildExternalSearchQueries(query);
  const seen = new Set<string>();
  const results: Product[] = [];

  for (const searchQuery of queries) {
    const batch = await fetchExternalQuery(searchQuery, kind);

    for (const product of batch) {
      const key = `${product.name}-${product.brand}`;
      if (seen.has(key)) {
        continue;
      }

      seen.add(key);
      results.push(product);
    }
  }

  return results;
}
