"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { getRecommendedCalories } from "@/lib/mock-data";
import {
  getStoredSelectedDogId,
  hydrateDogsFromStorage,
  setStoredSelectedDogId,
  upsertDogProfile,
} from "@/lib/repositories/dogs-client";
import { hydrateFeedingLogsFromStorage } from "@/lib/repositories/feeding-logs-client";
import { DogProfile, Product, FeedingLog } from "@/lib/types";

type HomeDashboardProps = {
  initialDogs: DogProfile[];
  featuredProducts: Product[];
  feedingLogs: FeedingLog[];
};

type DogDraft = {
  id?: string;
  name: string;
  weightKg: string;
  ageGroup: DogProfile["ageGroup"];
  activityFactor: string;
  isNeutered: boolean;
  note: string;
};

const emptyDraft: DogDraft = {
  name: "",
  weightKg: "",
  ageGroup: "adult",
  activityFactor: "1.6",
  isNeutered: true,
  note: "",
};

function toDraft(dog: DogProfile): DogDraft {
  return {
    id: dog.id,
    name: dog.name,
    weightKg: String(dog.weightKg),
    ageGroup: dog.ageGroup,
    activityFactor: String(dog.activityFactor),
    isNeutered: dog.isNeutered,
    note: dog.note ?? "",
  };
}

