import { feedingLogs as mockFeedingLogs } from "@/lib/mock-data";
import { FeedingLog } from "@/lib/types";
import { hasSupabaseEnv } from "@/lib/env";
import { getSupabaseServerClient } from "@/lib/supabase";
import { FeedingLogRow, mapFeedingLogRow } from "@/lib/repositories/mappers";

function sortLogs(logs: FeedingLog[]) {
  return [...logs].sort((left, right) => right.logDate.localeCompare(left.logDate));
}

export async function getFeedingLogs(): Promise<FeedingLog[]> {
  if (!hasSupabaseEnv()) {
    return sortLogs(mockFeedingLogs);
  }

  const supabase = getSupabaseServerClient();
  if (!supabase) {
    return sortLogs(mockFeedingLogs);
  }

  const { data, error } = await supabase
    .from("feeding_logs")
    .select(
      "id, dog_id, log_date, food_product_id, treat_product_id, food_grams, treat_pieces, food_kcal, treat_kcal, total_kcal, recommended_kcal, note",
    )
    .order("log_date", { ascending: false })
    .limit(24);

  if (error || !data) {
    return sortLogs(mockFeedingLogs);
  }

  return sortLogs((data as FeedingLogRow[]).map(mapFeedingLogRow));
}
