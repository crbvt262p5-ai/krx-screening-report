"use client";

import { useState } from "react";
import type { PortfolioPosition } from "@/lib/portfolio-dashboard";
import { buildRetirementSnapshot } from "@/lib/retirement-portfolio";

type RetirementDashboardProps = {
  rows: PortfolioPosition[];
};

type RetirementTab = "summary" | "products";

function formatCurrency(value: number) {
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}

function formatSignedCurrency(value: number) {
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded.toLocaleString("ko-KR")}원`;
}

function formatPct(value: number, signed = false) {
  return `${signed && value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function RetirementDashboard({ rows }: RetirementDashboardProps) {
  const [tab, setTab] = useState<RetirementTab>("summary");
  const snapshot = buildRetirementSnapshot(rows);

  if (rows.length === 0) {
    return (
      <main className="retirement-shell retirement-empty-shell">
        <section className="retirement-empty-card">
          <span>NH투자증권 DC</span>
          <h1>DC 원장을 준비하고 있어요</h1>
          <p>DC 캡처 데이터를 비공개 저장소에 올리면 이 섹션에 별도로 표시됩니다.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="retirement-shell">
      <section className="retirement-hero">
        <div className="retirement-hero-head">
          <div>
            <p>NH INVESTMENT · DC</p>
            <h1>퇴직연금 자산</h1>
          </div>
          <span className="retirement-asof">2026.08.07 캡처 기준</span>
        </div>

        <div className="retirement-balance">
          <span>총 평가금액</span>
          <strong>{formatCurrency(snapshot.totalEvaluation)}</strong>
          <b className={snapshot.totalProfit < 0 ? "loss-text" : "gain-text"}>
            {formatSignedCurrency(snapshot.totalProfit)} ({formatPct(snapshot.totalReturnPct, true)})
          </b>
        </div>

        <div className="retirement-hero-metrics">
          <article>
            <span>매입금액</span>
            <strong>{formatCurrency(snapshot.totalPurchase)}</strong>
          </article>
          <article>
            <span>보유 상품</span>
            <strong>{rows.length}개</strong>
          </article>
          <article>
            <span>현금성 재원</span>
            <strong>{formatCurrency(snapshot.cash)}</strong>
          </article>
        </div>
      </section>

      <nav className="retirement-tabs" aria-label="DC 상세 화면">
        <button className={tab === "summary" ? "active" : ""} type="button" onClick={() => setTab("summary")}>요약</button>
        <button className={tab === "products" ? "active" : ""} type="button" onClick={() => setTab("products")}>보유상품</button>
      </nav>

      {tab === "summary" ? (
        <>
          <section className="retirement-allocation-grid">
            <article className="retirement-allocation-card retirement-allocation-main">
              <div>
                <p className="section-kicker">ASSET ALLOCATION</p>
                <h2>DC 자산배분</h2>
              </div>
              <div className="retirement-allocation-visual">
                <div
                  className="retirement-donut"
                  style={{
                    background: `conic-gradient(#176b46 0 ${snapshot.safeAssetPct}%, #ef9f45 ${snapshot.safeAssetPct}% 100%)`,
                  }}
                >
                  <span><b>{formatPct(snapshot.safeAssetPct)}</b>안전자산</span>
                </div>
                <div className="retirement-allocation-legend">
                  <div><i className="safe" /><span>안전자산</span><strong>{formatCurrency(snapshot.safeAssets)}</strong><b>{formatPct(snapshot.safeAssetPct)}</b></div>
                  <div><i className="risk" /><span>주식형 ETF</span><strong>{formatCurrency(snapshot.etfAssets)}</strong><b>{formatPct(snapshot.etfPct)}</b></div>
                  <div><i className="cash" /><span>현금성자산</span><strong>{formatCurrency(snapshot.cash)}</strong><b>{formatPct(snapshot.cashPct)}</b></div>
                </div>
              </div>
            </article>

            <article className="retirement-insight-card">
              <div>
                <p className="section-kicker">DC CHECKUP</p>
                <h2>운용 점검</h2>
              </div>
              <div className="retirement-insight-list">
                <article>
                  <span>손실 기여도가 큰 상품</span>
                  <strong>{snapshot.largestLoss?.row.name ?? "없음"}</strong>
                  <p>
                    {snapshot.largestLoss
                      ? `평가손실 ${formatSignedCurrency(snapshot.largestLoss.metrics.profit)}으로 전체 순손실의 약 ${formatPct(snapshot.largestLossContributionPct)} 규모입니다.`
                      : "현재 손실 상품이 없습니다."}
                  </p>
                </article>
                <article>
                  <span>리밸런싱 여력</span>
                  <strong>현금성 {formatPct(snapshot.cashPct)}</strong>
                  <p>현금성자산은 한 번에 투입하기보다 목표 안전자산 비중을 정한 뒤 분할 배치하는 편이 좋습니다.</p>
                </article>
                <article>
                  <span>현재 구조</span>
                  <strong>안전자산 {formatPct(snapshot.safeAssetPct)} · ETF {formatPct(snapshot.etfPct)}</strong>
                  <p>DC는 일반계좌와 달리 장기 자산배분 기준으로 점검하며, 단기 매수·매도 신호는 적용하지 않습니다.</p>
                </article>
              </div>
            </article>
          </section>

          <section className="retirement-top-products">
            <div className="retirement-section-head">
              <div>
                <p className="section-kicker">HOLDINGS</p>
                <h2>비중 상위 상품</h2>
              </div>
              <button type="button" onClick={() => setTab("products")}>전체 보기</button>
            </div>
            <div className="retirement-product-strip">
              {snapshot.positions.slice(0, 4).map(({ row, metrics }) => (
                <article key={row.rowId}>
                  <span>{row.assetClass}</span>
                  <strong>{row.name}</strong>
                  <div><b>{formatCurrency(metrics.evaluation)}</b><em>{formatPct(row.actualWeightPct)}</em></div>
                </article>
              ))}
            </div>
          </section>
        </>
      ) : (
        <section className="retirement-products-panel">
          <div className="retirement-section-head">
            <div>
              <p className="section-kicker">ALL PRODUCTS</p>
              <h2>DC 보유상품</h2>
            </div>
            <span>평가금액 순</span>
          </div>
          <div className="retirement-product-list">
            {snapshot.positions.map(({ row, metrics }) => (
              <article key={row.rowId}>
                <div className="retirement-product-icon">{row.assetClass === "ETF" ? "ETF" : row.assetClass.slice(0, 2)}</div>
                <div className="retirement-product-name">
                  <strong>{row.name}</strong>
                  <span>{row.subTheme}{metrics.quantity ? ` · ${metrics.quantity}${row.assetClass === "ETF" ? "주" : ""}` : ""}</span>
                </div>
                <div className="retirement-product-value">
                  <strong>{formatCurrency(metrics.evaluation)}</strong>
                  <span>{formatPct(row.actualWeightPct)} 비중</span>
                </div>
                <div className={`retirement-product-pnl ${metrics.profit < 0 ? "loss-text" : "gain-text"}`}>
                  <strong>{formatSignedCurrency(metrics.profit)}</strong>
                  <span>{formatPct(metrics.returnPct, true)}</span>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
