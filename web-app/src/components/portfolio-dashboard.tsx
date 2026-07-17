"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { hasSupabaseEnv } from "@/lib/env";
import {
  buildPortfolioSnapshot,
  normalizePortfolioRecords,
  type PortfolioPosition,
} from "@/lib/portfolio-dashboard";

type PortfolioDashboardProps = {
  initialRows: PortfolioPosition[];
};

type WorkspaceTab = "overview" | "analysis" | "positions" | "editor";

function formatPct(value: number) {
  return `${value.toFixed(2)}%`;
}

function formatGap(actualWeightPct: number, targetWeightPct: number) {
  const gap = targetWeightPct - actualWeightPct;
  return `${gap > 0 ? "+" : ""}${gap.toFixed(2)}%p`;
}

function buildActionReasons(row: PortfolioPosition) {
  const reasons: string[] = [];
  const gap = row.actualWeightPct - row.targetWeightPct;

  if (gap > 0.75) {
    reasons.push(`현재 비중이 목표보다 ${gap.toFixed(2)}%p 높습니다.`);
  } else if (gap < -0.75) {
    reasons.push(`현재 비중이 목표보다 ${Math.abs(gap).toFixed(2)}%p 낮습니다.`);
  }

  if (row.trendView.includes("과열")) {
    reasons.push("추세가 과열 구간으로 표시돼 단기 과열 해소를 점검할 필요가 있습니다.");
  } else if (row.trendView.includes("눌림")) {
    reasons.push("추세가 눌림 구간이라면 분할 접근 논리를 붙이기 좋습니다.");
  } else if (row.trendView.includes("확인 필요")) {
    reasons.push("추세 확인이 끝나지 않아 비중을 서두르기보다 근거 보강이 먼저입니다.");
  } else if (row.trendView.includes("진행")) {
    reasons.push("추세 진행 상태라 방향성은 유지되지만 가격 위치는 따로 점검해야 합니다.");
  }

  if (row.cycleView.includes("과열")) {
    reasons.push("사이클도 과열 구간으로 적혀 있어 수익 보호 논리가 생깁니다.");
  } else if (row.cycleView.includes("주도") || row.cycleView.includes("상승")) {
    reasons.push("사이클이 아직 상승 흐름이라 너무 빠른 축소는 기회비용이 생길 수 있습니다.");
  }

  if (row.conviction === "핵심") {
    reasons.push("핵심 보유군이라 정리보다 목표 비중 복귀 중심으로 보는 편이 자연스럽습니다.");
  } else if (row.conviction === "위성") {
    reasons.push("위성 포지션이라면 기준 이탈 시 더 빠른 축소 판단이 가능합니다.");
  }

  if (row.styleBucket === "인컴") {
    reasons.push("인컴 자산은 배당/현금흐름 역할을 같이 봐야 해서 비중 조정이 더 보수적이어야 합니다.");
  } else if (row.styleBucket === "성장") {
    reasons.push("성장 자산은 추세와 실적 기대를 함께 봐야 하므로 변동성 관리가 중요합니다.");
  } else if (row.styleBucket === "패시브") {
    reasons.push("패시브 자산이라 개별 종목보다 테마·지역 익스포저 조절 관점이 더 중요합니다.");
  }

  if (row.notes) {
    reasons.push(`메모 반영: ${row.notes}`);
  }

  return reasons.slice(0, 4);
}

function buildOutlook(row: PortfolioPosition) {
  if (row.trendView.includes("과열") && row.plannedAction.includes("비중축소")) {
    return "상승 추세는 살아 있어도 단기 과열 해소 구간을 염두에 둔 관리형 축소가 어울립니다.";
  }
  if (row.trendView.includes("진행") && row.plannedAction.includes("추가매수")) {
    return "방향성은 우호적이라 눌림 확인 시 비중을 천천히 늘리는 시나리오가 자연스럽습니다.";
  }
  if (row.trendView.includes("확인 필요")) {
    return "지금은 전망 확신보다 체크리스트 보강이 우선이라 관찰 강도가 더 중요합니다.";
  }
  return "현재 분류상으로는 추세와 목표 비중의 균형을 맞추는 운영이 우선입니다.";
}

function buildValuationLens(row: PortfolioPosition) {
  if (row.strategy.includes("Value") || row.theme.includes("금융") || row.theme.includes("지주사")) {
    return "밸류 관점에서는 할인 해소 여지와 자산가치 재평가가 핵심 근거입니다.";
  }
  if (row.styleBucket === "성장" || row.theme.includes("AI") || row.theme.includes("반도체")) {
    return "밸류보다 성장 지속성, 실적 모멘텀, 주도주 프리미엄이 더 중요한 구간입니다.";
  }
  if (row.styleBucket === "인컴") {
    return "밸류는 배당 지속성과 현금흐름 방어력으로 해석하는 편이 더 맞습니다.";
  }
  return "절대 밸류보다 포트 역할과 목표 비중 적합성이 더 중요한 종목으로 보입니다.";
}

