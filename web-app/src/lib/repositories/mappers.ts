import { DogProfile, FeedingLog, Product } from "@/lib/types";
import { PortfolioPosition } from "@/lib/portfolio-dashboard";

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

export type PortfolioPositionRow = {
  row_id: string;
  ticker: string;
  name: string;
  market_scope: string;
  asset_class: string;
  country: string;
  theme: string;
  theme_category?: string | null;
  sub_theme?: string | null;
  strategy?: string | null;
  style_bucket?: string | null;
  trend_view?: string | null;
  cycle_view?: string | null;
  conviction?: string | null;
  fx_exposure?: string | null;
  timing_view?: string | null;
  actual_weight_pct: number;
  target_weight_pct: number;
  per?: number | null;
  pbr?: number | null;
  eps?: number | null;
  forward_per?: number | null;
  planned_action?: string | null;
  notes?: string | null;
  sort_order: number;
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

export function mapPortfolioPositionRow(row: PortfolioPositionRow): PortfolioPosition {
  return {
    rowId: row.row_id,
    ticker: row.ticker,
    name: row.name,
    marketScope: row.market_scope,
    assetClass: row.asset_class,
    country: row.country,
    theme: row.theme,
    themeCategory: row.theme_category ?? "",
    subTheme: row.sub_theme ?? "",
    strategy: row.strategy ?? "",
    styleBucket: row.style_bucket ?? "",
    trendView: row.trend_view ?? "",
    cycleView: row.cycle_view ?? "",
    conviction: row.conviction ?? "",
    fxExposure: row.fx_exposure ?? "",
    timingView: row.timing_view ?? "",
    actualWeightPct: Number(row.actual_weight_pct),
    targetWeightPct: Number(row.target_weight_pct),
    per: row.per ?? null,
    pbr: row.pbr ?? null,
    eps: row.eps ?? null,
    forwardPer: row.forward_per ?? null,
    plannedAction: row.planned_action ?? "",
    notes: row.notes ?? "",
  };
}

export function toPortfolioPositionRow(
  row: PortfolioPosition,
  sortOrder: number,
): PortfolioPositionRow {
  return {
    row_id: row.rowId,
    ticker: row.ticker,
    name: row.name,
    market_scope: row.marketScope,
    asset_class: row.assetClass,
    country: row.country,
    theme: row.theme,
    theme_category: row.themeCategory || null,
    sub_theme: row.subTheme || null,
    strategy: row.strategy || null,
    style_bucket: row.styleBucket || null,
    trend_view: row.trendView || null,
    cycle_view: row.cycleView || null,
    conviction: row.conviction || null,
    fx_exposure: row.fxExposure || null,
    timing_view: row.timingView || null,
    actual_weight_pct: row.actualWeightPct,
    target_weight_pct: row.targetWeightPct,
    per: row.per,
    pbr: row.pbr,
    eps: row.eps,
    forward_per: row.forwardPer,
    planned_action: row.plannedAction || null,
    notes: row.notes || null,
    sort_order: sortOrder,
  };
}
