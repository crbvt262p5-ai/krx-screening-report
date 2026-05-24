"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { getStoredSelectedDogId } from "@/lib/repositories/dogs-client";
import { createManualProduct } from "@/lib/repositories/products-client";
import { ProductKind } from "@/lib/types";

type ManualProductFormProps = {
  initialDogId?: string;
};

type ProductDraft = {
  name: string;
  brand: string;
  kind: ProductKind;
  totalWeightG: string;
  kcalPer100g: string;
  kcalPerPiece: string;
  totalKcal: string;
};

const emptyDraft: ProductDraft = {
  name: "",
  brand: "",
  kind: "food",
  totalWeightG: "",
  kcalPer100g: "",
  kcalPerPiece: "",
  totalKcal: "",
};

function getNumber(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

export function ManualProductForm({ initialDogId }: ManualProductFormProps) {
  const router = useRouter();
  const [activeDogId] = useState(() => initialDogId ?? getStoredSelectedDogId() ?? "");
  const [draft, setDraft] = useState<ProductDraft>(emptyDraft);
  const [status, setStatus] = useState(
    "검색 결과가 없을 때 자주 먹는 제품을 직접 등록해 둘 수 있어요.",
  );
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!draft.name.trim()) {
      setStatus("제품 이름을 먼저 입력해 주세요.");
      return;
    }

    if (draft.kind === "food" && !getNumber(draft.kcalPer100g) && !getNumber(draft.totalKcal)) {
      setStatus("사료는 100g당 kcal 또는 총 kcal 중 하나는 필요합니다.");
      return;
    }

    if (draft.kind === "treat" && !getNumber(draft.kcalPerPiece) && !getNumber(draft.totalKcal)) {
      setStatus("간식은 1개당 kcal 또는 총 kcal 중 하나는 필요합니다.");
      return;
    }

    setIsSaving(true);
    setStatus("제품 정보를 저장하는 중입니다...");

    try {
      const saved = await createManualProduct({
        id: crypto.randomUUID(),
        kind: draft.kind,
        sourceType: "manual",
        name: draft.name.trim(),
        brand: draft.brand.trim() || "직접 등록",
        aliases: [],
        totalWeightG: getNumber(draft.totalWeightG),
        kcalPer100g: getNumber(draft.kcalPer100g),
        totalKcal: getNumber(draft.totalKcal),
        kcalPerPiece: getNumber(draft.kcalPerPiece),
        verified: true,
      });

      const params = new URLSearchParams({
        q: saved.name,
        kind: saved.kind,
      });

      if (activeDogId) {
        params.set("dogId", activeDogId);
      }

      router.push(`/search?${params.toString()}`);
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "제품 등록 중 문제가 발생했습니다.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  const backHref = activeDogId
    ? `/search?dogId=${encodeURIComponent(activeDogId)}`
    : "/search";

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="hero-panel">
        <div className="space-y-4">
          <p className="eyebrow">Manual Product</p>
          <div className="space-y-3">
            <h1 className="hero-title">검색이 약한 제품은 직접 등록해서 바로 계산에 씁니다</h1>
            <p className="hero-copy">
              자주 먹는 사료와 간식을 한 번만 등록해두면 다음 검색부터 로컬 검수 결과처럼 먼저
              보이게 됩니다.
            </p>
          </div>
        </div>
        <div className="hero-actions">
          <Link className="secondary-cta" href={backHref}>
            검색으로 돌아가기
          </Link>
        </div>
      </section>

      <section className="panel">
        <form className="form-stack" onSubmit={handleSubmit}>
          <div className="field-grid">
            <label className="field-group">
              <span>제품 종류</span>
              <select
                className="field-input"
                value={draft.kind}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    kind: event.target.value as ProductKind,
                  }))
                }
              >
                <option value="food">사료</option>
                <option value="treat">간식</option>
              </select>
            </label>

            <label className="field-group">
              <span>브랜드</span>
              <input
                className="field-input"
                value={draft.brand}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, brand: event.target.value }))
                }
                placeholder="예: ORIJEN, 로얄캐닌"
              />
            </label>
          </div>

          <label className="field-group">
            <span>제품 이름</span>
            <input
              className="field-input"
              value={draft.name}
              onChange={(event) =>
                setDraft((current) => ({ ...current, name: event.target.value }))
              }
              placeholder="예: 오리젠 스몰브리드"
            />
          </label>

          <div className="field-grid">
            <label className="field-group">
              <span>총중량(g)</span>
              <input
                className="field-input"
                inputMode="decimal"
                value={draft.totalWeightG}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, totalWeightG: event.target.value }))
                }
                placeholder="예: 1500"
              />
            </label>

            <label className="field-group">
              <span>총 kcal</span>
              <input
                className="field-input"
                inputMode="decimal"
                value={draft.totalKcal}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, totalKcal: event.target.value }))
                }
                placeholder="예: 5850"
              />
            </label>
          </div>

          <div className="field-grid">
            <label className="field-group">
              <span>100g당 kcal</span>
              <input
                className="field-input"
                inputMode="decimal"
                value={draft.kcalPer100g}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, kcalPer100g: event.target.value }))
                }
                placeholder="사료용"
              />
            </label>

            <label className="field-group">
              <span>1개당 kcal</span>
              <input
                className="field-input"
                inputMode="decimal"
                value={draft.kcalPerPiece}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, kcalPerPiece: event.target.value }))
                }
                placeholder="간식용"
              />
            </label>
          </div>

          <p className="inline-status">{status}</p>

          <div className="hero-actions">
            <button className="primary-cta" type="submit" disabled={isSaving}>
              {isSaving ? "저장 중..." : "제품 등록하고 검색으로 돌아가기"}
            </button>
            <Link className="secondary-cta" href={backHref}>
              취소
            </Link>
          </div>
        </form>
      </section>
    </main>
  );
}
