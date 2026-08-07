"use client";

import { useState } from "react";
import { PortfolioDashboard } from "@/components/portfolio-dashboard";
import { RetirementDashboard } from "@/components/retirement-dashboard";
import type { PortfolioPosition } from "@/lib/portfolio-dashboard";
import type { PortfolioScreeningRecord } from "@/lib/portfolio-screening-shared";
import { buildRetirementSnapshot } from "@/lib/retirement-portfolio";

type PortfolioWorkspaceProps = {
  initialRows: PortfolioPosition[];
  screeningRecords: PortfolioScreeningRecord[];
};

type AccountSection = "taxable" | "dc";

function formatCompactCurrency(value: number) {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(2)}억원`;
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString("ko-KR")}만원`;
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}

export function PortfolioWorkspace({ initialRows, screeningRecords }: PortfolioWorkspaceProps) {
  const [activeAccount, setActiveAccount] = useState<AccountSection>("taxable");
  const taxableRows = initialRows.filter((row) => row.accountSection !== "dc");
  const retirementRows = initialRows.filter((row) => row.accountSection === "dc");
  const retirementSnapshot = buildRetirementSnapshot(retirementRows);

  return (
    <div className="account-workspace">
      <div className="account-switcher-shell">
        <nav className="account-switcher" aria-label="포트폴리오 계좌 구분">
          <button
            className={activeAccount === "taxable" ? "active" : ""}
            type="button"
            onClick={() => setActiveAccount("taxable")}
          >
            <span className="account-switcher-icon">일반</span>
            <div><strong>일반계좌</strong><small>{taxableRows.length}종목 · 국내/해외</small></div>
          </button>
          <button
            className={activeAccount === "dc" ? "active" : ""}
            type="button"
            onClick={() => setActiveAccount("dc")}
          >
            <span className="account-switcher-icon">DC</span>
            <div><strong>NH DC·IRP</strong><small>{retirementRows.length > 0 ? formatCompactCurrency(retirementSnapshot.totalEvaluation) : "업로드 대기"}</small></div>
          </button>
        </nav>
      </div>

      {activeAccount === "taxable" ? (
        <PortfolioDashboard initialRows={taxableRows} screeningRecords={screeningRecords} />
      ) : (
        <RetirementDashboard rows={retirementRows} />
      )}
    </div>
  );
}