export function HomeDashboard({
  initialDogs,
  featuredProducts,
  feedingLogs,
}: HomeDashboardProps) {
  const [dogs, setDogs] = useState(() => hydrateDogsFromStorage(initialDogs));
  const [logs] = useState(() => hydrateFeedingLogsFromStorage(feedingLogs));
  const [selectedDogId, setSelectedDogId] = useState(
    () => getStoredSelectedDogId() ?? hydrateDogsFromStorage(initialDogs)[0]?.id ?? "",
  );
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [draft, setDraft] = useState<DogDraft>(emptyDraft);
  const [statusMessage, setStatusMessage] = useState("강아지를 선택하고 오늘 급여 흐름으로 이동할 수 있어요.");
  const [isSaving, setIsSaving] = useState(false);

  const dogCards = useMemo(
    () =>
      dogs.map((dog) => {
        const calories = getRecommendedCalories(dog);
        const latestLog = logs.find((log) => log.dogId === dog.id);

        return {
          ...dog,
          rer: calories.rer,
          recommended: calories.recommended,
          latestLog,
        };
      }),
    [dogs, logs],
  );

  const selectedDog = dogCards.find((dog) => dog.id === selectedDogId) ?? dogCards[0] ?? null;
  const recentLogs = useMemo(
    () => logs.filter((log) => (selectedDog ? log.dogId === selectedDog.id : true)).slice(0, 4),
    [logs, selectedDog],
  );

  function openNewEditor() {
    setDraft(emptyDraft);
    setIsEditorOpen(true);
  }

  function openEditEditor(dog: DogProfile) {
    setDraft(toDraft(dog));
    setIsEditorOpen(true);
  }

  async function handleSaveDog() {
    const weight = Number(draft.weightKg);
    const activity = Number(draft.activityFactor);

    if (!draft.name.trim() || !Number.isFinite(weight) || weight <= 0) {
      setStatusMessage("이름과 체중을 먼저 정확히 입력해 주세요.");
      return;
    }

    setIsSaving(true);
    setStatusMessage("프로필을 저장하는 중입니다...");

    try {
      const savedDog = await upsertDogProfile(
        {
          id: draft.id,
          name: draft.name.trim(),
          weightKg: weight,
          ageGroup: draft.ageGroup,
          activityFactor: Number.isFinite(activity) && activity > 0 ? activity : 1.6,
          isNeutered: draft.isNeutered,
          note: draft.note.trim() || undefined,
        },
        dogs,
      );

      const nextDogs = dogs.some((dog) => dog.id === savedDog.id)
        ? dogs.map((dog) => (dog.id === savedDog.id ? savedDog : dog))
        : [savedDog, ...dogs];

      setDogs(nextDogs);
      setSelectedDogId(savedDog.id);
      setStoredSelectedDogId(savedDog.id);
      setIsEditorOpen(false);
      setDraft(emptyDraft);
      setStatusMessage(`${savedDog.name} 프로필을 저장했습니다.`);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "프로필 저장 중 문제가 발생했습니다.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="hero-panel">
        <div className="space-y-4">
          <p className="eyebrow">Dog Food & Treat Tracker</p>
          <div className="space-y-3">
            <h1 className="hero-title">강아지별 하루 칼로리를 빠르게 확인하는 모바일 앱</h1>
            <p className="hero-copy">
              첫 단계는 강아지 선택, 두 번째는 제품 검색, 세 번째는 오늘 급여량 입력입니다.
              고급 수치는 제품 선택 뒤 자동으로 채우고, 검색 실패 시에는 직접 등록할 수 있게
              설계합니다.
            </p>
          </div>
        </div>
        <div className="hero-actions">
          <Link
            className="primary-cta"
            href={selectedDog ? `/search?dogId=${encodeURIComponent(selectedDog.id)}` : "/search"}
          >
            {selectedDog ? `${selectedDog.name} 오늘 급여 시작` : "오늘 급여 시작"}
          </Link>
          <Link
            className="secondary-cta"
            href={
              selectedDog
                ? `/products/new?dogId=${encodeURIComponent(selectedDog.id)}`
                : "/products/new"
            }
          >
            제품 직접 등록
          </Link>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">Phase 1</p>
              <h2>강아지 선택</h2>
            </div>
            <button className="ghost-chip" type="button" onClick={openNewEditor}>
              새 프로필 추가
            </button>
          </div>

          <p className="inline-status">{statusMessage}</p>

          <div className="mt-5 grid gap-4">
            {dogCards.map((dog) => (
              <article className={`dog-card ${selectedDogId === dog.id ? "dog-card-active" : ""}`} key={dog.id}>
                <div className="dog-card-top">
                  <div>
                    <p className="dog-name">{dog.name}</p>
                    <p className="muted-copy">
                      {dog.weightKg}kg · {dog.ageGroup} · 활동계수 {dog.activityFactor}
                    </p>
                  </div>
                  <span className="badge">{dog.isNeutered ? "중성화" : "비중성화"}</span>
                </div>

                <div className="metric-grid">
                  <div className="metric-card">
                    <span>권장 하루 kcal</span>
                    <strong>{dog.recommended.toFixed(0)} kcal</strong>
                  </div>
                  <div className="metric-card">
                    <span>최근 기록</span>
                    <strong>
                      {dog.latestLog ? `${dog.latestLog.totalKcal.toFixed(0)} kcal` : "기록 없음"}
                    </strong>
                  </div>
                </div>

                <div className="card-actions">
                  <button
                    className="primary-small"
                    type="button"
                    onClick={() => {
                      setSelectedDogId(dog.id);
                      setStoredSelectedDogId(dog.id);
                      setStatusMessage(`${dog.name} 기준으로 오늘 급여 입력을 시작할 준비가 됐어요.`);
                    }}
                  >
                    {dog.name}로 시작
                  </button>
                  <button className="text-button" type="button" onClick={() => openEditEditor(dog)}>
                    프로필 수정
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="stack gap-6">
          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">Selected Dog</p>
                <h2>현재 선택된 강아지</h2>
              </div>
            </div>

            {selectedDog ? (
              <div className="selected-dog-card">
                <p className="dog-name">{selectedDog.name}</p>
                <p className="muted-copy">
                  {selectedDog.weightKg}kg · {selectedDog.ageGroup} · 활동계수 {selectedDog.activityFactor}
                </p>
                <div className="metric-grid">
                  <div className="metric-card">
                    <span>RER</span>
                    <strong>{selectedDog.rer.toFixed(0)} kcal</strong>
                  </div>
                  <div className="metric-card">
                    <span>권장 하루 kcal</span>
                    <strong>{selectedDog.recommended.toFixed(0)} kcal</strong>
                  </div>
                </div>
              </div>
            ) : (
              <p className="muted-copy">먼저 강아지 프로필을 하나 추가해 주세요.</p>
            )}
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">Recent Logs</p>
                <h2>최근 기록</h2>
              </div>
            </div>

            <div className="mt-4 grid gap-3">
              {recentLogs.length ? (
                recentLogs.map((log) => (
                  <article className="log-card" key={log.id}>
                    <div className="log-card-top">
                      <div>
                        <p className="product-title">{log.logDate}</p>
                        <p className="muted-copy">
                          {log.foodProductName || "사료 미입력"}
                          {log.treatProductName ? ` + ${log.treatProductName}` : ""}
                        </p>
                      </div>
                      <span className="badge">{log.totalKcal.toFixed(0)} kcal</span>
                    </div>
                    <div className="metric-grid">
                      <div className="metric-card">
                        <span>사료</span>
                        <strong>{log.foodKcal.toFixed(1)} kcal</strong>
                      </div>
                      <div className="metric-card">
                        <span>간식</span>
                        <strong>{log.treatKcal.toFixed(1)} kcal</strong>
                      </div>
                    </div>
                  </article>
                ))
              ) : (
                <p className="muted-copy">저장된 기록이 아직 없습니다. 계산 화면에서 하루 기록을 남겨보세요.</p>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">Featured</p>
                <h2>검수된 제품 예시</h2>
              </div>
            </div>

            <div className="mt-4 grid gap-3">
              {featuredProducts.map((product) => (
                <article className="product-row" key={product.id}>
                  <div>
                    <p className="product-title">{product.name}</p>
                    <p className="muted-copy">{product.brand}</p>
                  </div>
                  <div className="product-meta">
                    <span>{product.kind === "food" ? "사료" : "간식"}</span>
                    <strong>
                      {product.kcalPer100g
                        ? `${product.kcalPer100g} kcal/100g`
                        : `${product.kcalPerPiece} kcal/개`}
                    </strong>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="section-kicker">Roadmap</p>
            <h2>이번 단계에서 만들 흐름</h2>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-4">
          {[
            {
              title: "1. 강아지 선택",
              body: "프로필을 고르고 오늘 급여를 시작합니다.",
            },
            {
              title: "2. 제품 검색",
              body: "사료와 간식을 각각 검색하고 빠르게 선택합니다.",
            },
            {
              title: "3. kcal 계산",
              body: "기본 입력은 g와 개수만 두고 나머지는 자동 계산합니다.",
            },
            {
              title: "4. 기록 저장",
              body: "하루 총칼로리와 권장량 비교를 기록으로 남깁니다.",
            },
          ].map((step) => (
            <article className="step-card" key={step.title}>
              <p className="step-title">{step.title}</p>
              <p className="muted-copy">{step.body}</p>
            </article>
          ))}
        </div>
      </section>

      {isEditorOpen ? (
        <div className="modal-overlay" role="presentation" onClick={() => setIsEditorOpen(false)}>
          <div className="modal-card" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <div className="section-head">
              <div>
                <p className="section-kicker">{draft.id ? "Edit Profile" : "New Profile"}</p>
                <h2>{draft.id ? "강아지 프로필 수정" : "강아지 프로필 추가"}</h2>
              </div>
              <button className="ghost-chip" type="button" onClick={() => setIsEditorOpen(false)}>
                닫기
              </button>
            </div>

            <div className="form-stack">
              <label className="field-group">
                <span>이름</span>
                <input
                  className="field-input"
                  value={draft.name}
                  onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
                  placeholder="예: 멜로"
                />
              </label>

              <div className="field-grid">
                <label className="field-group">
                  <span>체중(kg)</span>
                  <input
                    className="field-input"
                    inputMode="decimal"
                    value={draft.weightKg}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, weightKg: event.target.value }))
                    }
                    placeholder="예: 9.0"
                  />
                </label>

                <label className="field-group">
                  <span>활동량</span>
                  <select
                    className="field-input"
                    value={draft.activityFactor}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, activityFactor: event.target.value }))
                    }
                  >
                    <option value="1.2">낮음 / 체중관리</option>
                    <option value="1.6">보통</option>
                    <option value="2.0">활동적</option>
                    <option value="3.0">매우 활동적 / 성장기</option>
                  </select>
                </label>
              </div>

              <div className="field-grid">
                <label className="field-group">
                  <span>연령군</span>
                  <select
                    className="field-input"
                    value={draft.ageGroup}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        ageGroup: event.target.value as DogProfile["ageGroup"],
                      }))
                    }
                  >
                    <option value="puppy">퍼피 / 성장기</option>
                    <option value="adult">성견</option>
                    <option value="senior">노령견</option>
                  </select>
                </label>

                <label className="field-group checkbox-group">
                  <span>중성화 여부</span>
                  <button
                    className={`toggle-pill ${draft.isNeutered ? "toggle-pill-active" : ""}`}
                    type="button"
                    onClick={() =>
                      setDraft((current) => ({ ...current, isNeutered: !current.isNeutered }))
                    }
                  >
                    {draft.isNeutered ? "중성화 완료" : "비중성화"}
                  </button>
                </label>
              </div>

              <label className="field-group">
                <span>메모</span>
                <textarea
                  className="field-input field-textarea"
                  value={draft.note}
                  onChange={(event) => setDraft((current) => ({ ...current, note: event.target.value }))}
                  placeholder="알레르기, 식탐, 체중관리 메모 등"
                />
              </label>
            </div>

            <div className="hero-actions">
              <button className="primary-cta" type="button" onClick={handleSaveDog} disabled={isSaving}>
                {isSaving ? "저장 중..." : "프로필 저장"}
              </button>
              <button className="secondary-cta" type="button" onClick={() => setIsEditorOpen(false)}>
                취소
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
