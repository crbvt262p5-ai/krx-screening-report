"use client";

import { DogProfile } from "@/lib/types";
import { hasSupabaseEnv } from "@/lib/env";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { DogRow, mapDogRow, toDogRow } from "@/lib/repositories/mappers";

const DOG_STORAGE_KEY = "dog-food-app.dogs";
const SELECTED_DOG_STORAGE_KEY = "dog-food-app.selected-dog-id";

export function hydrateDogsFromStorage(initialDogs: DogProfile[]) {
  if (typeof window === "undefined" || hasSupabaseEnv()) {
    return initialDogs;
  }

  try {
    const raw = window.localStorage.getItem(DOG_STORAGE_KEY);
    if (!raw) {
      window.localStorage.setItem(DOG_STORAGE_KEY, JSON.stringify(initialDogs));
      return initialDogs;
    }

    const parsed = JSON.parse(raw) as DogProfile[];
    return parsed.length ? parsed : initialDogs;
  } catch {
    return initialDogs;
  }
}

function saveDogsToStorage(dogs: DogProfile[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(DOG_STORAGE_KEY, JSON.stringify(dogs));
}

export function getStoredSelectedDogId() {
  if (typeof window === "undefined") {
    return undefined;
  }

  try {
    const selectedDogId = window.localStorage.getItem(SELECTED_DOG_STORAGE_KEY);
    return selectedDogId || undefined;
  } catch {
    return undefined;
  }
}

export function setStoredSelectedDogId(dogId: string) {
  if (typeof window === "undefined" || !dogId) {
    return;
  }

  try {
    window.localStorage.setItem(SELECTED_DOG_STORAGE_KEY, dogId);
  } catch {
    // Best-effort only; ignore storage failures.
  }
}

export async function upsertDogProfile(
  draft: Omit<DogProfile, "id"> & { id?: string },
  currentDogs: DogProfile[],
): Promise<DogProfile> {
  const profile: DogProfile = {
    id: draft.id ?? crypto.randomUUID(),
    name: draft.name,
    weightKg: draft.weightKg,
    ageGroup: draft.ageGroup,
    activityFactor: draft.activityFactor,
    isNeutered: draft.isNeutered,
    note: draft.note,
  };

  if (!hasSupabaseEnv()) {
    const nextDogs = currentDogs.some((dog) => dog.id === profile.id)
      ? currentDogs.map((dog) => (dog.id === profile.id ? profile : dog))
      : [profile, ...currentDogs];
    saveDogsToStorage(nextDogs);
    setStoredSelectedDogId(profile.id);
    return profile;
  }

  const supabase = getSupabaseBrowserClient();
  if (!supabase) {
    return profile;
  }

  const dogsTable = supabase.from("dogs" as never) as unknown as {
    upsert: (
      values: DogRow,
      options: { onConflict: string },
    ) => {
      select: (query: string) => {
        single: () => Promise<{ data: DogRow | null; error: Error | null }>;
      };
    };
  };

  const { data, error } = await dogsTable
    .upsert(toDogRow(profile), { onConflict: "id" })
    .select("id, name, weight_kg, age_group, activity_factor, is_neutered, note")
    .single();

  if (error || !data) {
    throw new Error("강아지 프로필 저장에 실패했습니다.");
  }

  setStoredSelectedDogId(data.id);
  return mapDogRow(data);
}
