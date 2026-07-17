import { writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse, type NextRequest } from "next/server";
import { hasSupabaseEnv, isVercelRuntime } from "@/lib/env";
import { normalizePortfolioRecords, type PortfolioPosition } from "@/lib/portfolio-dashboard";
import { upsertPortfolioPositions } from "@/lib/repositories/portfolio";

function resolvePortfolioPath() {
  return path.resolve(process.cwd(), "data", "portfolio_positions.csv");
}

function toExportRows(rows: PortfolioPosition[]) {
  return rows.map((row) => ({
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
}

export async function POST(request: NextRequest) {
  try {
    const payload = (await request.json()) as { rows?: PortfolioPosition[] };
    const rows = Array.isArray(payload.rows) ? normalizePortfolioRecords(payload.rows) : [];

    if (rows.length === 0) {
      return NextResponse.json({ error: "저장할 포트 데이터가 없습니다." }, { status: 400 });
    }

    if (hasSupabaseEnv()) {
      const result = await upsertPortfolioPositions(rows);
      return NextResponse.json({
        ok: true,
        savedCount: rows.length,
        persistence: result.ok ? "supabase" : "csv",
      });
    }

    if (isVercelRuntime()) {
      return NextResponse.json(
        {
          error: "Vercel 배포에서는 Supabase 연결 없이 CSV 저장을 지원하지 않습니다.",
        },
        { status: 501 },
      );
    }

    const { utils } = await import("xlsx");
    const worksheet = utils.json_to_sheet(toExportRows(rows));
    const csv = utils.sheet_to_csv(worksheet);
    await writeFile(resolvePortfolioPath(), `\uFEFF${csv}`, "utf-8");

    return NextResponse.json({ ok: true, savedCount: rows.length, persistence: "csv" });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "portfolio CSV 저장 중 문제가 발생했습니다.",
      },
      { status: 500 },
    );
  }
}
