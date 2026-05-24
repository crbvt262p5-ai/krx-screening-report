"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { dogs, getRecommendedCalories } from "@/lib/mock-data";
import {
  getStoredSelectedDogId,
  hydrateDogsFromStorage,
  setStoredSelectedDogId,
} from "@/lib/repositories/dogs-client";
import {
  createFeedingLog,
  hydrateFeedingLogsFromStorage,
} from "@/lib/repositories/feeding-logs-client";
import { FeedingLog, ProductKind } from "@/lib/types";

function getNumber(value: string | null) {
  if (!value) {
    return undefined;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function FeedingPanel() {
  const searchParams = useSearchParams();
  const availableDogs = useMemo(() => hydrateDogsFromStorage(dogs), []);
  const selectedDogId = searchParams.get("dogId") ?? getStoredSelectedDogId();
  const selectedDog =
    availableDogs.find((dog) => dog.id === selectedDogId) ?? availableDogs[0] ?? dogs[0];
  const recommended = getRecommendedCalories(selectedDog);

  const productId = searchParams.get("id") || undefined;
  const productName = searchParams.get("name") || "선택된 제품";
  const productBrand = searchParams.get("brand") || "-";
  const productKind = (searchParams.get("kind") as ProductKind) || "food";
  const kcalPer100g = getNumber(searchParams.get("kcalPer100g"));
  const kcalPerPiece = getNumber(searchParams.get("kcalPerPiece"));
  const totalKcal = getNumber(searchParams.get("totalKcal"));

  const [foodGrams, setFoodGrams] = useState("80");
  const [treatPieces, setTreatPieces] = useState("2");
  const [manualKcalPer100g, setManualKcalPer100g] = useState(
    kcalPer100g ? String(kcalPer100g) : "",
  );
  const [manualKcalPerPiece, setManualKcalPerPiece] = useState(
    kcalPerPiece ? String(kcalPerPiece) : "",
  );
  const [saveStatus, setSaveStatus] = useState(
    "계산 결과를 확인한 뒤 오늘 기록으로 저장할 수 있어요.",
  );
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (selectedDog?.id) {
      setStoredSelectedDogId(selectedDog.id);
    }
  }, [selectedDog?.id]);

  const computed = useMemo(() => {
    const grams = Number(foodGrams);
    const pieces = Number(treatPieces);
    const foodBase = Number(manualKcalPer100g) || kcalPer100g || 0;
    const treatBase =
      Number(manualKcalPerPiece) ||
      kcalPerPiece ||
      (totalKcal && pieces > 0 ? totalKcal / pieces : 0);

    const foodKcal = productKind === "food" ? (grams * foodBase) / 100 : 0;
    const treatKcal = productKind === "treat" ? pieces * treatBase : 0;
    const total = foodKcal + treatKcal;
    const diff = total - recommended.recommended;

    return {
      foodKcal,
      treatKcal,
      total,
      comparison:
        Math.abs(diff) < recommended.recommended * 0.05
          ? "권장량과 비슷해요"
          : diff > 0
            ? `${diff.toFixed(1)} kcal 많아요`
            : `${Math.abs(diff).toFixed(1)} kcal 적어요`,
    };
  }, [
    foodGrams,
    treatPieces,
    kcalPer100g,
    kcalPerPiece,
    manualKcalPer100g,
    manualKcalPerPiece,
    productKind,
    recommended.recommended,
    totalKcal,
  ]);

  async function handleSaveLog() {
    if (!selectedDog?.id) {
      setSaveStatus("먼저 강아지 프로필을 선택해 주세요.");
      return;
    }

    const existingLogs = hydrateFeedingLogsFromStorage([]);
    const today = new Date().toLocaleDateString("sv-SE");

    const log: FeedingLog = {
      id: crypto.randomUUID(),
      dogId: selectedDog.id,
      logDate: today,
      foodProductId: productKind === "food" ? productId : undefined,
      treatProductId: productKind === "treat" ? productId : undefined,
      foodProductName: productKind === "food" ? productName : undefined,
      treatProductName: productKind === "treat" ? productName : undefined,
      foodGrams: productKind === "food" ? Number(foodGrams) || 0 : 0,
      treatPieces: productKind === "treat" ? Number(treatPieces) || 0 : 0,
      foodKcal: computed.foodKcal,
      treatKcal: computed.treatKcal,
      totalKcal: computed.total,
      recommendedKcal: recommended.recommended,
      note: `${productBrand} · ${computed.comparison}`,
    };

    setIsSaving(true);
    setSaveStatus("오늘 급여 기록을 저장하는 중입니다...");

    try {
      await createFeedingLog(log, existingLogs);
      setSaveStatus(`${selectedDog.name}의 ${today} 기록을 저장했습니다.`);
    } catch (error) {
      setSaveStatus(
        error instanceof Error ? error.message : "급여 기록 저장 중 문제가 발생했습니다.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="hero-panel">
        <div className="space-y-4">
          <p className="eyebrow">Daily Feeding</p>
          <div className="space-y-3">
            <h1 className="hero-title">선택한 제품으로 오늘 급여량을 바로 계산합니다</h1>
            <p className="hero-copy">
              기본 입력은 사료 g 또는 간식 개수만 남기고, 필요한 경우에만 kcal 값을 수동 보정합니다.
            </p>
          </div>
        </div>
        <div className="hero-actions">
          <Link
            className="secondary-cta"
            href={selectedDog ? `/search?dogId=${encodeURIComponent(selectedDog.id)}` : "/search"}
          >
            검색으로 돌아가기
          </Link>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">Selected Product</p>
              <h2>급여 입력</h2>
            </div>
          </div>

          <article className="selected-dog-card mt-4">
            <p className="product-title">{productName}</p>
            <p className="muted-copy">
              {productBrand} · {productKind === "food" ? "사료" : "간식"}
            </p>
          </article>

          <div className="form-stack">
            {productKind === "food" ? (
              <>
                <label className="field-group">
                  <span>오늘 먹인 양(g)</span>
                  <input
                    className="field-input"
                    inputMode="decimal"
                    value={foodGrams}
                    onChange={(event) => setFoodGrams(event.target.value)}
                  />
                </label>
                <label className="field-group">
                  <span>100g당 kcal 보정</span>
                  <input
                    className="field-input"
                    inputMode="decimal"
                    value={manualKcalPer100g}
                    onChange={(event) => setManualKcalPer100g(event.target.value)}
                    placeholder={kcalPer100g ? `${kcalPer100g}` : "예: 380"}
                  />
                </label>
              </>
            ) : (
              <>
                <label className="field-group">
                  <span>오늘 먹인 개수</span>
                  <input
                    className="field-input"
                    inputMode="numeric"
                    value={treatPieces}
                    onChange={(event) => setTreatPieces(event.target.value)}
                  />
                </label>
                <label className="field-group">
                  <span>1개당 kcal 보정</span>
                  <input
                    className="field-input"
                    inputMode="decimal"
                    value={manualKcalPerPiece}
                    onChange={(event) => setManualKcalPerPiece(event.target.value)}
                    placeholder={kcalPerPiece ? `${kcalPerPiece}` : "예: 35"}
                  />
                </label>
              </>
            )}
          </div>
        </section>

        <aside className="stack gap-6">
          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">Selected Dog</p>
                <h2>{selectedDog.name} 기준</h2>
              </div>
            </div>

            <div className="selected-dog-card mt-4">
              <p className="muted-copy">
                {selectedDog.weightKg}kg · {selectedDog.ageGroup} · 활동계수 {selectedDog.activityFactor}
              </p>
              <div className="metric-grid">
                <div className="metric-card">
                  <span>RER</span>
                  <strong>{recommended.rer.toFixed(0)} kcal</strong>
                </div>
                <div className="metric-card">
                  <span>권장 하루 kcal</span>
                  <strong>{recommended.recommended.toFixed(0)} kcal</strong>
                </div>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">Result</p>
                <h2>계산 결과</h2>
              </div>
            </div>

            <div className="mt-4 grid gap-3">
              <article className="metric-card">
                <span>사료 칼로리</span>
                <strong>{computed.foodKcal.toFixed(1)} kcal</strong>
              </article>
              <article className="metric-card">
                <span>간식 칼로리</span>
                <strong>{computed.treatKcal.toFixed(1)} kcal</strong>
              </article>
              <article className="metric-card">
                <span>하루 총칼로리</span>
                <strong>{computed.total.toFixed(1)} kcal</strong>
              </article>
              <article className="metric-card">
                <span>권장량 비교</span>
                <strong>{computed.comparison}</strong>
              </article>
            </div>

            <p className="inline-status">{saveStatus}</p>

            <div className="hero-actions mt-4">
              <button className="primary-cta" type="button" onClick={handleSaveLog} disabled={isSaving}>
                {isSaving ? "기록 저장 중..." : "오늘 기록 저장"}
              </button>
              <Link className="secondary-cta" href="/">
                홈으로 돌아가기
              </Link>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
