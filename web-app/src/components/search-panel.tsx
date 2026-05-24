"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStoredSelectedDogId } from "@/lib/repositories/dogs-client";
import { searchManualProducts } from "@/lib/repositories/products-client";
import { Product, ProductKind } from "@/lib/types";

function buildFeedingLink(product: Product, dogId?: string) {
  const params = new URLSearchParams({
    id: product.id,
    name: product.name,
    brand: product.brand,
    kind: product.kind,
  });

  if (dogId) {
    params.set("dogId", dogId);
  }

  if (product.kcalPer100g) {
    params.set("kcalPer100g", String(product.kcalPer100g));
  }

  if (product.kcalPerPiece) {
    params.set("kcalPerPiece", String(product.kcalPerPiece));
  }

  if (product.totalKcal) {
    params.set("totalKcal", String(product.totalKcal));
  }

  return `/feeding?${params.toString()}`;
}

type SearchPayload = {
  query: string;
  kind: ProductKind;
  localResults: Product[];
  externalResults: Product[];
  error?: string;
};

type SearchPanelProps = {
  initialDogId?: string;
  initialQuery?: string;
  initialKind?: ProductKind;
};

export function SearchPanel({
  initialDogId,
  initialQuery = "",
  initialKind = "food",
}: SearchPanelProps) {
  const [activeDogId] = useState(() => initialDogId ?? getStoredSelectedDogId() ?? "");
  const [query, setQuery] = useState(initialQuery);
  const [kind, setKind] = useState<ProductKind>(initialKind);
  const [isLoading, setIsLoading] = useState(false);
  const [payload, setPayload] = useState<SearchPayload | null>(null);
  const [status, setStatus] = useState("사료나 간식을 검색해 보세요. 제출형 검색으로만 동작합니다.");

  async function runSearch(nextQuery: string, nextKind: ProductKind) {
    if (!nextQuery.trim()) {
      setStatus("검색어를 입력해 주세요.");
      return;
    }

    setIsLoading(true);
    setStatus("제품을 찾는 중입니다...");

    try {
      const response = await fetch(
        `/api/products/search?q=${encodeURIComponent(nextQuery.trim())}&kind=${nextKind}`,
      );
      const json = (await response.json()) as SearchPayload & { error?: string };

      if (!response.ok) {
        throw new Error(json.error || "검색에 실패했습니다.");
      }

      const manualResults = searchManualProducts(nextQuery.trim(), nextKind);
      const localResults = [...manualResults, ...json.localResults].filter(
        (product, index, array) =>
          array.findIndex(
            (candidate) =>
              candidate.name === product.name && candidate.brand === product.brand,
          ) === index,
      );

      setPayload({
        ...json,
        localResults,
      });
      setStatus(
        `로컬 ${localResults.length}개, 외부 ${json.externalResults.length}개 결과를 찾았습니다.`,
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "검색 중 문제가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runSearch(query, kind);
  }

  useEffect(() => {
    if (!initialQuery.trim()) {
      return;
    }

    const timer = window.setTimeout(() => {
      void runSearch(initialQuery, initialKind);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [initialKind, initialQuery]);

  const manualHref = initialDogId
    ? `/products/new?dogId=${encodeURIComponent(initialDogId)}`
    : "/products/new";
  const resolvedManualHref = activeDogId
    ? `/products/new?dogId=${encodeURIComponent(activeDogId)}`
    : manualHref;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="hero-panel">
        <div className="space-y-4">
          <p className="eyebrow">Product Search</p>
          <div className="space-y-3">
            <h1 className="hero-title">사료와 간식을 검색해서 자동 계산 가능한 제품을 고릅니다</h1>
            <p className="hero-copy">
              로컬 검수 제품을 먼저 보여주고, 부족하면 Open Pet Food Facts와 Open Food Facts
              결과를 같이 보여줍니다.
            </p>
          </div>
        </div>
        <div className="hero-actions">
          <Link className="secondary-cta" href="/">
            강아지 선택으로 돌아가기
          </Link>
          <Link className="secondary-cta" href={resolvedManualHref}>
            제품 직접 등록
          </Link>
        </div>
      </section>

      <section className="panel">
        <form className="search-form-grid" onSubmit={handleSearch}>
          <label className="field-group">
            <span>제품 종류</span>
            <select
              className="field-input"
              value={kind}
              onChange={(event) => setKind(event.target.value as ProductKind)}
            >
              <option value="food">사료</option>
              <option value="treat">간식</option>
            </select>
          </label>

          <label className="field-group search-field-wide">
            <span>검색어</span>
            <input
              className="field-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="예: 오리젠 스몰브리드, 로얄캐닌 미니"
            />
          </label>

          <button className="primary-cta search-submit" type="submit" disabled={isLoading}>
            {isLoading ? "검색 중..." : "검색"}
          </button>
        </form>

        <p className="inline-status">{status}</p>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">Local First</p>
              <h2>검수 제품</h2>
            </div>
          </div>

          <div className="mt-4 grid gap-3">
            {payload?.localResults.length ? (
              payload.localResults.map((product) => (
                <article className="product-row product-row-card" key={`local-${product.id}`}>
                  <div>
                    <p className="product-title">{product.name}</p>
                    <p className="muted-copy">{product.brand}</p>
                  </div>
                  <div className="product-meta">
                    <span>{product.kind === "food" ? "사료" : "간식"}</span>
                    <strong>
                      {product.kcalPer100g
                        ? `${product.kcalPer100g} kcal/100g`
                        : product.kcalPerPiece
                          ? `${product.kcalPerPiece} kcal/개`
                          : "보정 필요"}
                    </strong>
                    <Link
                      className="text-button product-select-link"
                      href={buildFeedingLink(product, activeDogId)}
                    >
                      이 제품으로 계산
                    </Link>
                  </div>
                </article>
              ))
            ) : (
              <p className="muted-copy">아직 로컬 검수 결과가 없습니다. 직접 등록한 제품도 여기에 함께 표시됩니다.</p>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">External</p>
              <h2>외부 검색 결과</h2>
            </div>
          </div>

          <div className="mt-4 grid gap-3">
            {payload?.externalResults.length ? (
              payload.externalResults.map((product) => (
                <article className="product-row product-row-card" key={`external-${product.id}`}>
                  <div>
                    <p className="product-title">{product.name}</p>
                    <p className="muted-copy">{product.brand}</p>
                  </div>
                  <div className="product-meta">
                    <span>{product.kind === "food" ? "사료" : "간식"}</span>
                    <strong>
                      {product.kcalPer100g
                        ? `${product.kcalPer100g} kcal/100g`
                        : product.totalKcal
                          ? `${product.totalKcal} kcal/총량`
                          : "데이터 부족"}
                    </strong>
                    <Link
                      className="text-button product-select-link"
                      href={buildFeedingLink(product, activeDogId)}
                    >
                      이 제품으로 계산
                    </Link>
                  </div>
                </article>
              ))
            ) : (
              <p className="muted-copy">외부 검색 결과가 없으면 다음 단계에서 직접 등록 플로우를 붙입니다.</p>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
