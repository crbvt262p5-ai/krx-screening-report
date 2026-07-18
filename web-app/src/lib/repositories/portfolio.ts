import { PortfolioPosition } from "@/lib/portfolio-dashboard";
import { hasSupabaseEnv } from "@/lib/env";
import { getSupabaseServerClient } from "@/lib/supabase";
import {
  mapPortfolioPositionRow,
  PortfolioPositionRow,
  toPortfolioPositionRow,
} from "@/lib/repositories/mappers";

export async function getPortfolioPositions(): Promise<PortfolioPosition[]> {
  if (!hasSupabaseEnv()) {
    return [];
  }

  const supabase = getSupabaseServerClient();
  if (!supabase) {
    return [];
  }

  const { data, error } = await supabase
    .from("portfolio_positions")
    .select(
      "row_id, ticker, name, market_scope, asset_class, country, theme, theme_category, sub_theme, strategy, style_bucket, trend_view, cycle_view, conviction, fx_exposure, timing_view, actual_weight_pct, target_weight_pct, per, pbr, eps, forward_per, planned_action, notes, sort_order",
    )
    .order("sort_order", { ascending: true });

  if (error || !data) {
    return [];
  }

  return (data as PortfolioPositionRow[]).map(mapPortfolioPositionRow);
}

export async function upsertPortfolioPositions(rows: PortfolioPosition[]) {
  if (!hasSupabaseEnv()) {
    return { ok: false as const, reason: "missing_env" };
  }

  const supabase = getSupabaseServerClient();
  if (!supabase) {
    return { ok: false as const, reason: "missing_client" };
  }

  const payload = rows.map((row, index) => toPortfolioPositionRow(row, index));
  const { error } = await supabase
    .from("portfolio_positions")
    .upsert(payload, { onConflict: "row_id" });

  if (error) {
    throw new Error("포트폴리오 저장에 실패했습니다.");
  }

  return { ok: true as const, count: payload.length };
}
