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
  const sections = new Set(rows.map((row) => row.accountSection));

  for (const section of sections) {
    const sectionRows = payload.filter((_, index) => rows[index].accountSection === section);
    const rowIds = sectionRows.map((row) => row.row_id);
    let deleteQuery = supabase
      .from("portfolio_positions")
      .delete()
      .not("row_id", "in", `(${rowIds.map((rowId) => `"${rowId}"`).join(",")})`);

    deleteQuery =
      section === "dc"
        ? deleteQuery.like("row_id", "DC-%")
        : deleteQuery.not("row_id", "like", "DC-%");

    const { error: deleteError } = await deleteQuery;
    if (deleteError) {
      throw new Error(`${section === "dc" ? "DC" : "일반계좌"} 포트폴리오 정리에 실패했습니다.`);
    }
  }

  const { error } = await supabase
    .from("portfolio_positions")
    .upsert(payload, { onConflict: "row_id" });

  if (error) {
    throw new Error("포트폴리오 저장에 실패했습니다.");
  }

  return { ok: true as const, count: payload.length };
}