function buildPortfolioNarrative(rows: PortfolioPosition[], snapshot: ReturnType<typeof buildPortfolioSnapshot>) {
  const topTheme = snapshot.themeMix[0];
  const topTrim = snapshot.trimCandidates[0];
  const topBuy = snapshot.buyCandidates[0];
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
    narratives.push(`${topTrim.name}은 목표 초과폭이 커서 우선 축소 후보로 보입니다.`);
  }
  if (topBuy) {
    narratives.push(`${topBuy.name}은 목표 미달폭이 커서 추가 검토 1순위 후보입니다.`);
  }
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

export function PortfolioDashboard({ initialRows }: PortfolioDashboardProps) {
  const usesCloudStorage = hasSupabaseEnv();
  const [rows, setRows] = useState(initialRows);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("overview");
  const [query, setQuery] = useState("");
  const [scopeFilter, setScopeFilter] = useState("전체");
  const [actionFilter, setActionFilter] = useState("전체");
  const [tabFilter, setTabFilter] = useState("전체");
  const [sortKey, setSortKey] = useState("actual_desc");
  const [selectedRowId, setSelectedRowId] = useState(initialRows[0]?.rowId ?? "");
  const [draft, setDraft] = useState<PortfolioPosition | null>(initialRows[0] ?? null);
  const [isSavingFile, setIsSavingFile] = useState(false);
  const [statusMessage, setStatusMessage] = useState(
    usesCloudStorage
      ? "현재 포트를 불러왔어요. 수정 후 클라우드 저장하면 배포 환경에서도 그대로 유지됩니다."
      : "현재 포트 CSV를 기본으로 불러왔어요. 엑셀이나 CSV를 올리면 바로 화면이 바뀝니다.",
  );
  const deferredQuery = useDeferredValue(query);

  const filteredRows = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLowerCase();

    const nextRows = rows.filter((row) => {
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
  }, [actionFilter, deferredQuery, rows, scopeFilter, sortKey, tabFilter]);

  const snapshot = useMemo(() => buildPortfolioSnapshot(rows), [rows]);
  const quickTabs = ["전체", "핵심 보유", "추가매수", "비중축소", "관찰"];
  const workspaceTabs = [
    { key: "overview", label: "개요", description: "요약과 리밸런싱 우선순위" },
    { key: "analysis", label: "분석", description: "비중 사유와 인사이트" },
    { key: "positions", label: "종목", description: "검색, 필터, 종목 비교" },
    { key: "editor", label: "편집", description: "선택 종목 상세 수정" },
  ] as const;
  const selectedRow =
    rows.find((row) => row.rowId === selectedRowId) ??
    rows[0] ??
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

  function selectRow(row: PortfolioPosition, nextTab: "positions" | "editor" = "editor") {
    setSelectedRowId(row.rowId);
    setDraft({ ...row });
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
      setDraft(nextRows[0] ? { ...nextRows[0] } : null);
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

  const topThemes = snapshot.themeMix.slice(0, 4);
  const topActions = snapshot.actionMix.slice(0, 4);
  const topThemeSummary = topThemes
    .map((item) => `${item.label} ${formatPct(item.actualWeightPct)}`)
    .join(" · ");
  const domesticVsOverseas = `${formatPct(snapshot.domesticWeight)} / ${formatPct(snapshot.overseasWeight)}`;
  const analysisThemeMix = snapshot.themeMix.slice(0, 5);
  const analysisRegionMix = snapshot.regionMix.slice(0, 3);
  const themeChartStyle = buildDonutStyle(analysisThemeMix, ["#1f6feb", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"]);
  const regionChartStyle = buildDonutStyle(analysisRegionMix, ["#174ea6", "#06b6d4", "#94a3b8"]);
  const portfolioNarrative = buildPortfolioNarrative(rows, snapshot);

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="hero-panel">
        <div className="space-y-3">
          <p className="eyebrow">포트 대시보드</p>
          <div className="space-y-2">
            <h1 className="hero-title">포트 조정용 운영 화면</h1>
            <p className="hero-copy">
              화면을 세 구역으로 나눠서 보이게 정리했습니다. 개요에서 흐름을 보고, 종목에서 후보를
              고르고, 편집에서 바로 수정하는 구조입니다.
            </p>
          </div>
          <p className="hero-inline-note">상위 테마: {topThemeSummary}</p>
        </div>

        <div className="hero-actions">
          <label className="primary-cta portfolio-upload">
            엑셀 업로드
            <input className="sr-only" type="file" accept=".xlsx,.xls,.csv" onChange={handleUploadFile} />
          </label>
          <button
            className="secondary-cta"
            type="button"
            onClick={() => {
              setRows(initialRows);
              setSelectedRowId(initialRows[0]?.rowId ?? "");
              setDraft(initialRows[0] ? { ...initialRows[0] } : null);
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

      <div className="inline-status-bar">
        <p className="inline-status">{statusMessage}</p>
      </div>

      {workspaceTab === "overview" ? (
        <>
          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <section className="panel">
              <div className="section-head">
                <div>
                  <p className="section-kicker">요약</p>
                  <h2>한눈 요약</h2>
                </div>
                <span className="badge">{snapshot.holdingCount}개 종목</span>
              </div>

              <div className="portfolio-metric-grid mt-5">
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
                  <span>국가 수</span>
                  <strong>{snapshot.countries}</strong>
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
                  <span>추가 매수 여력</span>
                  <strong>{snapshot.cashDrag > 0 ? formatPct(snapshot.cashDrag) : "0.00%"}</strong>
                </article>
                <article className="portfolio-stat-card">
                  <span>목표 초과 비중</span>
                  <strong>
                    {formatPct(
                      snapshot.trimCandidates.reduce(
                        (sum, row) => sum + (row.actualWeightPct - row.targetWeightPct),
                        0,
                      ),
                    )}
                  </strong>
                </article>
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

            <aside className="stack gap-6">
              <section className="panel">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">핵심</p>
                    <h2>핵심 보유군</h2>
                  </div>
                </div>
                <div className="stack gap-3">
                  {snapshot.coreHoldings.map((row) => (
                    <article className="portfolio-holding-card" key={row.rowId}>
                      <div className="dog-card-top">
                        <div>
                          <p className="dog-name">{row.name}</p>
                          <p className="muted-copy">
                            {row.marketScope} · {row.assetClass} · {row.theme}
                          </p>
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
              </section>
            </aside>
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <p className="section-kicker">리밸런싱</p>
                <h2>우선 확인 종목</h2>
              </div>
            </div>

            <div className="portfolio-priority-grid mt-5">
              <section className="portfolio-priority-card">
                <div className="section-head">
                  <div>
                    <p className="section-kicker">매수</p>
                    <h2>추가매수 우선순위</h2>
                  </div>
                </div>
                <div className="stack gap-2">
                  {snapshot.buyCandidates.map((row) => (
                    <button
                      key={row.rowId}
                      className="priority-row"
                      type="button"
                      onClick={() => selectRow(row)}
                    >
                      <div>
                        <strong>{row.name}</strong>
                        <p>{row.theme} · {row.marketScope}</p>
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
                    <h2>비중축소 우선순위</h2>
                  </div>
                </div>
                <div className="stack gap-2">
                  {snapshot.trimCandidates.map((row) => (
                    <button
                      key={row.rowId}
                      className="priority-row"
                      type="button"
                      onClick={() => selectRow(row)}
                    >
                      <div>
                        <strong>{row.name}</strong>
                        <p>{row.theme} · {row.marketScope}</p>
                      </div>
                      <span className="gap-pill gap-pill-trim">{formatGap(row.actualWeightPct, row.targetWeightPct)}</span>
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
                  {snapshot.trimCandidates.map((row) => (
                    <article className="analysis-security-card" key={row.rowId}>
                      <div className="position-card-top">
                        <div>
                          <p className="dog-name">{row.name}</p>
                          <p className="muted-copy">
                            {row.theme} · {row.marketScope} · {formatGap(row.actualWeightPct, row.targetWeightPct)}
                          </p>
                        </div>
                        <span className="action-label action-label-trim">비중축소 검토</span>
                      </div>
                      <ul className="analysis-bullet-list">
                        {buildActionReasons(row).map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                      <div className="analysis-meta-grid">
                        <div>
                          <span>전망</span>
                          <strong>{buildOutlook(row)}</strong>
                        </div>
                        <div>
                          <span>밸류 / 해석</span>
                          <strong>{buildValuationLens(row)}</strong>
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
                  {snapshot.buyCandidates.map((row) => (
                    <article className="analysis-security-card" key={row.rowId}>
                      <div className="position-card-top">
                        <div>
                          <p className="dog-name">{row.name}</p>
                          <p className="muted-copy">
                            {row.theme} · {row.marketScope} · {formatGap(row.actualWeightPct, row.targetWeightPct)}
                          </p>
                        </div>
                        <span className="action-label action-label-buy">추가매수 검토</span>
                      </div>
                      <ul className="analysis-bullet-list">
                        {buildActionReasons(row).map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                      <div className="analysis-meta-grid">
                        <div>
                          <span>전망</span>
                          <strong>{buildOutlook(row)}</strong>
                        </div>
                        <div>
                          <span>밸류 / 해석</span>
                          <strong>{buildValuationLens(row)}</strong>
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

                <div className="position-tag-row">
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
                <div className="portfolio-classification-grid">
                  <div>
                    <span>국가</span>
                    <strong>{selectedRow.country || "-"}</strong>
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
