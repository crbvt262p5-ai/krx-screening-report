import { dogs as mockDogs } from "@/lib/mock-data";
import { DogProfile } from "@/lib/types";
import { hasSupabaseEnv } from "@/lib/env";
import { getSupabaseServerClient } from "@/lib/supabase";
import { DogRow, mapDogRow } from "@/lib/repositories/mappers";

export async function getDogs(): Promise<DogProfile[]> {
  if (!hasSupabaseEnv()) {
    return mockDogs;
  }

  const supabase = getSupabaseServerClient();
  if (!supabase) {
    return mockDogs;
  }

  const { data, error } = await supabase
    .from("dogs")
    .select("id, name, weight_kg, age_group, activity_factor, is_neutered, note")
    .order("created_at", { ascending: false });

  if (error || !data) {
    return mockDogs;
  }

  return (data as DogRow[]).map(mapDogRow);
}
