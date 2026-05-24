import { NextResponse } from "next/server";
import { hasSupabaseEnv } from "@/lib/env";

export async function GET() {
  return NextResponse.json({
    ok: true,
    service: "dog-food-tracker-web",
    timestamp: new Date().toISOString(),
    supabaseConfigured: hasSupabaseEnv(),
  });
}
