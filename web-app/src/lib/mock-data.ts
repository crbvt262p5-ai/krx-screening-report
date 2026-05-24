import { DogProfile, FeedingLog, Product } from "@/lib/types";

export const dogs: DogProfile[] = [
  {
    id: "dog-mello",
    name: "멜로",
    weightKg: 9,
    ageGroup: "adult",
    activityFactor: 1.6,
    isNeutered: true,
    note: "식탐이 있어서 간식 칼로리 체크가 중요함",
  },
  {
    id: "dog-coco",
    name: "코코",
    weightKg: 4.2,
    ageGroup: "senior",
    activityFactor: 1.2,
    isNeutered: true,
  },
];

export const products: Product[] = [
  {
    id: "food-orijen-small",
    kind: "food",
    sourceType: "internal",
    name: "오리젠 스몰브리드",
    brand: "ORIJEN",
    aliases: ["오리젠", "오리젠 스몰", "orijen small breed"],
    totalWeightG: 1500,
    kcalPer100g: 390,
    totalKcal: 5850,
    verified: true,
  },
  {
    id: "treat-dental-soft",
    kind: "treat",
    sourceType: "manual",
    name: "덴탈 소프트 츄",
    brand: "멍데이",
    aliases: ["덴탈츄", "소프트츄"],
    totalWeightG: 300,
    totalKcal: 960,
    piecesPerPack: 24,
    kcalPerPiece: 40,
    verified: true,
  },
  {
    id: "food-royal-mini",
    kind: "food",
    sourceType: "open_pet_food_facts",
    name: "로얄캐닌 미니 어덜트",
    brand: "Royal Canin",
    aliases: ["로얄캐닌", "미니 어덜트"],
    totalWeightG: 800,
    kcalPer100g: 374,
    totalKcal: 2992,
    verified: false,
  },
];

export const feedingLogs: FeedingLog[] = [
  {
    id: "log-2026-04-18-mello",
    dogId: "dog-mello",
    logDate: "2026-04-18",
    foodProductId: "food-orijen-small",
    treatProductId: "treat-dental-soft",
    foodProductName: "오리젠 스몰브리드",
    treatProductName: "덴탈 소프트 츄",
    foodGrams: 85,
    treatPieces: 2,
    foodKcal: 331.5,
    treatKcal: 80,
    totalKcal: 411.5,
    recommendedKcal: 364,
  },
  {
    id: "log-2026-04-18-coco",
    dogId: "dog-coco",
    foodProductId: "food-royal-mini",
    logDate: "2026-04-18",
    foodProductName: "로얄캐닌 미니 어덜트",
    treatProductName: "저칼로리 트릿",
    foodGrams: 55,
    treatPieces: 1,
    foodKcal: 205.7,
    treatKcal: 35,
    totalKcal: 240.7,
    recommendedKcal: 226.4,
  },
];

export function getRecommendedCalories(dog: DogProfile) {
  const rer = 70 * Math.pow(dog.weightKg, 0.75);
  const recommended = rer * dog.activityFactor;

  return {
    rer,
    recommended,
  };
}
