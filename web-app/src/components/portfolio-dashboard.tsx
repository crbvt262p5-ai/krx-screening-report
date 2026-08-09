"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { hasSupabaseEnv } from "@/lib/env";
import {
  buildPortfolioSnapshot,
  normalizePortfolioRecords,
  type PortfolioPosition,
} from "@/lib/portfolio-dashboard";
import {
  buildScreeningLookup,
  matchScreeningRecord,
  type PortfolioScreeningRecord,
} from "@/lib/portfolio-screening-shared";
import { getValuationOverride } from "@/lib/portfolio-valuation-overrides";
import type { ValuationEnrichmentItem } from "@/lib/portfolio-enrichment";
import type { PortfolioMarketSnapshot } from "@/lib/portfolio-live-market";

type PortfolioDashboardProps = {
  initialRows: PortfolioPosition[];
  screeningRecords: PortfolioScreeningRecord[];
};

type WorkspaceTab = "home" | "overview" | "analysis" | "positions" | "editor";
type ScreenedPortfolioPosition = PortfolioPosition & {
  screening: PortfolioScreeningRecord | null;
};
type AdvisoryPortfolioPosition = PortfolioPosition & {
  screening?: PortfolioScreeningRecord | null;
};
type MarketSnapshotMap = Record<string, PortfolioMarketSnapshot>;
type TradeMode = "buy" | "sell";

const INVESTOR_PROFILE = {
  title: "밸류 우선 운영",
  summary:
    "저평가, 자산가치 재평가, 배당 지속성, 현금흐름 방어력을 우선하고 과열 추세 추격은 낮게 평가합니다.",
  principles: [
    "저PER·저PBR 또는 자산가치 할인 해소 가능성 우선",
    "배당·현금흐름·주주환원 근거가 있으면 가점",
    "고밸류 성장주는 실적 개선 근거 없으면 보수적으로",
    "추세는 매수 근거가 아니라 진입 타이밍 보조 정도로만 사용",
  ],
} as const;

function formatPct(value: number) {
  return `${value.toFixed(2)}%`;
}

function formatGap(actualWeightPct: number, targetWeightPct: number) {
  const gap = targetWeightPct - actualWeightPct;
  return `${gap > 0 ? "+" : ""}${gap.toFixed(2)}%p`;
}

function formatMultiple(value: number | null, suffix = "배") {
  if (value === null) {
    return "미입력";
  }
  return `${value.toFixed(1)}${suffix}`;
}

function formatNumberValue(value: number | null) {
  if (value === null) {
    return "미입력";
  }
  return value.toLocaleString("ko-KR");
}

function formatMetricOrPending(value: number | null, formatter: (input: number | null) => string) {
  if (value === null) {
    return "연동 필요";
  }
  return formatter(value);
}

function formatScreeningScore(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return value.toFixed(1);
}

