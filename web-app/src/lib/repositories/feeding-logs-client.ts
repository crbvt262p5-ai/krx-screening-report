"use client";

import { FeedingLog } from "@/lib/types";
import { hasSupabaseEnv } from "@/lib/env";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import {
  FeedingLogRow,
  mapFeedingLogRow,
  toFeedingLogRow,
} from "@/lib/repositories/mappers";

const FEEDING_LOG_STORAGE_KEY = "dog-food-app.feeding-logs";

function sortLogs(logs: FeedingLog[]) {
  return [...logs].sort((left, right) => right.logDate.localeCompare(left.logDate));
}

export function hydrateFeedingLogsFromStorage(initialLogs: FeedingLog[]) {
  if (typeof window === "undefined" || hasSupabaseEnv()) {
    return sortLogs(initialLogs);
  }

  try {
    const raw = window.localStorage.getItem(FEEDING_LOG_STORAGE_KEY);
    if (!raw) {
      window.localStorage.setItem(FEEDING_LOG_STORAGE_KEY, JSON.stringify(sortLogs(initialLogs)));
      return sortLogs(initialLogs);
    }

    const parsed = JSON.parse(raw) as FeedingLog[];
    return parsed.length ? sortLogs(parsed) : sortLogs(initialLogs);
  } catch {
    return sortLogs(initialLogs);
  }
}

function saveFeedingLogsToStorage(logs: FeedingLog[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(FEEDING_LOG_STORAGE_KEY, JSON.stringify(sortLogs(logs)));
}

export async function createFeedingLog(log: FeedingLog, currentLogs: FeedingLog[]) {
  if (!hasSupabaseEnv()) {
    const nextLogs = sortLogs([log, ...currentLogs]);
    saveFeedingLogsToStorage(nextLogs);
    return log;
  }

  const supabase = getSupabaseBrowserClient();
  if (!supabase) {
    return log;
  }

  const feedingLogsTable = supabase.from("feeding_logs" as never) as unknown as {
    insert: (
      values: FeedingLogRow,
    ) => {
      select: (query: string) => {
        single: () => Promise<{ data: FeedingLogRow | null; error: Error | null }>;
      };
    };
  };

  const { data, error } = await feedingLogsTable
    .insert(toFeedingLogRow(log))
    .select(
      "id, dog_id, log_date, food_product_id, treat_product_id, food_grams, treat_pieces, food_kcal, treat_kcal, total_kcal, recommended_kcal, note",
    )
    .single();

  if (error || !data) {
    throw new Error("급여 기록 저장에 실패했습니다.");
  }

  return mapFeedingLogRow(data);
}
