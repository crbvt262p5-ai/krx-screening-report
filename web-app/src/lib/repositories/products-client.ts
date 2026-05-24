"use client";

import { hasSupabaseEnv } from "@/lib/env";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { Product, ProductKind } from "@/lib/types";
import { mapProductRow, ProductRow, toProductRow } from "@/lib/repositories/mappers";

const PRODUCT_STORAGE_KEY = "dog-food-app.products.manual";

function saveManualProducts(products: Product[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(PRODUCT_STORAGE_KEY, JSON.stringify(products));
}

export function hydrateManualProductsFromStorage() {
  if (typeof window === "undefined" || hasSupabaseEnv()) {
    return [] as Product[];
  }

  try {
    const raw = window.localStorage.getItem(PRODUCT_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw) as Product[];
    return parsed;
  } catch {
    return [];
  }
}

export function searchManualProducts(query: string, kind: ProductKind) {
  const normalized = query.toLowerCase().trim();
  if (!normalized) {
    return [];
  }

  return hydrateManualProductsFromStorage().filter((product) => {
    if (product.kind !== kind) {
      return false;
    }

    const searchable = [product.name, product.brand, ...product.aliases].join(" ").toLowerCase();
    return searchable.includes(normalized);
  });
}

export async function createManualProduct(product: Product) {
  if (!hasSupabaseEnv()) {
    const current = hydrateManualProductsFromStorage();
    const next = [product, ...current.filter((item) => item.id !== product.id)];
    saveManualProducts(next);
    return product;
  }

  const supabase = getSupabaseBrowserClient();
  if (!supabase) {
    return product;
  }

  const productsTable = supabase.from("products" as never) as unknown as {
    upsert: (
      values: ProductRow,
      options: { onConflict: string },
    ) => {
      select: (query: string) => {
        single: () => Promise<{ data: ProductRow | null; error: Error | null }>;
      };
    };
  };

  const { data, error } = await productsTable
    .upsert(toProductRow(product), { onConflict: "id" })
    .select(
      "id, kind, source_type, name, brand, total_weight_g, kcal_per_100g, total_kcal, pieces_per_pack, kcal_per_piece, verified",
    )
    .single();

  if (error || !data) {
    throw new Error("수동 제품 등록에 실패했습니다.");
  }

  return mapProductRow(data);
}
