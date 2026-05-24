export type DogAgeGroup = "puppy" | "adult" | "senior";
export type ProductKind = "food" | "treat";
export type SourceType = "manual" | "internal" | "open_pet_food_facts";

export type DogProfile = {
  id: string;
  name: string;
  weightKg: number;
  ageGroup: DogAgeGroup;
  activityFactor: number;
  isNeutered: boolean;
  note?: string;
};

export type Product = {
  id: string;
  kind: ProductKind;
  sourceType: SourceType;
  name: string;
  brand: string;
  aliases: string[];
  totalWeightG?: number;
  kcalPer100g?: number;
  totalKcal?: number;
  piecesPerPack?: number;
  kcalPerPiece?: number;
  verified: boolean;
};

export type FeedingLog = {
  id: string;
  dogId: string;
  logDate: string;
  foodProductId?: string;
  treatProductId?: string;
  foodProductName?: string;
  treatProductName?: string;
  foodGrams: number;
  treatPieces: number;
  foodKcal: number;
  treatKcal: number;
  totalKcal: number;
  recommendedKcal: number;
  note?: string;
};
