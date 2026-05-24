import { products as mockProducts } from "@/lib/mock-data";
import { Product, ProductKind } from "@/lib/types";
import { hasSupabaseEnv } from "@/lib/env";
import { getSupabaseServerClient } from "@/lib/supabase";
import { mapProductRow, ProductRow } from "@/lib/repositories/mappers";

function rankLocalProduct(product: Product, normalizedQuery: string) {
  const searchable = [product.name, product.brand, ...product.aliases].join(" ").toLowerCase();
  const exactNameBonus = product.name.toLowerCase() === normalizedQuery ? 5 : 0;
  const verifiedBonus = product.verified ? 2 : 0;
  const includesScore = searchable.includes(normalizedQuery) ? 3 : 0;
  return exactNameBonus + verifiedBonus + includesScore;
}

export async function getFeaturedProducts(): Promise<Product[]> {
  if (!hasSupabaseEnv()) {
    return mockProducts.filter((product) => product.verified).slice(0, 3);
  }

  const supabase = getSupabaseServerClient();
  if (!supabase) {
    return mockProducts.filter((product) => product.verified).slice(0, 3);
  }

  const { data, error } = await supabase
    .from("products")
    .select(
      "id, kind, source_type, name, brand, total_weight_g, kcal_per_100g, total_kcal, pieces_per_pack, kcal_per_piece, verified",
    )
    .eq("verified", true)
    .limit(3);

  if (error || !data) {
    return mockProducts.filter((product) => product.verified).slice(0, 3);
  }

  return (data as ProductRow[]).map(mapProductRow);
}

export async function searchStoredProducts(query: string, kind: ProductKind): Promise<Product[]> {
  const normalized = query.toLowerCase().trim();
  if (!normalized) {
    return [];
  }

  if (!hasSupabaseEnv()) {
    return mockProducts
      .filter((product) => product.kind === kind)
      .filter((product) =>
        [product.name, product.brand, ...product.aliases].join(" ").toLowerCase().includes(normalized),
      )
      .sort((left, right) => rankLocalProduct(right, normalized) - rankLocalProduct(left, normalized));
  }

  const supabase = getSupabaseServerClient();
  if (!supabase) {
    return [];
  }

  const { data, error } = await supabase
    .from("products")
    .select(
      "id, kind, source_type, name, brand, total_weight_g, kcal_per_100g, total_kcal, pieces_per_pack, kcal_per_piece, verified",
    )
    .eq("kind", kind)
    .or(`name.ilike.%${normalized}%,brand.ilike.%${normalized}%`)
    .limit(12);

  if (error || !data) {
    return [];
  }

  return (data as ProductRow[])
    .map(mapProductRow)
    .sort((left, right) => rankLocalProduct(right, normalized) - rankLocalProduct(left, normalized));
}
