"use client";

import { useDeferredValue, useMemo, useState } from "react";
import * as XLSX from "xlsx";
import { hasSupabaseEnv } from "@/lib/env";
import {
  buildPortfolioSnapshot,
  normalizePortfolioRecords,
  type PortfolioPosition,
} from "@/lib/portfolio-dashboard";

type PortfolioDashboardProps = {
  initialRows: PortfolioPosition[];
};

function formatPct(value: number) {
  return `${value.toFixed(2)}%`;
}

function formatGap(actualWeightPct: number, targetWeightPct: number) {
  const gap = targetWeightPct - actualWeightPct;
  return `${gap > 0 ? "+" : ""}${gap.toFixed(2)}%p`;
}

export function PortfolioDashboard({ initialRows }: PortfolioDashboardProps) {
  const usesCloudStorage = hasSupabaseEnv();
  const [rows, setRows] = useState(initialRows);
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

  async function handleUploadFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const records = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
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
    const worksheet = XLSX.utils.json_to_sheet(exportRows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "portfolio");
    XLSX.writeFile(workbook, "portfolio_dashboard_template.xlsx");
    setStatusMessage("현재 화면 기준으로 엑셀 템플릿을 내려받았습니다.");
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

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <section className="hero-panel">
        <div className="space-y-3">
          <p className="eyebrow">포트 대시보드</p>
          <div className="space-y-2">
            <h1 className="hero-title">포트 조정용 운영 화면</h1>
            <p className="hero-copy">
              국내/해외, 테마, 전략, 추세, 실제 비중, 목표 비중, 액션을 한 번에 보고 바로 수정하는
              용도입니다.
            </p>
          </div>
          <p className="hero-inline-note">상위 테마: {topThemeSummary}</p>
        </div>

        <div className="hero-actions">
          <label className="primary-cta portfolio-upload">
            엑셀 업로드
            <input
              className="sr-only"
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={handleUploadFile}
            />
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
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">요약</p>
              <h2>한눈 요약</h2>
            </div>
            <span className="badge">{snapshot.holdingCount}개 종목</span>
          </div>

          <div className="inline-status-bar">
            <p className="inline-status">{statusMessage}</p>
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

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="section-kicker">탐색</p>
              <h2>보유 종목 탐색</h2>
            </div>
            <span className="badge">{filteredRows.length}개 표시</span>
          </div>

          <div className="portfolio-priority-grid mt-5">
            <section className="portfolio-priority-card">
              <div className="section-head">
                <div>
                  <p className="section-kicker">리밸런싱</p>
                  <h2>추가매수 우선순위</h2>
                </div>
              </div>
              <div className="stack gap-2">
                {snapshot.buyCandidates.map((row) => (
                  <button
                    key={row.rowId}
                    className="priority-row"
                    type="button"
                    onClick={() => {
                      setSelectedRowId(row.rowId);
                      setDraft({ ...row });
                    }}
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
                  <p className="section-kicker">리밸런싱</p>
                  <h2>비중축소 우선순위</h2>
                </div>
              </div>
              <div className="stack gap-2">
                {snapshot.trimCandidates.map((row) => (
                  <button
                    key={row.rowId}
                    className="priority-row"
                    type="button"
                    onClick={() => {
                      setSelectedRowId(row.rowId);
                      setDraft({ ...row });
                    }}
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
            <select
              className="portfolio-input"
              value={scopeFilter}
              onChange={(event) => setScopeFilter(event.target.value)}
            >
              <option value="전체">전체 지역</option>
              <option value="국내">국내</option>
              <option value="해외">해외</option>
            </select>
            <select
              className="portfolio-input"
              value={actionFilter}
              onChange={(event) => setActionFilter(event.target.value)}
            >
              <option value="전체">전체 액션</option>
              {snapshot.actionMix.map((item) => (
                <option key={item.label} value={item.label}>
                  {item.label}
                </option>
              ))}
            </select>
            <select
              className="portfolio-input"
              value={sortKey}
              onChange={(event) => setSortKey(event.target.value)}
            >
              <option value="actual_desc">실제 비중순</option>
              <option value="target_desc">목표 비중순</option>
              <option value="gap_desc">언더웨이트 큰 순</option>
              <option value="gap_asc">오버웨이트 큰 순</option>
              <option value="action">액션순</option>
              <option value="name_asc">이름순</option>
            </select>
          </div>

          <div className="portfolio-table-wrap mt-5">
            <table className="portfolio-table">
              <thead>
                <tr>
                  <th>종목</th>
                  <th>지역</th>
                  <th>자산</th>
                  <th>테마</th>
                  <th>전략</th>
                  <th>추세</th>
                  <th>실제</th>
                  <th>목표</th>
                  <th>갭</th>
                  <th>액션</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => (
                  <tr
                    className={`portfolio-row portfolio-row-${actionTone(row.plannedAction)} ${
                      selectedRow?.rowId === row.rowId ? "portfolio-row-selected" : ""
                    }`}
                    key={row.rowId}
                    onClick={() => {
                      setSelectedRowId(row.rowId);
                      setDraft({ ...row });
                    }}
                  >
                    <td>
                      <strong>{row.name}</strong>
                      <div className="subtle">{row.ticker}</div>
                    </td>
                    <td>{row.marketScope}</td>
                    <td>{row.assetClass}</td>
                    <td>
                      <strong>{row.theme}</strong>
                      <div className="subtle">{row.subTheme || "-"}</div>
                    </td>
                    <td>
                      <strong>{row.strategy || "-"}</strong>
                      <div className="subtle">{row.styleBucket || "-"}</div>
                    </td>
                    <td>
                      <strong>{row.trendView || "-"}</strong>
                      <div className="subtle">{row.cycleView || "-"}</div>
                    </td>
                    <td>{formatPct(row.actualWeightPct)}</td>
                    <td>{formatPct(row.targetWeightPct)}</td>
                    <td>
                      <span className={`gap-pill gap-pill-${actionTone(row.plannedAction)}`}>
                        {formatGap(row.actualWeightPct, row.targetWeightPct)}
                      </span>
                    </td>
                    <td>
                      <strong className={`action-label action-label-${actionTone(row.plannedAction)}`}>
                        {row.plannedAction}
                      </strong>
                      <div className="subtle">{row.notes || "-"}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="panel">
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
                      <input
                        className="portfolio-input"
                        value={draft.theme}
                        onChange={(event) => handleDraftChange("theme", event.target.value)}
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>세부 테마</span>
                      <input
                        className="portfolio-input"
                        value={draft.subTheme}
                        onChange={(event) => handleDraftChange("subTheme", event.target.value)}
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>전략</span>
                      <input
                        className="portfolio-input"
                        value={draft.strategy}
                        onChange={(event) => handleDraftChange("strategy", event.target.value)}
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>추세</span>
                      <input
                        className="portfolio-input"
                        value={draft.trendView}
                        onChange={(event) => handleDraftChange("trendView", event.target.value)}
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>실제 비중</span>
                      <input
                        className="portfolio-input"
                        type="number"
                        step="0.01"
                        value={draft.actualWeightPct}
                        onChange={(event) =>
                          handleDraftChange("actualWeightPct", Number(event.target.value))
                        }
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>목표 비중</span>
                      <input
                        className="portfolio-input"
                        type="number"
                        step="0.01"
                        value={draft.targetWeightPct}
                        onChange={(event) =>
                          handleDraftChange("targetWeightPct", Number(event.target.value))
                        }
                      />
                    </label>
                    <label className="portfolio-field">
                      <span>액션</span>
                      <select
                        className="portfolio-input"
                        value={draft.plannedAction}
                        onChange={(event) => handleDraftChange("plannedAction", event.target.value)}
                      >
                        <option value="추가매수 검토">추가매수 검토</option>
                        <option value="비중축소 검토">비중축소 검토</option>
                        <option value="정리 검토">정리 검토</option>
                        <option value="보유 유지">보유 유지</option>
                        <option value="보유/관찰">보유/관찰</option>
                      </select>
                    </label>
                    <label className="portfolio-field">
                      <span>타이밍</span>
                      <input
                        className="portfolio-input"
                        value={draft.timingView}
                        onChange={(event) => handleDraftChange("timingView", event.target.value)}
                      />
                    </label>
                    <label className="portfolio-field portfolio-field-wide">
                      <span>메모</span>
                      <textarea
                        className="portfolio-textarea"
                        value={draft.notes}
                        onChange={(event) => handleDraftChange("notes", event.target.value)}
                      />
                    </label>
                    <div className="hero-actions">
                      <button className="primary-small" type="button" onClick={handleApplyDraft}>
                        화면 반영
                      </button>
                      <button
                        className="secondary-cta"
                        type="button"
                        onClick={handleSaveToFile}
                        disabled={isSavingFile}
                      >
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
        </aside>
      </section>
    </main>
  );
}