function formatSignedPct(value: number | null) {
  if (value === null) {
    return "-";
  }
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatCurrency(value: number | null, suffix = "원") {
  if (value === null) {
    return "-";
  }
  return `${Math.round(value).toLocaleString("ko-KR")}${suffix}`;
}

function formatSignedCurrency(value: number | null, suffix = "원") {
  if (value === null) {
    return "-";
  }
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded.toLocaleString("ko-KR")}${suffix}`;
}

function formatThemeCategorySummary(labels: string[]) {
  if (labels.length === 0) {
    return "미분류";
  }
  if (labels.length === 1) {
    return labels[0];
  }
  return `${labels[0]} 외 ${labels.length - 1}개`;
}

function withScreeningFallback(row: PortfolioPosition, screening: PortfolioScreeningRecord | null): PortfolioPosition {
  const valuationOverride = getValuationOverride(row);
  return {
    ...row,
    per: row.per ?? screening?.per ?? valuationOverride?.per ?? null,
    pbr: row.pbr ?? screening?.pbr ?? valuationOverride?.pbr ?? null,
    eps: row.eps ?? screening?.consensusEpsEstimate ?? valuationOverride?.eps ?? null,
    forwardPer: row.forwardPer ?? screening?.forwardPer ?? valuationOverride?.forwardPer ?? null,
  };
}

function hasIdentityUncertainty(row: AdvisoryPortfolioPosition) {
  return (
    row.notes.includes("정확한 법인명 확인 필요") ||
    row.notes.includes("미확인") ||
    (row.marketScope === "해외" && !row.screening && !/^[A-Z][A-Z0-9.\-=]{0,14}$/.test(row.ticker))
  );
}

function screeningLabel(row: AdvisoryPortfolioPosition) {
  if (hasIdentityUncertainty(row)) {
    return "종목 확인 필요";
  }
  if (row.screening?.coreBucket) {
    return row.screening.coreBucket;
  }
  if (row.screening?.recommendationBucket) {
    return row.screening.recommendationBucket;
  }
  return "미연동";
}

function screeningReason(row: AdvisoryPortfolioPosition) {
  return row.screening?.recommendationReasons || "";
}

function hasStrongValueDividendSupport(row: AdvisoryPortfolioPosition) {
  return (
    (row.screening?.valueScore ?? 0) >= 14 ||
    (row.screening?.dividendYieldTrailing ?? 0) >= 4 ||
    (row.pbr ?? row.screening?.pbr ?? 99) <= 0.6 ||
    (row.per ?? row.screening?.per ?? 99) <= 6
  );
}

function isUnscreenedMomentumGrowth(row: AdvisoryPortfolioPosition) {
  return (
    row.marketScope === "해외" &&
    !row.screening &&
    row.styleBucket === "성장" &&
    (row.theme.includes("AI") || row.theme.includes("빅테크") || row.theme.includes("반도체"))
  );
}

function hasValueSupport(row: AdvisoryPortfolioPosition) {
  return (
    (row.per !== null && row.per <= 12) ||
    (row.pbr !== null && row.pbr <= 1.2) ||
    hasStrongValueDividendSupport(row) ||
    row.strategy.includes("Value") ||
    row.strategy.includes("Dividend") ||
    row.theme.includes("금융") ||
    row.theme.includes("지주사") ||
    row.theme.includes("배당") ||
    row.theme.includes("자산")
  );
}

function getScreeningBias(row: AdvisoryPortfolioPosition) {
  let score = 0;

  if (row.screening?.coreBucket === "Value Core") score += 5;
  if (row.screening?.coreBucket === "Growth Core") score -= 1.5;
  if (row.screening?.recommendationBucket === "실매수 검토") score += 3.5;
  if (row.screening?.recommendationBucket === "소액 관찰") score += 1.2;
  if (row.screening?.recommendationBucket === "가치함정 경고") score -= 4.2;
  if (row.screening?.recommendationBucket === "제외") score -= 5.5;
  if (row.screening?.stage === "과열") score -= 2;

  if ((row.screening?.valueScore ?? 0) >= 14) score += 2.6;
  else if ((row.screening?.valueScore ?? 0) >= 10) score += 1.3;

  if ((row.screening?.valueTrapRiskScore ?? 0) >= 2.5) score -= 2.5;
  if (hasIdentityUncertainty(row)) score -= 3.5;

  return score;
}

function getValuationPreferenceScore(row: AdvisoryPortfolioPosition) {
  let score = 0;

  if (row.per !== null) {
    if (row.per <= 8) score += 4.5;
    else if (row.per <= 12) score += 3;
    else if (row.per <= 18) score += 1.2;
    else if (row.per >= 25) score -= 3;
    else if (row.per >= 20) score -= 1.5;
  }

  if (row.pbr !== null) {
    if (row.pbr <= 0.8) score += 3.5;
    else if (row.pbr <= 1.2) score += 2.4;
    else if (row.pbr <= 1.8) score += 0.8;
    else if (row.pbr >= 3) score -= 2.2;
  }

  if (row.forwardPer !== null && row.per !== null) {
    if (row.forwardPer < row.per * 0.9) score += 1.5;
    else if (row.forwardPer > row.per * 1.1) score -= 0.8;
  }

  if (row.styleBucket === "인컴") score += 1;
  if (row.strategy.includes("Value")) score += 2.2;
  if (row.strategy.includes("Dividend")) score += 1.8;
  if (row.theme.includes("지주사") || row.theme.includes("금융") || row.theme.includes("배당")) score += 1.2;
  score += getScreeningBias(row);

  return score;
}

function getHeatPenalty(row: AdvisoryPortfolioPosition) {
  let penalty = 0;
  if (row.trendView.includes("과열")) penalty += 1.8;
  if (row.cycleView.includes("과열")) penalty += 1.6;
  if (row.screening?.stage === "과열") penalty += 2.2;
  if (row.styleBucket === "성장" && !hasValueSupport(row)) penalty += 1.2;
  if ((row.per ?? 0) >= 25 && !row.strategy.includes("Value")) penalty += 1.2;
  return penalty;
}

function getBuyPriorityScore(row: AdvisoryPortfolioPosition) {
  const gap = row.targetWeightPct - row.actualWeightPct;
  const valuationScore = getValuationPreferenceScore(row);
  let score = valuationScore * 2.4;

  if (hasIdentityUncertainty(row)) {
    score -= 8;
  }
  if (row.screening?.recommendationBucket === "제외") {
    score -= 10;
  }
  if (isUnscreenedMomentumGrowth(row)) {
    score -= 9;
  }

  if (gap > 0) {
    score += Math.min(4, gap * 1.5);
  } else {
    score -= Math.min(3, Math.abs(gap) * 1.1);
  }

  if (row.conviction === "핵심") score += 1.2;
  if (row.plannedAction.includes("추가매수")) score += 1;
  if (row.plannedAction.includes("보유")) score += 0.2;
  if ((row.screening?.finalScore ?? 0) >= 28) score += 1.8;
  if (hasStrongValueDividendSupport(row)) score += 4.5;
  if ((row.screening?.dividendYieldTrailing ?? 0) >= 4) score += 2.4;
  if ((row.screening?.returns6mPct ?? 0) <= 30 && (row.screening?.returns6mPct ?? 0) >= -20) score += 1.2;
  score -= getHeatPenalty(row) * 1.6;

  if (!hasValueSupport(row) && row.styleBucket === "성장") {
    score -= 5.2;
  }

  return score;
}

function getTrimPriorityScore(row: AdvisoryPortfolioPosition) {
  const overweight = row.actualWeightPct - row.targetWeightPct;
  let score = getHeatPenalty(row) * 2.2 - getValuationPreferenceScore(row) * 1.6;

  if (hasIdentityUncertainty(row) && overweight > 0) {
    score += 2.4;
  }

  if (overweight > 0) {
    score += Math.min(4, overweight * 1.6);
  }

  if (row.plannedAction.includes("비중축소") || row.plannedAction.includes("정리")) score += 1.4;
  if (row.conviction === "위성") score += 0.8;
  if (row.per !== null && row.per >= 25) score += 1.4;
  if (row.pbr !== null && row.pbr >= 3) score += 1;
  if (row.screening?.recommendationBucket === "가치함정 경고") score += 2.5;
  if (row.screening?.recommendationBucket === "제외") score += 3.2;
  if (hasStrongValueDividendSupport(row)) score -= 5.4;
  if ((row.screening?.dividendYieldTrailing ?? 0) >= 4) score -= 2.6;
  if ((row.screening?.returns6mPct ?? 0) <= 0) score -= 1.6;
  if (row.screening?.recommendationBucket === "소액 관찰") score -= 1.4;
  if (hasValueSupport(row) && row.trendView.includes("확인 필요")) score -= 0.8;

  return score;
}

function buildDecisionSummary(row: AdvisoryPortfolioPosition) {
  const gap = row.actualWeightPct - row.targetWeightPct;
  const valuationScore = getValuationPreferenceScore(row);

  if (hasIdentityUncertainty(row)) {
    if (gap < 0) {
      return `${row.name}은 종목 식별이 불완전해 추가매수 판단보다 먼저 정확한 티커 확인이 필요합니다.`;
    }
    return `${row.name}은 종목 식별이 불완전한 상태라 강한 매수/매도보다 확인 우선 종목으로 보는 편이 맞습니다.`;
  }

  if (row.plannedAction.includes("비중축소") || row.plannedAction.includes("정리")) {
    if (row.screening?.recommendationBucket === "제외" || row.screening?.recommendationBucket === "가치함정 경고") {
      return `${row.name}은 스크리닝에서 ${row.screening.recommendationBucket}로 잡혀, 포트 축소 후보로 보는 근거가 분명합니다.`;
    }
    if (valuationScore <= -2) {
      return `${row.name}은 밸류 부담과 초과 비중이 겹쳐, 비중 축소 의견이 더 설득력 있습니다.`;
    }
    if (row.trendView.includes("과열") || row.cycleView.includes("과열")) {
      return `${row.name}은 과열 구간이지만, 이 화면에서는 추세보다 밸류 부담과 오버웨이트 관리가 핵심 축소 근거입니다.`;
    }
    if (gap > 0) {
      return `${row.name}은 목표보다 ${gap.toFixed(2)}%p 무거워 포트 균형 복귀 목적의 축소 의견입니다.`;
    }
    return `${row.name}은 포트 내 역할 대비 비중이 무거워 보여 관리형 축소 의견입니다.`;
  }

  if (row.plannedAction.includes("추가매수")) {
    if (isUnscreenedMomentumGrowth(row)) {
      return `${row.name}은 언더웨이트여도 현재 로직에서는 모멘텀 성장주로 분류돼, 네 성향 기준 추가매수 우선순위에서 뒤로 밀립니다.`;
    }
    if (row.screening?.coreBucket === "Value Core" && row.screening?.recommendationBucket === "실매수 검토") {
      return `${row.name}은 스크리닝에서도 Value Core 실매수 검토로 잡혀, 네 성향과 가장 맞는 추가매수 후보입니다.`;
    }
    if (valuationScore >= 6) {
      return `${row.name}은 밸류 할인과 포트 역할이 맞물려, 추세보다 가격 메리트 중심의 확대 검토 의견입니다.`;
    }
    if (row.per !== null && row.forwardPer !== null && row.forwardPer < row.per) {
      return `${row.name}은 목표 비중보다 가볍고 선행 밸류가 개선돼 확대 검토 의견입니다.`;
    }
    if (gap < 0) {
      return `${row.name}은 목표보다 ${Math.abs(gap).toFixed(2)}%p 가벼워 비중 복원 목적의 확대 의견입니다.`;
    }
    if (!hasValueSupport(row)) {
      return `${row.name}은 현재 추세보다 밸류 근거가 약해, 확대보다 관찰 쪽이 더 자연스러워 보입니다.`;
    }
    return `${row.name}은 포트 역할 대비 현재 비중이 부족해 보여 추가 검토 의견입니다.`;
  }

  if (row.plannedAction.includes("관찰")) {
    return `${row.name}은 지금 비중 조정보다 추세 확인이 먼저인 관찰 의견입니다.`;
  }

  return `${row.name}은 현재 비중을 급히 움직이기보다 유지 쪽이 더 자연스러운 의견입니다.`;
}

function buildAnalysisVerdict(row: AdvisoryPortfolioPosition) {
  if (hasIdentityUncertainty(row)) {
    return "판단 보류";
  }
  if (row.screening?.recommendationBucket === "제외") {
    return "확대 비추천";
  }
  if (row.screening?.recommendationBucket === "가치함정 경고") {
    return "함정 주의";
  }
  if (row.screening?.coreBucket === "Value Core" && row.screening?.recommendationBucket === "실매수 검토") {
    return "가치 매수 후보";
  }
  if (hasStrongValueDividendSupport(row) && row.targetWeightPct > row.actualWeightPct) {
    return "가치 관찰 강화";
  }
  if (row.actualWeightPct > row.targetWeightPct) {
    return "비중 관리 우선";
  }
  return "중립";
}

function buildCriteriaRows(row: AdvisoryPortfolioPosition) {
  return [
    {
      label: "밸류",
      value:
        row.screening?.valueScore !== null && row.screening?.valueScore !== undefined
          ? `Value ${formatScreeningScore(row.screening.valueScore)}`
          : row.per !== null || row.pbr !== null
            ? `${formatMultiple(row.per)} / ${formatMultiple(row.pbr)}`
            : "근거 약함",
      tone:
        hasStrongValueDividendSupport(row) ? "positive" : (row.screening?.recommendationBucket === "가치함정 경고" ? "negative" : "neutral"),
    },
    {
      label: "배당·주주환원",
      value:
        row.screening?.payoutRatioPct !== null && row.screening?.payoutRatioPct !== undefined
          ? `성향 ${formatPct(row.screening.payoutRatioPct)} · 환원 ${formatScreeningScore(row.screening.shareholderReturnScore)}`
          : row.screening?.dividendYieldTrailing !== null && row.screening?.dividendYieldTrailing !== undefined
            ? `배당 ${formatPct(row.screening.dividendYieldTrailing)}`
          : row.styleBucket === "인컴"
            ? "인컴 성격"
            : "보통",
      tone:
        (row.screening?.shareholderReturnScore ?? 0) >= 2 ||
        (row.screening?.dividendYieldNormalized ?? row.screening?.dividendYieldTrailing ?? 0) >= 4 ||
        row.styleBucket === "인컴"
          ? "positive"
          : "neutral",
    },
    {
      label: "스크리닝 판정",
      value: screeningLabel(row),
      tone:
        row.screening?.recommendationBucket === "제외" || row.screening?.recommendationBucket === "가치함정 경고"
          ? "negative"
          : row.screening?.coreBucket === "Value Core"
            ? "positive"
            : "neutral",
    },
    {
      label: "과열·추격",
      value: row.screening?.stage || row.trendView || "중립",
      tone:
        row.screening?.stage === "과열" || row.trendView.includes("과열")
          ? "negative"
          : row.trendView.includes("확인 필요")
            ? "neutral"
            : "positive",
    },
    {
      label: "비중 상태",
      value:
        row.targetWeightPct > row.actualWeightPct
          ? `언더 ${formatGap(row.actualWeightPct, row.targetWeightPct)}`
          : row.actualWeightPct > row.targetWeightPct
            ? `오버 ${formatGap(row.actualWeightPct, row.targetWeightPct)}`
            : "중립",
      tone:
        row.targetWeightPct > row.actualWeightPct && hasValueSupport(row)
          ? "positive"
          : row.actualWeightPct > row.targetWeightPct
            ? "negative"
            : "neutral",
    },
  ];
}

function shareholderReturnLabel(row: AdvisoryPortfolioPosition) {
  const score = row.screening?.shareholderReturnScore;
  if (score === null || score === undefined) return "확인 필요";
  if (score >= 4) return "강함";
  if (score >= 2) return "양호";
  if (score >= 0.5) return "보통";
  return "약함";
}

function payoutStabilityLabel(row: AdvisoryPortfolioPosition) {
  const score = row.screening?.payoutRepeatabilityScore;
  if (score === null || score === undefined) return "확인 필요";
  if (score >= 2) return "안정";
  if (score >= 0.5) return "보통";
  return "주의";
}

function heatmapSizeClass(weight: number) {
  if (weight >= 8) return "portfolio-map-cell-xl";
  if (weight >= 5) return "portfolio-map-cell-lg";
  if (weight >= 3) return "portfolio-map-cell-md";
  if (weight >= 1.5) return "portfolio-map-cell-sm";
  return "portfolio-map-cell-xs";
}

function heatmapTone(changePct: number | null, weightGap: number) {
  const signal = changePct ?? -weightGap;
  if (signal >= 2) return "heat-gain-strong";
  if (signal >= 0.4) return "heat-gain";
  if (signal <= -2) return "heat-loss-strong";
  if (signal <= -0.4) return "heat-loss";
  return "heat-flat";
}

function parseSavedPositionValue(notes: string) {
  const match = notes.replaceAll(",", "").match(/평가\s*([\d.]+)원/);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

function parseSavedReturnPct(notes: string) {
  const match = notes.match(/수익률\s*(-?[\d.]+)%/);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

function buildWeaknessLabel(row: AdvisoryPortfolioPosition) {
  if (hasIdentityUncertainty(row)) {
    return "정확한 종목 식별이 먼저 필요합니다.";
  }
  if (row.screening?.recommendationBucket === "제외") {
    return "스크리닝에서 제외되어 신규 확대 근거가 약합니다.";
  }
  if (row.screening?.recommendationBucket === "가치함정 경고") {
    return "저평가처럼 보여도 함정 가능성을 먼저 점검해야 합니다.";
  }
  if (isUnscreenedMomentumGrowth(row)) {
    return "성장/모멘텀 스토리 대비 네 성향과 맞는 가치 근거가 약합니다.";
  }
  if ((row.screening?.dividendYieldTrailing ?? 0) < 1 && !hasStrongValueDividendSupport(row)) {
    return "배당·현금흐름 방어 근거가 약합니다.";
  }
  return "핵심 반대 근거는 약하지만, 확신을 줄 만한 결정적 근거도 더 필요합니다.";
}

function buildChecklist(row: AdvisoryPortfolioPosition) {
  if (hasIdentityUncertainty(row)) {
    return "법인명/티커 확정";
  }
  if (row.screening?.recommendationBucket === "제외") {
    return "과열 해소 여부 확인";
  }
  if (row.screening?.recommendationBucket === "가치함정 경고") {
    return "함정 사유 재검토";
  }
  if (hasStrongValueDividendSupport(row) && row.targetWeightPct > row.actualWeightPct) {
    return "실적/배당 유지 확인 후 분할";
  }
  if (row.actualWeightPct > row.targetWeightPct) {
    return "비중 정상화 여부 점검";
  }
  return "근거 보강 후 유지 판단";
}

function buildActionReasonTags(row: AdvisoryPortfolioPosition) {
  const tags: string[] = [];
  const underweight = row.targetWeightPct - row.actualWeightPct;
  const overweight = row.actualWeightPct - row.targetWeightPct;

  if (hasIdentityUncertainty(row)) tags.push("심볼 확인");
  if (row.per !== null && row.per <= 10) tags.push("저PER");
  if (row.pbr !== null && row.pbr <= 1) tags.push("저PBR");
  if (row.forwardPer !== null && row.per !== null && row.forwardPer < row.per * 0.9) tags.push("이익 개선");
  if ((row.screening?.dividendYieldTrailing ?? 0) >= 4 || row.styleBucket === "인컴") tags.push("배당 방어");
  if (underweight > 0.4) tags.push("목표 미달");
  if (overweight > 0.4) tags.push("목표 초과");
  if (row.trendView.includes("과열") || row.cycleView.includes("과열") || row.screening?.stage === "과열") tags.push("과열 관리");
  if (row.screening?.recommendationBucket === "가치함정 경고") tags.push("함정 주의");
  if (row.screening?.recommendationBucket === "제외") tags.push("확대 비추천");
  if (row.trendView.includes("확인 필요")) tags.push("추세 확인");

  return [...new Set(tags)].slice(0, 3);
}

function buildPortfolioNarrative(
  rows: ScreenedPortfolioPosition[],
  snapshot: ReturnType<typeof buildPortfolioSnapshot>,
  buyCandidates: ScreenedPortfolioPosition[],
  trimCandidates: ScreenedPortfolioPosition[],
) {
  const topTheme = snapshot.themeMix[0];
  const topTrim = trimCandidates[0];
  const topBuy = buyCandidates[0];
  const narratives: string[] = [];

  if (topTheme) {
    narratives.push(`현재 최대 테마는 ${topTheme.label}로 실제 비중 ${formatPct(topTheme.actualWeightPct)}입니다.`);
  }
  if (snapshot.topFiveWeight > 35) {
    narratives.push(`상위 5종목 비중이 ${formatPct(snapshot.topFiveWeight)}로 높아 종목 집중 관리가 필요합니다.`);
  } else {
    narratives.push(`상위 5종목 비중이 ${formatPct(snapshot.topFiveWeight)}라 집중도는 관리 가능한 범위입니다.`);
  }
  narratives.push(`국내/해외 비중은 ${formatPct(snapshot.domesticWeight)} / ${formatPct(snapshot.overseasWeight)}입니다.`);
  if (topTrim) {
    narratives.push(`${topTrim.name}은 추세 때문이 아니라 밸류 부담 또는 오버웨이트 관리 차원에서 축소 후보로 보입니다.`);
  }
  if (topBuy) {
    narratives.push(`${topBuy.name}은 목표 미달폭보다 밸류 근거가 더 탄탄해 추가 검토 1순위 후보입니다.`);
  }
  const valuationCoverage = rows.filter(
    (row) => row.per !== null || row.pbr !== null || row.forwardPer !== null || row.eps !== null,
  ).length;
  narratives.push(`밸류 지표가 입력된 종목은 ${valuationCoverage}개로, 이 숫자가 많을수록 의견 설명의 설득력이 올라갑니다.`);
  const screeningCoverage = rows.filter((row) => row.screening !== null).length;
  narratives.push(`스크리닝 시스템과 연결된 종목은 ${screeningCoverage}개이며, 국내 종목 의견은 이 결과를 우선 반영합니다.`);
  return narratives;
}

function buildDonutStyle(items: Array<{ actualWeightPct: number }>, colors: string[]) {
  const total = items.reduce((sum, item) => sum + item.actualWeightPct, 0);
  if (!total) {
    return { background: "conic-gradient(#dbe6f6 0deg 360deg)" };
  }

  let current = 0;
  const stops = items.map((item, index) => {
    const start = current;
    const sweep = (item.actualWeightPct / total) * 360;
    current += sweep;
    return `${colors[index % colors.length]} ${start}deg ${current}deg`;
  });

  return { background: `conic-gradient(${stops.join(", ")})` };
}

function getRowMarketTimeZone(row: AdvisoryPortfolioPosition) {
  if (row.marketScope === "국내" || row.country === "한국") {
    return "Asia/Seoul";
  }
  if (row.country === "일본" || row.ticker.endsWith(".T")) {
    return "Asia/Tokyo";
  }
  return "America/New_York";
}

function getMinutesInTimeZone(date: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    weekday: "short",
  }).formatToParts(date);

  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? "0");
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? "0");
  const weekday = parts.find((part) => part.type === "weekday")?.value ?? "Mon";

  return {
    minutes: hour * 60 + minute,
    weekday,
  };
}

function buildMarketPhaseLabel(row: AdvisoryPortfolioPosition, date: Date) {
  const timeZone = getRowMarketTimeZone(row);
  const { minutes, weekday } = getMinutesInTimeZone(date, timeZone);
  const isWeekend = weekday === "Sat" || weekday === "Sun";

  if (isWeekend) {
    if (timeZone === "America/New_York") return "미국 휴장";
    if (timeZone === "Asia/Tokyo") return "일본 휴장";
    return "국내 휴장";
  }

  if (timeZone === "Asia/Seoul") {
    if (minutes < 9 * 60) return "국내 개장 전";
    if (minutes < 15 * 60 + 30) return "국내 장중";
    return "국내 장마감";
  }

  if (timeZone === "Asia/Tokyo") {
    if (minutes < 9 * 60) return "일본 개장 전";
    if (minutes < 15 * 60) return "일본 장중";
    return "일본 장마감";
  }

  if (minutes < 4 * 60) return "미국 장마감";
  if (minutes < 9 * 60 + 30) return "미국 프리마켓";
  if (minutes < 16 * 60) return "미국 장중";
  if (minutes < 20 * 60) return "미국 애프터마켓";
  return "미국 장마감";
}

function sortPnlEntries(entries: Array<{ label: string; value: number }>) {
  return [...entries].sort((left, right) => right.value - left.value);
}

export function PortfolioDashboard({ initialRows, screeningRecords }: PortfolioDashboardProps) {
  const usesCloudStorage = hasSupabaseEnv();
  const [rows, setRows] = useState(initialRows);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("home");
  const [query, setQuery] = useState("");
  const [scopeFilter, setScopeFilter] = useState("전체");
  const [actionFilter, setActionFilter] = useState("전체");
  const [tabFilter, setTabFilter] = useState("전체");
  const [sortKey, setSortKey] = useState("actual_desc");
  const [selectedRowId, setSelectedRowId] = useState(initialRows[0]?.rowId ?? "");
  const initialLookup = buildScreeningLookup(screeningRecords);
  const [draft, setDraft] = useState<PortfolioPosition | null>(
    initialRows[0] ? withScreeningFallback(initialRows[0], matchScreeningRecord(initialRows[0], initialLookup)) : null,
  );
  const [isSavingFile, setIsSavingFile] = useState(false);
  const [isEnrichingValuation, setIsEnrichingValuation] = useState(false);
  const [lastEnrichmentItems, setLastEnrichmentItems] = useState<ValuationEnrichmentItem[]>([]);
  const [marketSnapshots, setMarketSnapshots] = useState<MarketSnapshotMap>({});
  const [marketFetchedAt, setMarketFetchedAt] = useState<string | null>(null);
  const [tradeMode, setTradeMode] = useState<TradeMode>("buy");
  const [tradeWeightDelta, setTradeWeightDelta] = useState("0.00");
  const [tradeMemo, setTradeMemo] = useState("");
  const [statusMessage, setStatusMessage] = useState(
    usesCloudStorage
      ? "현재 포트를 불러왔어요. 수정 후 클라우드 저장하면 배포 환경에서도 그대로 유지됩니다."
      : "현재 포트 CSV를 기본으로 불러왔어요. 엑셀이나 CSV를 올리면 바로 화면이 바뀝니다.",
  );
  const deferredQuery = useDeferredValue(query);
  const screeningLookup = useMemo(() => buildScreeningLookup(screeningRecords), [screeningRecords]);
  const displayRows = useMemo<ScreenedPortfolioPosition[]>(
    () => {
      const screenedRows = rows.map((row) => {
        const screening = matchScreeningRecord(row, screeningLookup);
        return {
          ...withScreeningFallback(row, screening),
          screening,
        };
      });
      const hasLiveValues = screenedRows.some((row) =>
        Number.isFinite(marketSnapshots[row.rowId]?.estimatedHoldingValueKrw),
      );

      if (!hasLiveValues) {
        return screenedRows;
      }

      const resolvedValues = screenedRows.map((row) =>
        marketSnapshots[row.rowId]?.estimatedHoldingValueKrw ?? parseSavedPositionValue(row.notes) ?? 0,
      );
      const totalValue = resolvedValues.reduce((sum, value) => sum + value, 0);
      if (totalValue <= 0) {
        return screenedRows;
      }

      return screenedRows.map((row, index) => ({
        ...row,
        actualWeightPct: (resolvedValues[index] / totalValue) * 100,
      }));
    },
    [marketSnapshots, rows, screeningLookup],
  );

  const filteredRows = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLowerCase();

    const nextRows = displayRows.filter((row) => {
      const matchesQuery =
        !normalizedQuery ||
        `${row.name} ${row.ticker} ${row.theme} ${row.strategy}`.toLowerCase().includes(normalizedQuery);
      const matchesScope = scopeFilter === "전체" || row.marketScope === scopeFilter;
      const matchesAction = actionFilter === "전체" || row.plannedAction === actionFilter;
      const matchesTab =
        tabFilter === "전체" ||
        (tabFilter === "핵심 보유" && row.conviction === "핵심") ||
        (tabFilter === "추가매수" && row.plannedAction === "추가매수 검토") ||
        (tabFilter === "비중축소" && row.plannedAction === "비중축소 검토") ||
        (tabFilter === "관찰" && row.plannedAction === "보유/관찰");
      return matchesQuery && matchesScope && matchesAction && matchesTab;
    });

    nextRows.sort((left, right) => {
      const leftGap = left.targetWeightPct - left.actualWeightPct;
      const rightGap = right.targetWeightPct - right.actualWeightPct;

      switch (sortKey) {
        case "target_desc":
          return right.targetWeightPct - left.targetWeightPct;
        case "gap_desc":
          return rightGap - leftGap;
        case "gap_asc":
          return leftGap - rightGap;
        case "name_asc":
          return left.name.localeCompare(right.name, "ko");
        case "action":
          return left.plannedAction.localeCompare(right.plannedAction, "ko");
        case "actual_desc":
        default:
          return right.actualWeightPct - left.actualWeightPct;
      }
    });

    return nextRows;
  }, [actionFilter, deferredQuery, displayRows, scopeFilter, sortKey, tabFilter]);

  const snapshot = useMemo(() => buildPortfolioSnapshot(displayRows), [displayRows]);
  const quickTabs = ["전체", "핵심 보유", "추가매수", "비중축소", "관찰"];
  const workspaceTabs = [
    { key: "overview", label: "개요", description: "요약과 리밸런싱 우선순위" },
    { key: "analysis", label: "분석", description: "비중 사유와 인사이트" },
    { key: "positions", label: "종목", description: "검색, 필터, 종목 비교" },
    { key: "editor", label: "편집", description: "선택 종목 상세 수정" },
  ] as const;
  const selectedRow =
    displayRows.find((row) => row.rowId === selectedRowId) ??
    displayRows[0] ??
    null;

  function actionTone(action: string) {
    if (action === "추가매수 검토") {
      return "buy";
    }
    if (action === "비중축소 검토" || action === "정리 검토") {
      return "trim";
    }
    if (action === "보유/관찰") {
      return "watch";
    }
    return "hold";
  }

  function selectRow(row: ScreenedPortfolioPosition, nextTab: "positions" | "editor" = "editor") {
    setSelectedRowId(row.rowId);
    const baseRow = rows.find((item) => item.rowId === row.rowId) ?? null;
    setDraft(baseRow ? withScreeningFallback(baseRow, row.screening) : null);
    setWorkspaceTab(nextTab);
  }

  async function handleUploadFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const { read, utils } = await import("xlsx");
      const buffer = await file.arrayBuffer();
      const workbook = read(buffer, { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const records = utils.sheet_to_json<Record<string, unknown>>(sheet, {
        defval: "",
        raw: false,
      });
      const nextRows = normalizePortfolioRecords(records);

      if (nextRows.length === 0) {
        setStatusMessage("읽을 수 있는 행이 없어요. 첫 번째 시트와 헤더를 다시 확인해 주세요.");
        return;
      }

      setRows(nextRows);
      setSelectedRowId(nextRows[0]?.rowId ?? "");
      setDraft(
        nextRows[0]
          ? withScreeningFallback(nextRows[0], matchScreeningRecord(nextRows[0], screeningLookup))
          : null,
      );
      setStatusMessage(`${file.name} 파일에서 ${nextRows.length}개 종목을 불러왔습니다.`);
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "파일을 읽는 중 문제가 발생했습니다.",
      );
    } finally {
      event.target.value = "";
    }
  }

  function handleDownloadTemplate() {
    const exportRows = rows.map((row) => ({
      ticker: row.ticker,
      name: row.name,
      market_scope: row.marketScope,
      asset_class: row.assetClass,
      country: row.country,
      theme: row.theme,
      theme_category: row.themeCategory,
      sub_theme: row.subTheme,
      strategy: row.strategy,
      style_bucket: row.styleBucket,
      trend_view: row.trendView,
      cycle_view: row.cycleView,
      conviction: row.conviction,
      fx_exposure: row.fxExposure,
      timing_view: row.timingView,
      actual_weight_pct: row.actualWeightPct,
      target_weight_pct: row.targetWeightPct,
      per: row.per,
      pbr: row.pbr,
      eps: row.eps,
      forward_per: row.forwardPer,
      planned_action: row.plannedAction,
      notes: row.notes,
    }));

    void (async () => {
      const { utils, writeFile } = await import("xlsx");
      const worksheet = utils.json_to_sheet(exportRows);
      const workbook = utils.book_new();
      utils.book_append_sheet(workbook, worksheet, "portfolio");
      writeFile(workbook, "portfolio_dashboard_template.xlsx");
      setStatusMessage("현재 화면 기준으로 엑셀 템플릿을 내려받았습니다.");
    })().catch((error: unknown) => {
      setStatusMessage(error instanceof Error ? error.message : "엑셀 파일 생성 중 문제가 발생했습니다.");
    });
  }

  function handleDraftChange<K extends keyof PortfolioPosition>(key: K, value: PortfolioPosition[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  function buildTradeMemoLine(mode: TradeMode, delta: number, memo: string) {
    const stamp = new Date().toLocaleDateString("ko-KR");
    const actionLabel = mode === "buy" ? "매수" : "매도";
    const deltaLabel = `${mode === "buy" ? "+" : "-"}${delta.toFixed(2)}%p`;
    const memoTail = memo.trim() ? ` · ${memo.trim()}` : "";
    return `[${stamp}] ${actionLabel} 반영 ${deltaLabel}${memoTail}`;
  }

  function updateDraftForTrade(mode: TradeMode, delta: number, memo: string) {
    if (!draft) {
      return;
    }

    const signedDelta = mode === "buy" ? delta : -delta;
    const nextActualWeightPct = Math.max(0, Number((draft.actualWeightPct + signedDelta).toFixed(2)));
    const nextNotes = [draft.notes?.trim(), buildTradeMemoLine(mode, delta, memo)].filter(Boolean).join("\n");
    const nextPlannedAction =
      nextActualWeightPct === 0
        ? "정리 검토"
        : nextActualWeightPct < draft.targetWeightPct
          ? "추가매수 검토"
          : nextActualWeightPct > draft.targetWeightPct
            ? "비중축소 검토"
            : "보유/관찰";

    setDraft({
      ...draft,
      actualWeightPct: nextActualWeightPct,
      plannedAction: nextPlannedAction,
      notes: nextNotes,
    });

    setTradeWeightDelta("0.00");
    setTradeMemo("");
    setStatusMessage(`${draft.name} 오늘 매매 내용을 드래프트에 반영했습니다. 저장하면 포트에 확정됩니다.`);
  }

  function handleApplyTradeAdjustment() {
    const delta = Number(tradeWeightDelta);
    if (!draft || !Number.isFinite(delta) || delta <= 0) {
      setStatusMessage("오늘 매매 반영 값이 비어 있어요. 비중 변화를 0보다 크게 입력해 주세요.");
      return;
    }

    updateDraftForTrade(tradeMode, delta, tradeMemo);
  }

  function handleMarkFullySold() {
    if (!draft) {
      return;
    }

    const stamp = new Date().toLocaleDateString("ko-KR");
    const nextNotes = [draft.notes?.trim(), `[${stamp}] 전량 매도 반영`].filter(Boolean).join("\n");

    setDraft({
      ...draft,
      actualWeightPct: 0,
      plannedAction: "정리 검토",
      notes: nextNotes,
    });
    setTradeWeightDelta("0.00");
    setTradeMemo("");
    setStatusMessage(`${draft.name} 전량 매도 내용을 드래프트에 반영했습니다. 저장하면 포트에 확정됩니다.`);
  }

  async function handleEnrichValuation() {
    setIsEnrichingValuation(true);

    try {
      const response = await fetch("/api/portfolio/enrich", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ rows }),
      });

      const payload = (await response.json().catch(() => null)) as
        | {
            ok?: boolean;
            rows?: PortfolioPosition[];
            items?: ValuationEnrichmentItem[];
            summary?: {
              updatedCount: number;
              unchangedCount: number;
              skippedCount: number;
              unresolvedCount: number;
            };
            error?: string;
          }
        | null;

      if (!response.ok || !payload?.rows || !payload.summary) {
        throw new Error(payload?.error ?? "밸류 자동 채우기 중 문제가 발생했습니다.");
      }

      setLastEnrichmentItems(payload.items ?? []);
      setRows(payload.rows);

      const nextSelectedRow =
        payload.rows.find((row) => row.rowId === selectedRowId) ??
        payload.rows[0] ??
        null;

      setSelectedRowId(nextSelectedRow?.rowId ?? "");
      setDraft(
        nextSelectedRow
          ? withScreeningFallback(nextSelectedRow, matchScreeningRecord(nextSelectedRow, screeningLookup))
          : null,
      );

      let persistenceTail = "";
      if (payload.summary.updatedCount > 0) {
        setIsSavingFile(true);
        try {
          const persistence = await persistRows(payload.rows);
          persistenceTail =
            persistence === "supabase"
              ? " 클라우드 저장까지 완료했습니다."
              : " 로컬 파일 저장까지 완료했습니다.";
        } finally {
          setIsSavingFile(false);
        }
      }

      const unresolvedNames = (payload.items ?? [])
        .filter((item) => item.status === "unresolved")
        .slice(0, 3)
        .map((item) => item.name);

      const unresolvedTail =
        unresolvedNames.length > 0
          ? ` 자동 연결이 어려운 종목: ${unresolvedNames.join(", ")}${payload.summary.unresolvedCount > unresolvedNames.length ? " 외" : ""}.`
          : "";

      setStatusMessage(
        `밸류 자동 채우기 완료. 업데이트 ${payload.summary.updatedCount}개, 유지 ${payload.summary.unchangedCount}개, ETF 스킵 ${payload.summary.skippedCount}개, 미해결 ${payload.summary.unresolvedCount}개.${unresolvedTail}${persistenceTail}`,
      );
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : "밸류 자동 채우기 중 문제가 발생했습니다.",
      );
    } finally {
      setIsEnrichingValuation(false);
    }
  }

  function handleApplyDraft() {
    if (!draft) {
      return;
    }

    setRows((current) =>
      current.map((row) =>
        row.rowId === draft.rowId
          ? {
              ...draft,
              actualWeightPct: Number(draft.actualWeightPct),
              targetWeightPct: Number(draft.targetWeightPct),
            }
          : row,
      ),
    );
    setStatusMessage(`${draft.name} 수정 내용을 화면에 반영했습니다.`);
  }

  async function handleSaveToFile() {
    if (!draft) {
      return;
    }

    const nextRows = rows.map((row) =>
      row.rowId === draft.rowId
        ? {
            ...draft,
            actualWeightPct: Number(draft.actualWeightPct),
            targetWeightPct: Number(draft.targetWeightPct),
          }
        : row,
    );

    setRows(nextRows);
    setIsSavingFile(true);
    try {
      const response = await fetch("/api/portfolio/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ rows: nextRows }),
      });

      const payload = (await response.json().catch(() => null)) as
        | {
            ok?: boolean;
            persistence?: "supabase" | "csv";
            error?: string;
          }
        | null;

      if (!response.ok) {
        throw new Error(payload?.error ?? "저장 중 문제가 발생했습니다.");
      }

      setStatusMessage(
        payload?.persistence === "supabase"
          ? `${draft.name} 수정 내용을 Supabase에 저장했습니다. 배포 후에도 유지됩니다.`
          : `${draft.name} 수정 내용을 로컬 CSV에 저장했습니다.`,
      );
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "저장 중 문제가 발생했습니다.");
    } finally {
      setIsSavingFile(false);
    }
  }

  async function persistRows(nextRows: PortfolioPosition[]) {
    const response = await fetch("/api/portfolio/save", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ rows: nextRows }),
    });

    const payload = (await response.json().catch(() => null)) as
      | {
          ok?: boolean;
          persistence?: "supabase" | "csv";
          error?: string;
        }
      | null;

    if (!response.ok) {
      throw new Error(payload?.error ?? "저장 중 문제가 발생했습니다.");
    }

    return payload?.persistence ?? (usesCloudStorage ? "supabase" : "csv");
  }

  const topThemes = snapshot.themeMix.slice(0, 4);
  const topActions = snapshot.actionMix.slice(0, 4);
  const topThemeSummary = topThemes
    .map((item) => `${item.label} ${formatPct(item.actualWeightPct)}`)
    .join(" · ");
  const topThemeCategories = snapshot.themeCategoryMix.slice(0, 3);
  const topThemeCategorySummary = formatThemeCategorySummary(topThemeCategories.map((item) => item.label));
  const domesticVsOverseas = `${formatPct(snapshot.domesticWeight)} / ${formatPct(snapshot.overseasWeight)}`;
  const screeningConnectedCount = displayRows.filter((row) => row.screening !== null).length;
  const valuationConnectedCount = displayRows.filter(
    (row) => row.per !== null || row.pbr !== null || row.eps !== null || row.forwardPer !== null,
  ).length;
  const unresolvedEnrichmentItems = lastEnrichmentItems.filter((item) => item.status === "unresolved");
  const buyCandidates = useMemo(
    () =>
      [...displayRows]
        .filter(
          (row) =>
            (row.targetWeightPct > row.actualWeightPct || row.plannedAction.includes("추가매수")) &&
            !hasIdentityUncertainty(row) &&
            row.screening?.recommendationBucket !== "제외",
        )
        .sort((left, right) => getBuyPriorityScore(right) - getBuyPriorityScore(left))
        .slice(0, 5),
    [displayRows],
  );
  const trimCandidates = useMemo(
    () =>
      [...displayRows]
        .filter((row) => row.actualWeightPct > row.targetWeightPct || row.plannedAction.includes("비중축소") || row.plannedAction.includes("정리"))
        .sort((left, right) => getTrimPriorityScore(right) - getTrimPriorityScore(left))
        .slice(0, 5),
    [displayRows],
  );
  const reviewCandidates = useMemo(
    () =>
      [...displayRows]
        .filter((row) => hasIdentityUncertainty(row) || row.trendView.includes("확인 필요"))
        .sort((left, right) => Math.abs(right.actualWeightPct - right.targetWeightPct) - Math.abs(left.actualWeightPct - left.targetWeightPct))
        .slice(0, 4),
    [displayRows],
  );
  const watchCandidates = useMemo(
    () =>
      [...displayRows]
        .filter(
          (row) =>
            row.plannedAction.includes("관찰") ||
            (!buyCandidates.some((item) => item.rowId === row.rowId) &&
              !trimCandidates.some((item) => item.rowId === row.rowId) &&
              !reviewCandidates.some((item) => item.rowId === row.rowId) &&
              (row.screening?.recommendationBucket === "소액 관찰" || row.styleBucket === "인컴")),
        )
        .slice(0, 4),
    [buyCandidates, displayRows, reviewCandidates, trimCandidates],
  );
  const analysisThemeMix = snapshot.themeMix.slice(0, 5);
  const analysisRegionMix = snapshot.regionMix.slice(0, 3);
  const themeChartStyle = buildDonutStyle(analysisThemeMix, ["#1f6feb", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"]);
  const regionChartStyle = buildDonutStyle(analysisRegionMix, ["#174ea6", "#06b6d4", "#94a3b8"]);
  const portfolioNarrative = buildPortfolioNarrative(displayRows, snapshot, buyCandidates, trimCandidates);
  const marketClock = marketFetchedAt ? new Date(marketFetchedAt) : new Date();
  const portfolioDayPnlKrw = Object.values(marketSnapshots).reduce(
    (sum, item) => sum + (item.estimatedDayPnlKrw ?? 0),
    0,
  );
  const marketCoverageCount = Object.values(marketSnapshots).filter((item) => item.currentPrice !== null).length;
  const dayPnlRegionMix = useMemo(() => {
    const totals = new Map<string, number>();

    for (const row of displayRows) {
      const pnl = marketSnapshots[row.rowId]?.estimatedDayPnlKrw ?? null;
      if (pnl === null) {
        continue;
      }
      totals.set(row.marketScope, (totals.get(row.marketScope) ?? 0) + pnl);
    }

    return sortPnlEntries(
      [...totals.entries()].map(([label, value]) => ({ label, value: Math.round(value) })),
    );
  }, [displayRows, marketSnapshots]);
  const dayPnlThemeMix = useMemo(() => {
    const totals = new Map<string, number>();

    for (const row of displayRows) {
      const pnl = marketSnapshots[row.rowId]?.estimatedDayPnlKrw ?? null;
      if (pnl === null) {
        continue;
      }
      totals.set(row.theme, (totals.get(row.theme) ?? 0) + pnl);
    }

    return sortPnlEntries(
      [...totals.entries()].map(([label, value]) => ({ label, value: Math.round(value) })),
    );
  }, [displayRows, marketSnapshots]);
  const bestThemePnl = dayPnlThemeMix[0] ?? null;
  const weakestThemePnl = [...dayPnlThemeMix].reverse().find((item) => item.value < 0) ?? null;
  const domesticDayPnl = dayPnlRegionMix.find((item) => item.label === "국내")?.value ?? null;
  const overseasDayPnl = dayPnlRegionMix.find((item) => item.label === "해외")?.value ?? null;
  const gatewayPortfolio = useMemo(() => {
    let totalValue = 0;
    let totalPrincipal = 0;
    let domesticValue = 0;
    let overseasValue = 0;

    for (const row of displayRows) {
      const savedValue = parseSavedPositionValue(row.notes);
      const liveValue = marketSnapshots[row.rowId]?.estimatedHoldingValueKrw ?? null;
      const resolvedValue = liveValue ?? savedValue ?? 0;
      const returnPct = parseSavedReturnPct(row.notes);
      const principal =
        savedValue !== null && returnPct !== null && returnPct > -99.9
          ? savedValue / (1 + returnPct / 100)
          : resolvedValue;

      totalValue += resolvedValue;
      totalPrincipal += principal;
      if (row.marketScope === "국내") domesticValue += resolvedValue;
      if (row.marketScope === "해외") overseasValue += resolvedValue;
    }

    return {
      totalValue: Math.round(totalValue),
      totalPrincipal: Math.round(totalPrincipal),
      totalProfit: Math.round(totalValue - totalPrincipal),
      totalReturnPct: totalPrincipal > 0 ? ((totalValue - totalPrincipal) / totalPrincipal) * 100 : 0,
      domesticValue: Math.round(domesticValue),
      overseasValue: Math.round(overseasValue),
    };
  }, [displayRows, marketSnapshots]);

  useEffect(() => {
    let cancelled = false;

    async function loadMarketSnapshots() {
      try {
        const response = await fetch("/api/portfolio/market-snapshot", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ rows }),
        });

        const payload = (await response.json().catch(() => null)) as
          | {
              ok?: boolean;
              snapshots?: PortfolioMarketSnapshot[];
              fetchedAt?: string;
            }
          | null;

        if (!response.ok || !payload?.ok || !payload.snapshots) {
          return;
        }

        if (cancelled) {
          return;
        }

        setMarketSnapshots(
          Object.fromEntries(payload.snapshots.map((item) => [item.rowId, item])),
        );
        setMarketFetchedAt(payload.fetchedAt ?? new Date().toISOString());
      } catch {
        if (!cancelled) {
          setMarketFetchedAt(new Date().toISOString());
        }
      }
    }

    void loadMarketSnapshots();
    const timer = window.setInterval(() => {
      void loadMarketSnapshots();
    }, 60_000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [rows]);

  function getMarketSnapshot(rowId: string) {
    return marketSnapshots[rowId] ?? null;
  }

  function buildMarketLine(row: AdvisoryPortfolioPosition) {
    const snapshot = getMarketSnapshot(row.rowId);
    const phaseLabel = buildMarketPhaseLabel(row, marketClock);

    if (!snapshot || snapshot.currentPrice === null) {
      return `${phaseLabel} · 실시간 시세 대기 중`;
    }

    const priceText =
      snapshot.currency === "KRW" || !snapshot.currency
        ? formatCurrency(snapshot.currentPrice)
        : `${snapshot.currentPrice.toLocaleString("en-US")} ${snapshot.currency}`.trim();
    const fxText =
      snapshot.currency && snapshot.currency !== "KRW"
        ? snapshot.fxRateToKrw !== null
          ? `환율 ${formatCurrency(snapshot.fxRateToKrw)}`
          : "환율 대기"
        : "원화 자산";
    const pnlText =
      snapshot.estimatedDayPnlKrw !== null
        ? `추정 일간 ${formatSignedCurrency(snapshot.estimatedDayPnlKrw)}`
        : "일간 손익 계산 대기";

    return `${phaseLabel} · ${priceText} · ${formatSignedPct(snapshot.changePct)} · ${fxText} · ${pnlText}`;
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      {workspaceTab === "home" ? (
        <section className="gateway-shell">
          <div className="gateway-topbar">
            <div>
              <p className="section-kicker">MY PORTFOLIO</p>
              <h1>내 투자자산</h1>
            </div>
            <div className="gateway-top-actions">
              <label className="gateway-upload portfolio-upload">
                캡처·엑셀 업데이트
                <input className="sr-only" type="file" accept=".xlsx,.xls,.csv" onChange={handleUploadFile} />
              </label>
              <button className="gateway-detail-button" type="button" onClick={() => setWorkspaceTab("overview")}>
                상세 대시보드 보기
              </button>
            </div>
          </div>

          <div className="gateway-balance">
            <span>총 평가자산</span>
            <strong>{formatCurrency(gatewayPortfolio.totalValue)}</strong>
            <div>
              <b className={gatewayPortfolio.totalProfit < 0 ? "loss-text" : "gain-text"}>
                {formatSignedCurrency(gatewayPortfolio.totalProfit)} ({formatSignedPct(gatewayPortfolio.totalReturnPct)})
              </b>
              <small>
                {marketFetchedAt
                  ? `시세 갱신 ${new Date(marketFetchedAt).toLocaleTimeString("ko-KR")}`
                  : "최근 보유 캡처 평가금액 기준"}
              </small>
            </div>
          </div>

          <div className="gateway-metric-grid">
            <article>
              <span>추정 투자원금</span>
              <strong>{formatCurrency(gatewayPortfolio.totalPrincipal)}</strong>
            </article>
            <article>
              <span>오늘 손익</span>
              <strong className={portfolioDayPnlKrw < 0 ? "loss-text" : "gain-text"}>
                {marketCoverageCount > 0 ? formatSignedCurrency(portfolioDayPnlKrw) : "시세 대기"}
              </strong>
            </article>
            <article>
              <span>국내 자산</span>
              <strong>{formatCurrency(gatewayPortfolio.domesticValue)}</strong>
              <small>{formatPct(snapshot.domesticWeight)}</small>
            </article>
            <article>
              <span>해외 자산</span>
              <strong>{formatCurrency(gatewayPortfolio.overseasValue)}</strong>
              <small>{formatPct(snapshot.overseasWeight)}</small>
            </article>
          </div>

          <div className="gateway-allocation-track" aria-label="국내 해외 자산 배분">
            <i style={{ width: `${snapshot.domesticWeight}%` }} />
            <b style={{ width: `${snapshot.overseasWeight}%` }} />
          </div>

          <div className="gateway-lower-grid">
            <section className="gateway-holdings">
              <div className="gateway-section-head">
                <strong>상위 보유</strong>
                <span>전체 {snapshot.holdingCount}종목</span>
              </div>
              {displayRows.slice(0, 4).map((row, index) => (
                <button key={`gateway-${row.rowId}`} type="button" onClick={() => selectRow(row)}>
                  <span className="gateway-rank">{index + 1}</span>
                  <div>
                    <strong>{row.name}</strong>
                    <small>{row.theme} · {row.marketScope}</small>
                  </div>
                  <b>{formatPct(row.actualWeightPct)}</b>
                </button>
              ))}
            </section>

            <section className="gateway-checkup">
              <div className="gateway-section-head">
                <strong>포트 점검</strong>
                <span>현재 기준</span>
              </div>
              <button type="button" onClick={() => setWorkspaceTab("analysis")}>
                <div>
                  <span>가장 큰 테마</span>
                  <strong>{topThemes[0]?.label ?? "미분류"}</strong>
                </div>
                <b>{topThemes[0] ? formatPct(topThemes[0].actualWeightPct) : "-"}</b>
              </button>
              <button type="button" onClick={() => setWorkspaceTab("analysis")}>
                <div>
                  <span>비중축소 점검</span>
                  <strong>{trimCandidates.length}종목</strong>
                </div>
                <b>확인</b>
              </button>
              <button type="button" onClick={() => setWorkspaceTab("positions")}>
                <div>
                  <span>데이터 확인 필요</span>
                  <strong>{Math.max(0, displayRows.length - screeningConnectedCount)}종목</strong>
                </div>
                <b>보기</b>
              </button>
            </section>
          </div>
        </section>
      ) : (
      <section className="hero-panel">
        <div className="space-y-3">
          <p className="eyebrow">포트 대시보드</p>
          <div className="space-y-2">
            <h1 className="hero-title">포트 조정용 운영 화면</h1>
            <p className="hero-copy">
              장식은 줄이고 정보 밀도는 높였습니다. 이제는 기술적 흐름보다 밸류 지표와
              `krx_screening`의 실제 스크리닝 결과를 우선 반영해 확대·축소 의견을 판단합니다.
            </p>
          </div>
          <p className="hero-inline-note">상위 테마: {topThemeSummary}</p>
        </div>

        <div className="hero-actions">
          <label className="primary-cta portfolio-upload">
            엑셀 업로드
            <input className="sr-only" type="file" accept=".xlsx,.xls,.csv" onChange={handleUploadFile} />
          </label>
          <button className="secondary-cta" type="button" onClick={handleEnrichValuation} disabled={isEnrichingValuation}>
            {isEnrichingValuation ? "밸류 채우는 중..." : "밸류 자동 채우기"}
          </button>
          <button
            className="secondary-cta"
            type="button"
            onClick={() => {
              setRows(initialRows);
              setSelectedRowId(initialRows[0]?.rowId ?? "");
              setDraft(
                initialRows[0]
                  ? withScreeningFallback(initialRows[0], matchScreeningRecord(initialRows[0], screeningLookup))
                  : null,
              );
              setStatusMessage("기본 portfolio_positions.csv 기준으로 다시 돌려놨어요.");
            }}
          >
            기본 데이터 복원
          </button>
          <button className="secondary-cta" type="button" onClick={handleDownloadTemplate}>
            템플릿 다운로드
          </button>
        </div>

        <div className="workspace-tab-bar">
          <button className="workspace-tab workspace-home-tab" type="button" onClick={() => setWorkspaceTab("home")}>
            <strong>홈</strong>
            <span>총자산으로 돌아가기</span>
          </button>
          {workspaceTabs.map((tab) => (
            <button
              key={tab.key}
              className={`workspace-tab ${workspaceTab === tab.key ? "workspace-tab-active" : ""}`}
              type="button"
              onClick={() => setWorkspaceTab(tab.key)}
            >
              <strong>{tab.label}</strong>
              <span>{tab.description}</span>
            </button>
          ))}
        </div>
      </section>
      )}

      {workspaceTab !== "home" ? <div className="inline-status-bar">
        <p className="inline-status">{statusMessage}</p>
        {marketFetchedAt ? (
          <p className="inline-status market-status">
            시세 갱신 {new Date(marketFetchedAt).toLocaleTimeString("ko-KR")}
          </p>
        ) : null}
      </div> : null}

      {workspaceTab !== "home" && unresolvedEnrichmentItems.length > 0 ? (
        <section className="panel unresolved-panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">밸류 누락</p>
              <h2>자동 연동이 안 된 종목</h2>
            </div>
            <span className="badge">{unresolvedEnrichmentItems.length}개</span>
          </div>
          <div className="unresolved-grid mt-5">
            {unresolvedEnrichmentItems.slice(0, 6).map((item) => (
              <article className="unresolved-card" key={item.rowId}>
                <strong>{item.name}</strong>
                <p>{item.reason || "자동 데이터 소스에서 유효한 밸류 값을 찾지 못했습니다."}</p>
                <span>{item.source ? `조회 시도: ${item.source}` : "조회 심볼 미확정"}</span>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {workspaceTab === "overview" ? (
        <>
          <section className="market-map-shell">
            <div className="market-map-head">
              <div>
                <p className="section-kicker">PORTFOLIO MAP</p>
                <h2>보유 종목 시장 지도</h2>
                <p>박스 크기 = 실제 비중 · 색상 = 당일 등락률(시세 대기 시 목표 갭) · 클릭 = 종목 상세</p>
              </div>
              <div className="market-map-legend" aria-label="등락률 색상 범례">
                <span className="legend-loss">-2% 이하</span>
                <span className="legend-flat">보합</span>
                <span className="legend-gain">+2% 이상</span>
              </div>
            </div>

            <div className="market-map-layout">
              <div className="portfolio-map-grid">
                {displayRows.map((row) => {
                  const marketSnapshot = getMarketSnapshot(row.rowId);
                  const changePct = marketSnapshot?.changePct ?? null;
                  const weightGap = row.actualWeightPct - row.targetWeightPct;
                  return (
                    <button
                      key={`map-${row.rowId}`}
                      className={`portfolio-map-cell ${heatmapSizeClass(row.actualWeightPct)} ${heatmapTone(changePct, weightGap)}`}
                      type="button"
                      title={`${row.name} · ${formatPct(row.actualWeightPct)} · ${changePct !== null ? formatSignedPct(changePct) : formatGap(row.actualWeightPct, row.targetWeightPct)}`}
                      onClick={() => selectRow(row)}
                    >
                      <span className="portfolio-map-theme">{row.theme}</span>
                      <strong>{row.name}</strong>
                      <span className="portfolio-map-weight">{formatPct(row.actualWeightPct)}</span>
                      <span className="portfolio-map-change">
                        {changePct !== null ? formatSignedPct(changePct) : `갭 ${formatGap(row.actualWeightPct, row.targetWeightPct)}`}
                      </span>
                    </button>
                  );
                })}
              </div>

              <aside className="market-map-side">
                <article className="finviz-widget">
                  <div className="finviz-widget-head">
                    <div>
                      <span>THEME EXPOSURE</span>
                      <strong>테마 집중도</strong>
                    </div>
                    <b>{snapshot.themeCount}개</b>
                  </div>
                  <div className="exposure-bars">
                    {snapshot.themeMix.slice(0, 7).map((item) => (
                      <div className="exposure-row" key={`exposure-${item.label}`}>
                        <div>
                          <strong>{item.label}</strong>
                          <span>{formatPct(item.actualWeightPct)}</span>
                        </div>
                        <div className="exposure-track">
                          <i style={{ width: `${Math.min(100, item.actualWeightPct * 4)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </article>

                <article className="finviz-widget value-map-widget">
                  <div className="finviz-widget-head">
                    <div>
                      <span>VALUE MAP</span>
                      <strong>PBR × PER 분포</strong>
                    </div>
                    <b>낮을수록 좌하단</b>
                  </div>
                  <div className="value-map-axis">
                    <span className="value-map-y">PER</span>
                    <span className="value-map-x">PBR</span>
                    <i className="value-map-mid-x" />
                    <i className="value-map-mid-y" />
                    {displayRows
                      .filter((row) => row.per !== null && row.pbr !== null && row.per! > 0 && row.pbr! > 0)
                      .slice(0, 18)
                      .map((row) => (
                        <button
                          key={`value-map-${row.rowId}`}
                          className="value-map-dot"
                          type="button"
                          title={`${row.name} · PER ${formatMultiple(row.per)} · PBR ${formatMultiple(row.pbr)}`}
                          style={{
                            left: `${Math.min(92, Math.max(5, ((row.pbr ?? 0) / 5) * 90))}%`,
                            bottom: `${Math.min(90, Math.max(7, ((row.per ?? 0) / 40) * 84))}%`,
                            width: `${Math.min(24, 8 + row.actualWeightPct * 1.4)}px`,
                            height: `${Math.min(24, 8 + row.actualWeightPct * 1.4)}px`,
                          }}
                          onClick={() => selectRow(row)}
                        >
                          <span>{row.name.slice(0, 2)}</span>
                        </button>
                      ))}
                  </div>
                </article>
              </aside>
            </div>
          </section>

          <section className="overview-hero-grid">
            <section className="panel overview-summary-panel">
              <div className="section-head">
                <div>
                  <p className="section-kicker">요약</p>
                  <h2>한눈 요약</h2>
                </div>
                <span className="badge">{snapshot.holdingCount}개 종목</span>
              </div>

              <div className="portfolio-metric-grid portfolio-metric-grid-balanced mt-5">
                <article className="portfolio-stat-card">
                  <span>실제 비중 합계</span>
                  <strong>{formatPct(snapshot.actualWeightSum)}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>목표 비중 합계</span>
                  <strong>{formatPct(snapshot.targetWeightSum)}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>테마 수</span>
                  <strong>{snapshot.themeCount}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>상위 테마군</span>
                  <strong>{topThemeCategorySummary}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>국가 수</span>
                  <strong>{snapshot.countries}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>스크리닝 연동</span>
                  <strong>
                    {screeningConnectedCount} / {displayRows.length}
                  </strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>국내 / 해외</span>
                  <strong>{domesticVsOverseas}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>상위 5종목 편중</span>
                  <strong>{formatPct(snapshot.topFiveWeight)}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>오늘 포트 손익</span>
                  <strong>{marketCoverageCount > 0 ? formatSignedCurrency(portfolioDayPnlKrw) : "집계 대기"}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>추가 매수 여력</span>
                  <strong>{snapshot.cashDrag > 0 ? formatPct(snapshot.cashDrag) : "0.00%"}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>목표 초과 비중</span>
                  <strong>
                    {formatPct(
                      trimCandidates.reduce(
                        (sum, row) => sum + (row.actualWeightPct - row.targetWeightPct),
                        0,
                      ),
                    )}
                  </strong>
                </article>
              </div>

              <div className="day-pnl-grid mt-4">
                <article className="day-pnl-card">
                  <span>국내 오늘 손익</span>
                  <strong className={domesticDayPnl !== null && domesticDayPnl < 0 ? "loss-text" : "gain-text"}>
                    {domesticDayPnl !== null ? formatSignedCurrency(domesticDayPnl) : "집계 대기"}
                  </strong>
                </article>
                <article className="day-pnl-card">
                  <span>해외 오늘 손익</span>
                  <strong className={overseasDayPnl !== null && overseasDayPnl < 0 ? "loss-text" : "gain-text"}>
                    {overseasDayPnl !== null ? formatSignedCurrency(overseasDayPnl) : "집계 대기"}
                  </strong>
                </article>
                <article className="day-pnl-card day-pnl-card-wide">
                  <span>상위 기여 테마</span>
                  <strong className={bestThemePnl !== null && bestThemePnl.value < 0 ? "loss-text" : "gain-text"}>
                    {bestThemePnl ? `${bestThemePnl.label} ${formatSignedCurrency(bestThemePnl.value)}` : "집계 대기"}
                  </strong>
                </article>
                <article className="day-pnl-card day-pnl-card-wide">
                  <span>약한 테마</span>
                  <strong className={weakestThemePnl !== null ? "loss-text" : ""}>
                    {weakestThemePnl ? `${weakestThemePnl.label} ${formatSignedCurrency(weakestThemePnl.value)}` : "없음"}
                  </strong>
                </article>
              </div>
            </section>

            <aside className="panel overview-core-panel">
              <div className="section-head">
                <div>
                  <p className="section-kicker">핵심</p>
                  <h2>핵심 보유군</h2>
                </div>
                <span className="badge">상위 3개</span>
              </div>
              <div className="stack gap-3 mt-5">
                {snapshot.coreHoldings.slice(0, 3).map((row) => (
                  <article className="portfolio-holding-card portfolio-holding-card-compact" key={row.rowId}>
                    <div className="dog-card-top">
                      <div>
                        <p className="dog-name">{row.name}</p>
                        <p className="muted-copy">
                          {row.marketScope} · {row.assetClass} · {row.theme}
                        </p>
                        <p className="muted-copy">{screeningLabel(row)}</p>
                      </div>
                      <span className="badge">{row.conviction || "미분류"}</span>
                    </div>
                    <div className="metric-grid">
                      <div className="metric-card">
                        <span>실제 비중</span>
                        <strong>{formatPct(row.actualWeightPct)}</strong>
                      </div>
                      <div className="metric-card">
                        <span>목표 비중</span>
                        <strong>{formatPct(row.targetWeightPct)}</strong>
                      </div>
                    </div>
                    <p className="muted-copy">{row.strategy || row.notes || "전략 메모 없음"}</p>
                  </article>
                ))}
              </div>
            </aside>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <section className="panel">
              <div className="section-head">
                <div>
                  <p className="section-kicker">운용 원칙</p>
                  <h2>{INVESTOR_PROFILE.title}</h2>
                </div>
              </div>
              <div className="investment-profile-card mt-5">
                <p>{INVESTOR_PROFILE.summary}</p>
                <div className="investment-principle-list">
                  {INVESTOR_PROFILE.principles.map((principle) => (
                    <article className="investment-principle-item" key={principle}>
                      <span />
                      <strong>{principle}</strong>
                    </article>
                  ))}
                </div>
              </div>
            </section>
            <section className="panel">
              <div className="section-head">
                <div>
                  <p className="section-kicker">구성</p>
                  <h2>테마와 액션 요약</h2>
                </div>
              </div>
              <div className="portfolio-mix-grid mt-5">
                <section className="portfolio-mix-card">
                  <div className="section-head">
                    <div>
                      <p className="section-kicker">테마</p>
                      <h2>상위 테마</h2>
                    </div>
                  </div>
                  <div className="stack gap-3">
                    {topThemes.map((item) => (
                      <div className="mix-row" key={item.label}>
                        <div>
                          <strong>{item.label}</strong>
                          <p>{formatPct(item.actualWeightPct)}</p>
                        </div>
                        <span className="badge">{formatGap(item.actualWeightPct, item.targetWeightPct)}</span>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="portfolio-mix-card">
                  <div className="section-head">
                    <div>
                      <p className="section-kicker">액션</p>
                      <h2>액션 큐</h2>
                    </div>
                  </div>
                  <div className="stack gap-3">
                    {topActions.map((item) => (
                      <div className={`mix-row mix-row-${actionTone(item.label)}`} key={item.label}>
                        <div>
                          <strong>{item.label}</strong>
                          <p>{formatPct(item.actualWeightPct)}</p>
                        </div>
                        <span className={`badge action-badge action-badge-${actionTone(item.label)}`}>
                          {formatPct(item.targetWeightPct)}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            </section>
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">오늘 액션</p>
                <h2>지금 봐야 할 종목</h2>
              </div>
              <span className="badge">행동 우선</span>
            </div>

            <div className="action-hq-grid mt-5">
              <section className="portfolio-priority-card">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">매수</p>
                    <h2>추가매수</h2>
                  </div>
                </div>
                <div className="stack gap-2">
                  {buyCandidates.map((row) => (
                    <button
                      key={row.rowId}
                      className="priority-row"
                      type="button"
                      onClick={() => selectRow(row)}
                    >
                      <div>
                        <strong>{row.name}</strong>
                        <p>{buildDecisionSummary(row)}</p>
                        <p className="muted-copy">{screeningLabel(row)}</p>
                        <p className="priority-market-line">{buildMarketLine(row)}</p>
                        <div className="priority-tag-row">
                          {buildActionReasonTags(row).map((tag) => (
                            <span className="priority-tag" key={`${row.rowId}-${tag}`}>{tag}</span>
                          ))}
                        </div>
                      </div>
                      <span className="gap-pill gap-pill-buy">{formatGap(row.actualWeightPct, row.targetWeightPct)}</span>
                    </button>
                  ))}
                </div>
              </section>

              <section className="portfolio-priority-card">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">축소</p>
                    <h2>비중축소</h2>
                  </div>
                </div>
                <div className="stack gap-2">
                  {trimCandidates.map((row) => (
                    <button
                      key={row.rowId}
                      className="priority-row"
                      type="button"
                      onClick={() => selectRow(row)}
                    >
                      <div>
                        <strong>{row.name}</strong>
                        <p>{buildDecisionSummary(row)}</p>
                        <p className="muted-copy">{screeningLabel(row)}</p>
                        <p className="priority-market-line">{buildMarketLine(row)}</p>
                        <div className="priority-tag-row">
                          {buildActionReasonTags(row).map((tag) => (
                            <span className="priority-tag" key={`${row.rowId}-${tag}`}>{tag}</span>
                          ))}
                        </div>
                      </div>
                      <span className="gap-pill gap-pill-trim">{formatGap(row.actualWeightPct, row.targetWeightPct)}</span>
                    </button>
                  ))}
                </div>
              </section>

              <section className="portfolio-priority-card">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">관찰</p>
                    <h2>유지·관찰</h2>
                  </div>
                </div>
                <div className="stack gap-2">
                  {watchCandidates.map((row) => (
                    <button key={row.rowId} className="priority-row" type="button" onClick={() => selectRow(row)}>
                      <div>
                        <strong>{row.name}</strong>
                        <p>{buildDecisionSummary(row)}</p>
                        <p className="muted-copy">{screeningLabel(row)}</p>
                        <p className="priority-market-line">{buildMarketLine(row)}</p>
                        <div className="priority-tag-row">
                          {buildActionReasonTags(row).map((tag) => (
                            <span className="priority-tag" key={`${row.rowId}-${tag}`}>{tag}</span>
                          ))}
                        </div>
                      </div>
                      <span className="gap-pill">{formatGap(row.actualWeightPct, row.targetWeightPct)}</span>
                    </button>
                  ))}
                </div>
              </section>

              <section className="portfolio-priority-card">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">확인</p>
                    <h2>먼저 확인 필요</h2>
                  </div>
                </div>
                <div className="stack gap-2">
                  {reviewCandidates.map((row) => (
                    <button key={row.rowId} className="priority-row priority-row-review" type="button" onClick={() => selectRow(row)}>
                      <div>
                        <strong>{row.name}</strong>
                        <p>{buildDecisionSummary(row)}</p>
                        <p className="muted-copy">{screeningLabel(row)}</p>
                        <p className="priority-market-line">{buildMarketLine(row)}</p>
                        <div className="priority-tag-row">
                          {buildActionReasonTags(row).map((tag) => (
                            <span className="priority-tag" key={`${row.rowId}-${tag}`}>{tag}</span>
                          ))}
                        </div>
                      </div>
                      <span className="gap-pill gap-pill-review">확인</span>
                    </button>
                  ))}
                </div>
              </section>
            </div>
          </section>
        </>
      ) : null}

      {workspaceTab === "analysis" ? (
        <>
          <section className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <section className="panel">
              <div className="section-head">
                <div>
                  <p className="section-kicker">포트 구조</p>
                  <h2>비중 시각화</h2>
                </div>
              </div>

              <div className="analysis-chart-grid mt-5">
                <article className="analysis-chart-card">
                  <div>
                    <p className="section-kicker">테마 비중</p>
                    <h3>상위 테마 원형 비중</h3>
                  </div>
                  <div className="analysis-donut" style={themeChartStyle}>
                    <div className="analysis-donut-center">
                      <strong>{analysisThemeMix.length}</strong>
                      <span>상위 테마</span>
                    </div>
                  </div>
                  <div className="analysis-legend">
                    {analysisThemeMix.map((item, index) => (
                      <div className="analysis-legend-row" key={item.label}>
                        <span
                          className="analysis-dot"
                          style={{ backgroundColor: ["#1f6feb", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"][index] }}
                        />
                        <strong>{item.label}</strong>
                        <span>{formatPct(item.actualWeightPct)}</span>
                      </div>
                    ))}
                  </div>
                </article>

                <article className="analysis-chart-card">
                  <div>
                    <p className="section-kicker">지역 비중</p>
                    <h3>국내 / 해외 구성</h3>
                  </div>
                  <div className="analysis-donut analysis-donut-small" style={regionChartStyle}>
                    <div className="analysis-donut-center">
                      <strong>{formatPct(snapshot.domesticWeight + snapshot.overseasWeight)}</strong>
                      <span>투자 비중</span>
                    </div>
                  </div>
                  <div className="analysis-legend">
                    {analysisRegionMix.map((item, index) => (
                      <div className="analysis-legend-row" key={item.label}>
                        <span
                          className="analysis-dot"
                          style={{ backgroundColor: ["#174ea6", "#06b6d4", "#94a3b8"][index] }}
                        />
                        <strong>{item.label}</strong>
                        <span>{formatPct(item.actualWeightPct)}</span>
                      </div>
                    ))}
                  </div>
                </article>
              </div>
            </section>

            <section className="panel">
              <div className="section-head">
                <div>
                  <p className="section-kicker">포트 코멘트</p>
                  <h2>현재 포트 인사이트</h2>
                </div>
              </div>

              <div className="analysis-note-stack mt-5">
                {portfolioNarrative.map((line) => (
                  <article className="analysis-note-card" key={line}>
                    <p>{line}</p>
                  </article>
                ))}
              </div>
            </section>
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">액션 근거</p>
                <h2>비중 조정 사유</h2>
              </div>
            </div>

            <div className="analysis-decision-grid mt-5">
              <section className="analysis-decision-card">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">축소 후보</p>
                    <h3>왜 비중을 줄이나</h3>
                  </div>
                </div>
                <div className="stack gap-4">
                  {trimCandidates.map((row) => (
                    <article className="analysis-security-card" key={row.rowId}>
                      <div className="position-card-top">
                        <div>
                          <p className="dog-name">{row.name}</p>
                          <p className="muted-copy">
                            {row.theme} · {row.marketScope} · {formatGap(row.actualWeightPct, row.targetWeightPct)}
                          </p>
                          <p className="muted-copy">{screeningLabel(row)}</p>
                        </div>
                        <span className="action-label action-label-trim">비중축소 검토</span>
                      </div>
                      <p className="analysis-opinion">{buildDecisionSummary(row)}</p>
                      <div className="analysis-verdict-row">
                        <div>
                          <span>판정</span>
                          <strong>{buildAnalysisVerdict(row)}</strong>
                        </div>
                        <div>
                          <span>체크포인트</span>
                          <strong>{buildChecklist(row)}</strong>
                        </div>
                      </div>
                      <div className="analysis-criteria-grid">
                        {buildCriteriaRows(row).map((item) => (
                          <article className={`analysis-criteria-card analysis-criteria-${item.tone}`} key={`${row.rowId}-${item.label}`}>
                            <span>{item.label}</span>
                            <strong>{item.value}</strong>
                          </article>
                        ))}
                      </div>
                      <div className="analysis-meta-grid">
                        <div>
                          <span>가장 약한 부분</span>
                          <strong>{buildWeaknessLabel(row)}</strong>
                        </div>
                        <div>
                          <span>스크리닝 사유</span>
                          <strong>{screeningReason(row) || "국내 스크리닝 근거 미연동"}</strong>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="analysis-decision-card">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">매수 후보</p>
                    <h3>왜 더 볼 만한가</h3>
                  </div>
                </div>
                <div className="stack gap-4">
                  {buyCandidates.map((row) => (
                    <article className="analysis-security-card" key={row.rowId}>
                      <div className="position-card-top">
                        <div>
                          <p className="dog-name">{row.name}</p>
                          <p className="muted-copy">
                            {row.theme} · {row.marketScope} · {formatGap(row.actualWeightPct, row.targetWeightPct)}
                          </p>
                          <p className="muted-copy">{screeningLabel(row)}</p>
                        </div>
                        <span className="action-label action-label-buy">추가매수 검토</span>
                      </div>
                      <p className="analysis-opinion">{buildDecisionSummary(row)}</p>
                      <div className="analysis-verdict-row">
                        <div>
                          <span>판정</span>
                          <strong>{buildAnalysisVerdict(row)}</strong>
                        </div>
                        <div>
                          <span>체크포인트</span>
                          <strong>{buildChecklist(row)}</strong>
                        </div>
                      </div>
                      <div className="analysis-criteria-grid">
                        {buildCriteriaRows(row).map((item) => (
                          <article className={`analysis-criteria-card analysis-criteria-${item.tone}`} key={`${row.rowId}-${item.label}`}>
                            <span>{item.label}</span>
                            <strong>{item.value}</strong>
                          </article>
                        ))}
                      </div>
                      <div className="analysis-meta-grid">
                        <div>
                          <span>가장 약한 부분</span>
                          <strong>{buildWeaknessLabel(row)}</strong>
                        </div>
                        <div>
                          <span>스크리닝 사유</span>
                          <strong>{screeningReason(row) || "국내 스크리닝 근거 미연동"}</strong>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          </section>
        </>
      ) : null}

      {workspaceTab === "positions" ? (
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">탐색</p>
              <h2>보유 종목 탐색</h2>
            </div>
            <span className="badge">{filteredRows.length}개 표시</span>
          </div>

          <div className="portfolio-filter-row mt-5">
            <div className="portfolio-tab-row">
              {quickTabs.map((tab) => (
                <button
                  key={tab}
                  className={`portfolio-tab ${tabFilter === tab ? "portfolio-tab-active" : ""}`}
                  type="button"
                  onClick={() => setTabFilter(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          <div className="portfolio-filter-row mt-4">
            <input
              className="portfolio-input"
              type="search"
              placeholder="종목명, 티커, 테마, 전략 검색"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <select className="portfolio-input" value={scopeFilter} onChange={(event) => setScopeFilter(event.target.value)}>
              <option value="전체">전체 지역</option>
              <option value="국내">국내</option>
              <option value="해외">해외</option>
            </select>
            <select className="portfolio-input" value={actionFilter} onChange={(event) => setActionFilter(event.target.value)}>
              <option value="전체">전체 액션</option>
              {snapshot.actionMix.map((item) => (
                <option key={item.label} value={item.label}>
                  {item.label}
                </option>
              ))}
            </select>
            <select className="portfolio-input" value={sortKey} onChange={(event) => setSortKey(event.target.value)}>
              <option value="actual_desc">실제 비중순</option>
              <option value="target_desc">목표 비중순</option>
              <option value="gap_desc">언더웨이트 큰 순</option>
              <option value="gap_asc">오버웨이트 큰 순</option>
              <option value="action">액션순</option>
              <option value="name_asc">이름순</option>
            </select>
          </div>

          <div className="position-valuation-banner mt-4">
            <div>
              <span>밸류 연동</span>
              <strong>
                {valuationConnectedCount} / {displayRows.length}
              </strong>
            </div>
            <p>PER · PBR · EPS · Forward PER를 종목 카드 상단에서 바로 보이게 노출합니다.</p>
          </div>

          <div className="position-card-grid mt-5">
            {filteredRows.map((row) => (
              <button
                className={`position-card position-card-${actionTone(row.plannedAction)} ${
                  selectedRow?.rowId === row.rowId ? "position-card-selected" : ""
                }`}
                key={row.rowId}
                type="button"
                onClick={() => selectRow(row)}
              >
                <div className="position-card-top">
                  <div>
                    <p className="dog-name">{row.name}</p>
                    <p className="muted-copy">
                      {row.ticker} · {row.marketScope} · {row.assetClass}
                    </p>
                  </div>
                  <span className={`action-label action-label-${actionTone(row.plannedAction)}`}>
                    {row.plannedAction}
                  </span>
                </div>

                <p className="position-opinion">{buildDecisionSummary(row)}</p>

                <div className="position-tag-row">
                  <span className="portfolio-mini-tag">{row.themeCategory || "테마군 미입력"}</span>
                  <span className="portfolio-mini-tag">{row.theme}</span>
                  <span className="portfolio-mini-tag">{row.subTheme || "세부테마 미입력"}</span>
                  <span className="portfolio-mini-tag">{row.trendView || "추세 미입력"}</span>
                </div>

                <div className="position-metrics">
                  <div>
                    <span>실제</span>
                    <strong>{formatPct(row.actualWeightPct)}</strong>
                  </div>
                  <div>
                    <span>목표</span>
                    <strong>{formatPct(row.targetWeightPct)}</strong>
                  </div>
                  <div>
                    <span>갭</span>
                    <strong>{formatGap(row.actualWeightPct, row.targetWeightPct)}</strong>
                  </div>
                </div>

                <div className="position-live-strip">
                  <strong>{buildMarketLine(row)}</strong>
                </div>

                <div className="valuation-grid valuation-grid-prominent">
                  <div>
                    <span>PER</span>
                    <strong>{formatMetricOrPending(row.per, (value) => formatMultiple(value))}</strong>
                  </div>
                  <div>
                    <span>PBR</span>
                    <strong>{formatMetricOrPending(row.pbr, (value) => formatMultiple(value))}</strong>
                  </div>
                  <div>
                    <span>EPS</span>
                    <strong>{formatMetricOrPending(row.eps, formatNumberValue)}</strong>
                  </div>
                  <div>
                    <span>Fwd PER</span>
                    <strong>{formatMetricOrPending(row.forwardPer, (value) => formatMultiple(value))}</strong>
                  </div>
                </div>

                <div className="shareholder-return-grid">
                  <div>
                    <span>배당수익률</span>
                    <strong>
                      {formatMetricOrPending(
                        row.screening?.dividendYieldNormalized ?? row.screening?.dividendYieldTrailing ?? null,
                        (value) => formatPct(value ?? 0),
                      )}
                    </strong>
                  </div>
                  <div>
                    <span>배당성향</span>
                    <strong>
                      {formatMetricOrPending(row.screening?.payoutRatioPct ?? null, (value) => formatPct(value ?? 0))}
                    </strong>
                  </div>
                  <div>
                    <span>환원 평가</span>
                    <strong>{shareholderReturnLabel(row)}</strong>
                  </div>
                  <div>
                    <span>배당 안정성</span>
                    <strong>{payoutStabilityLabel(row)}</strong>
                  </div>
                </div>

                <div className="screening-card screening-card-compact">
                  <div className="screening-card-top">
                    <strong>{screeningLabel(row)}</strong>
                    <span>{row.screening?.stage || "-"}</span>
                  </div>
                  <div className="screening-score-grid">
                    <div>
                      <span>Final</span>
                      <strong>{formatScreeningScore(row.screening?.finalScore)}</strong>
                    </div>
                    <div>
                      <span>Value</span>
                      <strong>{formatScreeningScore(row.screening?.valueScore)}</strong>
                    </div>
                    <div>
                      <span>Valuation</span>
                      <strong>{formatScreeningScore(row.screening?.valuationScore)}</strong>
                    </div>
                    <div>
                      <span>Trap Risk</span>
                      <strong>{formatScreeningScore(row.screening?.valueTrapRiskScore)}</strong>
                    </div>
                  </div>
                  <p className="screening-reason">
                    {screeningReason(row) || "해외 종목 또는 미연동 종목이라 스크리닝 근거가 아직 없습니다."}
                  </p>
                </div>

                <div className="position-detail-grid">
                  <div>
                    <span>전략</span>
                    <strong>{row.strategy || "-"}</strong>
                  </div>
                  <div>
                    <span>스타일</span>
                    <strong>{row.styleBucket || "-"}</strong>
                  </div>
                  <div>
                    <span>사이클</span>
                    <strong>{row.cycleView || "-"}</strong>
                  </div>
                  <div>
                    <span>타이밍</span>
                    <strong>{row.timingView || "-"}</strong>
                  </div>
                </div>

                <p className="position-note">{row.notes || "메모 없음"}</p>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {workspaceTab === "editor" ? (
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">상세</p>
              <h2>운영 메모</h2>
            </div>
            {selectedRow ? (
              <span className={`badge action-badge action-badge-${actionTone(selectedRow.plannedAction)}`}>
                {selectedRow.plannedAction}
              </span>
            ) : null}
          </div>

          {selectedRow ? (
            <div className="portfolio-detail-stack mt-5">
              <article className="portfolio-detail-hero">
                <div className="dog-card-top">
                  <div>
                    <p className="dog-name">{selectedRow.name}</p>
                    <p className="muted-copy">
                      {selectedRow.ticker} · {selectedRow.marketScope} · {selectedRow.assetClass}
                    </p>
                  </div>
                  <span className="badge">{selectedRow.conviction || "미분류"}</span>
                </div>
                <div className="portfolio-tag-strip">
                  <span className="portfolio-mini-tag">{selectedRow.themeCategory || "테마군 미입력"}</span>
                  <span className="portfolio-mini-tag">{selectedRow.theme}</span>
                  <span className="portfolio-mini-tag">{selectedRow.subTheme || "세부 테마 미입력"}</span>
                  <span className="portfolio-mini-tag">{selectedRow.strategy || "전략 미입력"}</span>
                  <span className="portfolio-mini-tag">{selectedRow.trendView || "추세 미입력"}</span>
                </div>
                <div className="portfolio-metric-grid portfolio-metric-grid-compact">
                  <article className="portfolio-stat-card">
                    <span>실제 비중</span>
                    <strong>{formatPct(selectedRow.actualWeightPct)}</strong>
                  </article>
                  <article className="portfolio-stat-card">
                    <span>목표 비중</span>
                    <strong>{formatPct(selectedRow.targetWeightPct)}</strong>
                  </article>
                  <article className="portfolio-stat-card">
                    <span>갭</span>
                    <strong>{formatGap(selectedRow.actualWeightPct, selectedRow.targetWeightPct)}</strong>
                  </article>
                  <article className="portfolio-stat-card">
                    <span>환노출</span>
                    <strong>{selectedRow.fxExposure || "-"}</strong>
                  </article>
                </div>
                <div className="valuation-grid valuation-grid-wide">
                  <div>
                    <span>PER</span>
                    <strong>{formatMultiple(selectedRow.per)}</strong>
                  </div>
                  <div>
                    <span>PBR</span>
                    <strong>{formatMultiple(selectedRow.pbr)}</strong>
                  </div>
                  <div>
                    <span>EPS</span>
                    <strong>{formatNumberValue(selectedRow.eps)}</strong>
                  </div>
                  <div>
                    <span>Fwd PER</span>
                    <strong>{formatMultiple(selectedRow.forwardPer)}</strong>
                  </div>
                </div>
                <div className="shareholder-return-panel">
                  <div className="section-head">
                    <div>
                      <p className="section-kicker">주주환원</p>
                      <h3>배당과 자사주 정책</h3>
                    </div>
                    <span className="badge">{shareholderReturnLabel(selectedRow)}</span>
                  </div>
                  <div className="shareholder-return-grid shareholder-return-grid-detailed">
                    <div>
                      <span>평년 배당수익률</span>
                      <strong>
                        {formatMetricOrPending(
                          selectedRow.screening?.dividendYieldNormalized ??
                            selectedRow.screening?.dividendYieldTrailing ??
                            null,
                          (value) => formatPct(value ?? 0),
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>배당성향</span>
                      <strong>
                        {formatMetricOrPending(
                          selectedRow.screening?.payoutRatioPct ?? null,
                          (value) => formatPct(value ?? 0),
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>배당 성장률</span>
                      <strong>
                        {formatMetricOrPending(
                          selectedRow.screening?.dividendGrowthRatePct ?? null,
                          (value) => formatPct(value ?? 0),
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>배당 반복성</span>
                      <strong>{payoutStabilityLabel(selectedRow)}</strong>
                    </div>
                    <div>
                      <span>자사주 비율</span>
                      <strong>
                        {formatMetricOrPending(
                          selectedRow.screening?.treasuryStockRatioPct ?? null,
                          (value) => formatPct(value ?? 0),
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>최근 소각</span>
                      <strong>{selectedRow.screening ? (selectedRow.screening.treasuryBurnRecent ? "확인" : "미확인") : "연동 필요"}</strong>
                    </div>
                    <div>
                      <span>배당 확대</span>
                      <strong>{selectedRow.screening ? (selectedRow.screening.payoutIncreaseFlag ? "확인" : "미확인") : "연동 필요"}</strong>
                    </div>
                    <div>
                      <span>환원 점수</span>
                      <strong>{formatScreeningScore(selectedRow.screening?.shareholderReturnScore)}</strong>
                    </div>
                  </div>
                  <p className="shareholder-return-note">
                    자사주 소각과 배당 확대는 최근 공시·뉴스에서 확인된 경우만 표시합니다. 미확인은 없다는 뜻이 아니라
                    현재 데이터에서 확인되지 않았다는 뜻입니다.
                  </p>
                </div>
                <div className="screening-card screening-card-detailed">
                  <div className="section-head">
                    <div>
                      <p className="section-kicker">스크리닝</p>
                      <h3>시스템 판정</h3>
                    </div>
                    <span className="badge">{screeningLabel(selectedRow)}</span>
                  </div>
                  <div className="screening-score-grid screening-score-grid-wide">
                    <div>
                      <span>Final Score</span>
                      <strong>{formatScreeningScore(selectedRow.screening?.finalScore)}</strong>
                    </div>
                    <div>
                      <span>Value Score</span>
                      <strong>{formatScreeningScore(selectedRow.screening?.valueScore)}</strong>
                    </div>
                    <div>
                      <span>Valuation Score</span>
                      <strong>{formatScreeningScore(selectedRow.screening?.valuationScore)}</strong>
                    </div>
                    <div>
                      <span>Dividend Score</span>
                      <strong>{formatScreeningScore(selectedRow.screening?.dividendPotentialScore)}</strong>
                    </div>
                    <div>
                      <span>Quality Score</span>
                      <strong>{formatScreeningScore(selectedRow.screening?.businessQualityScore)}</strong>
                    </div>
                    <div>
                      <span>Trap Risk</span>
                      <strong>{formatScreeningScore(selectedRow.screening?.valueTrapRiskScore)}</strong>
                    </div>
                  </div>
                  <div className="screening-meta-grid">
                    <div>
                      <span>Stage</span>
                      <strong>{selectedRow.screening?.stage || "-"}</strong>
                    </div>
                    <div>
                      <span>Core Bucket</span>
                      <strong>{selectedRow.screening?.coreBucket || "-"}</strong>
                    </div>
                    <div>
                      <span>Leader Bucket</span>
                      <strong>{selectedRow.screening?.leaderBucket || "-"}</strong>
                    </div>
                    <div>
                      <span>6M Return</span>
                      <strong>
                        {selectedRow.screening?.returns6mPct !== null && selectedRow.screening?.returns6mPct !== undefined
                          ? formatPct(selectedRow.screening.returns6mPct)
                          : "-"}
                      </strong>
                    </div>
                  </div>
                  <p className="screening-reason">
                    {screeningReason(selectedRow) || "해외 종목 또는 미연동 종목이라 스크리닝 시스템 의견이 아직 없습니다."}
                  </p>
                </div>
                <div className="portfolio-classification-grid">
                  <div>
                    <span>국가</span>
                    <strong>{selectedRow.country || "-"}</strong>
                  </div>
                  <div>
                    <span>테마군</span>
                    <strong>{selectedRow.themeCategory || "-"}</strong>
                  </div>
                  <div>
                    <span>스타일</span>
                    <strong>{selectedRow.styleBucket || "-"}</strong>
                  </div>
                  <div>
                    <span>사이클</span>
                    <strong>{selectedRow.cycleView || "-"}</strong>
                  </div>
                  <div>
                    <span>타이밍</span>
                    <strong>{selectedRow.timingView || "-"}</strong>
                  </div>
                </div>
              </article>

              <article className="portfolio-detail-card">
                <h3>수정</h3>
                {draft ? (
                  <div className="portfolio-edit-grid">
                    <div className="trade-helper-card portfolio-field-wide">
                      <div className="section-head">
                        <div>
                          <p className="section-kicker">오늘 매매 반영</p>
                          <h2>퀵 반영</h2>
                        </div>
                      </div>
                      <div className="trade-helper-grid">
                        <label className="portfolio-field">
                          <span>매매 방향</span>
                          <select className="portfolio-input" value={tradeMode} onChange={(event) => setTradeMode(event.target.value as TradeMode)}>
                            <option value="buy">매수</option>
                            <option value="sell">매도</option>
                          </select>
                        </label>
                        <label className="portfolio-field">
                          <span>실제 비중 변화</span>
                          <input
                            className="portfolio-input"
                            type="number"
                            step="0.01"
                            min="0"
                            value={tradeWeightDelta}
                            onChange={(event) => setTradeWeightDelta(event.target.value)}
                          />
                        </label>
                        <label className="portfolio-field portfolio-field-wide">
                          <span>오늘 매매 메모</span>
                          <input
                            className="portfolio-input"
                            placeholder="예: 장중 2차 매수, 실적 확인 후 축소"
                            value={tradeMemo}
                            onChange={(event) => setTradeMemo(event.target.value)}
                          />
                        </label>
                      </div>
                      <div className="trade-helper-actions">
                        <button className="primary-small" type="button" onClick={handleApplyTradeAdjustment}>
                          오늘 매매 반영
                        </button>
                        <button className="secondary-cta" type="button" onClick={handleMarkFullySold}>
                          전량 매도 반영
                        </button>
                        <p className="trade-helper-copy">
                          종목 앱에서 사고팔고 난 뒤 여기서 비중 변화만 넣으면 드래프트에 바로 반영됩니다.
                        </p>
                      </div>
                    </div>
                    <label className="portfolio-field">
                      <span>테마군</span>
                      <input className="portfolio-input" value={draft.themeCategory} onChange={(event) => handleDraftChange("themeCategory", event.target.value)} />
                    </label>
                    <label className="portfolio-field">
                      <span>테마</span>
                      <input className="portfolio-input" value={draft.theme} onChange={(event) => handleDraftChange("theme", event.target.value)} />
                    </label>
                    <label className="portfolio-field">
                      <span>세부 테마</span>
                      <input className="portfolio-input" value={draft.subTheme} onChange={(event) => handleDraftChange("subTheme", event.target.value)} />
                    </label>
                    <label className="portfolio-field">
                      <span>전략</span>
                      <input className="portfolio-input" value={draft.strategy} onChange={(event) => handleDraftChange("strategy", event.target.value)} />
                    </label>
                    <label className="portfolio-field">
                      <span>PER</span>
                      <input className="portfolio-input" type="number" step="0.1" value={draft.per ?? ""} onChange={(event) => handleDraftChange("per", event.target.value === "" ? null : Number(event.target.value))} />
                    </label>
                    <label className="portfolio-field">
                      <span>PBR</span>
                      <input className="portfolio-input" type="number" step="0.1" value={draft.pbr ?? ""} onChange={(event) => handleDraftChange("pbr", event.target.value === "" ? null : Number(event.target.value))} />
                    </label>
                    <label className="portfolio-field">
                      <span>EPS</span>
                      <input className="portfolio-input" type="number" step="1" value={draft.eps ?? ""} onChange={(event) => handleDraftChange("eps", event.target.value === "" ? null : Number(event.target.value))} />
                    </label>
                    <label className="portfolio-field">
                      <span>Fwd PER</span>
                      <input className="portfolio-input" type="number" step="0.1" value={draft.forwardPer ?? ""} onChange={(event) => handleDraftChange("forwardPer", event.target.value === "" ? null : Number(event.target.value))} />
                    </label>
                    <label className="portfolio-field">
                      <span>추세</span>
                      <input className="portfolio-input" value={draft.trendView} onChange={(event) => handleDraftChange("trendView", event.target.value)} />
                    </label>
                    <label className="portfolio-field">
                      <span>실제 비중</span>
                      <input
                        className="portfolio-input"
                        type="number"
                        step="0.01"
                        value={draft.actualWeightPct}
                        onChange={(event) => handleDraftChange("actualWeightPct", Number(event.target.value))}
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>목표 비중</span>
                      <input
                        className="portfolio-input"
                        type="number"
                        step="0.01"
                        value={draft.targetWeightPct}
                        onChange={(event) => handleDraftChange("targetWeightPct", Number(event.target.value))}
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>액션</span>
                      <select className="portfolio-input" value={draft.plannedAction} onChange={(event) => handleDraftChange("plannedAction", event.target.value)}>
                        <option value="추가매수 검토">추가매수 검토</option>
                        <option value="비중축소 검토">비중축소 검토</option>
                        <option value="정리 검토">정리 검토</option>
                        <option value="보유 유지">보유 유지</option>
                        <option value="보유/관찰">보유/관찰</option>
                      </select>
                    </label>
                    <label className="portfolio-field">
                      <span>타이밍</span>
                      <input className="portfolio-input" value={draft.timingView} onChange={(event) => handleDraftChange("timingView", event.target.value)} />
                    </label>
                    <label className="portfolio-field portfolio-field-wide">
                      <span>메모</span>
                      <textarea className="portfolio-textarea" value={draft.notes} onChange={(event) => handleDraftChange("notes", event.target.value)} />
                    </label>
                    <div className="hero-actions">
                      <button className="secondary-cta" type="button" onClick={handleEnrichValuation} disabled={isEnrichingValuation}>
                        {isEnrichingValuation ? "밸류 채우는 중..." : "밸류 자동 채우기"}
                      </button>
                      <button className="primary-small" type="button" onClick={handleApplyDraft}>
                        화면 반영
                      </button>
                      <button className="secondary-cta" type="button" onClick={handleSaveToFile} disabled={isSavingFile}>
                        {isSavingFile ? "저장 중..." : usesCloudStorage ? "클라우드 저장" : "로컬 저장"}
                      </button>
                    </div>
                  </div>
                ) : null}
              </article>
            </div>
          ) : (
            <p className="muted-copy">선택된 종목이 없습니다.</p>
          )}
        </section>
      ) : null}
    </main>
  );
}
