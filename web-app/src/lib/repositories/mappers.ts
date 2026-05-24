import { DogProfile, FeedingLog, Product } from "@/lib/types";

export type DogRow = {
  id: string;
  name: string;
  weight_kg: number;
  age_group: "puppy" | "adult" | "senior";
  activity_factor: number;
  is_neutered: boolean;
  note?: string | null;
};

export type ProductRow = {
  id: string;
  kind: "food" | "treat";
  source_type: "manual" | "internal" | "open_pet_food_facts";
  name: string;
  brand: string;
  total_weight_g?: number | null;
  kcal_per_100g?: number | null;
  total_kcal?: number | null;
  pieces_per_pack?: number | null;
  kcal_per_piece?: number | null;
  verified: boolean;
};

export type FeedingLogRow = {
  id: string;
  dog_id: string;
  log_date: string;
  food_product_id?: string | null;
  treat_product_id?: string | null;
  food_grams: number;
  treat_pieces: number;
  food_kcal: number;
  treat_kcal: number;
  total_kcal: number;
  recommended_kcal: number;
  note?: string | null;
};

export function mapDogRow(row: DogRow): DogProfile {
  return {
    id: row.id,
    name: row.name,
    weightKg: Number(row.weight_kg),
    ageGroup: row.age_group,
    activityFactor: Number(row.activity_factor),
    isNeutered: row.is_neutered,
    note: row.note ?? undefined,
  };
}

export function toDogRow(profile: DogProfile): DogRow {
  return {
    id: profile.id,
    name: profile.name,
    weight_kg: profile.weightKg,
    age_group: profile.ageGroup,
    activity_factor: profile.activityFactor,
    is_neutered: profile.isNeutered,
    note: profile.note ?? null,
  };
}

export function mapProductRow(row: ProductRow): Product {
  return {
    id: row.id,
    kind: row.kind,
    sourceType: row.source_type,
    name: row.name,
    brand: row.brand,
    aliases: [],
    totalWeightG: row.total_weight_g ?? undefined,
    kcalPer100g: row.kcal_per_100g ?? undefined,
    totalKcal: row.total_kcal ?? undefined,
    piecesPerPack: row.pieces_per_pack ?? undefined,
    kcalPerPiece: row.kcal_per_piece ?? undefined,
    verified: row.verified,
  };
}

export function toProductRow(product: Product): ProductRow {
  return {
    id: product.id,
    kind: product.kind,
    source_type: product.sourceType,
    name: product.name,
    brand: product.brand,
    total_weight_g: product.totalWeightG ?? null,
    kcal_per_100g: product.kcalPer100g ?? null,
    total_kcal: product.totalKcal ?? null,
    pieces_per_pack: product.piecesPerPack ?? null,
    kcal_per_piece: product.kcalPerPiece ?? null,
    verified: product.verified,
  };
}

export function mapFeedingLogRow(row: FeedingLogRow): FeedingLog {
  return {
    id: row.id,
    dogId: row.dog_id,
    logDate: row.log_date,
    foodProductId: row.food_product_id ?? undefined,
    treatProductId: row.treat_product_id ?? undefined,
    foodGrams: Number(row.food_grams),
    treatPieces: Number(row.treat_pieces),
    foodKcal: Number(row.food_kcal),
    treatKcal: Number(row.treat_kcal),
    totalKcal: Number(row.total_kcal),
    recommendedKcal: Number(row.recommended_kcal),
    note: row.note ?? undefined,
  };
}

export function toFeedingLogRow(log: FeedingLog): FeedingLogRow {
  return {
    id: log.id,
    dog_id: log.dogId,
    log_date: log.logDate,
    food_product_id: log.foodProductId ?? null,
    treat_product_id: log.treatProductId ?? null,
    food_grams: log.foodGrams,
    treat_pieces: log.treatPieces,
    food_kcal: log.foodKcal,
    treat_kcal: log.treatKcal,
    total_kcal: log.totalKcal,
    recommended_kcal: log.recommendedKcal,
    note: log.note ?? null,
  };
}
