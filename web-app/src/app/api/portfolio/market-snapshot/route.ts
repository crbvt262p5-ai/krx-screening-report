import { NextResponse, type NextRequest } from "next/server";
import { normalizePortfolioRecords, type PortfolioPosition } from "@/lib/portfolio-dashboard";
import { loadPortfolioMarketSnapshots } from "@/lib/portfolio-live-market";

export async function POST(request: NextRequest) {
  try {
    const payload = (await request.json()) as { rows?: PortfolioPosition[] };
    const rows = Array.isArray(payload.rows) ? normalizePortfolioRecords(payload.rows) : [];

    if (rows.length === 0) {
      return NextResponse.json({ error: "시세를 확인할 포트 데이터가 없습니다." }, { status: 400 });
    }

    const snapshots = await loadPortfolioMarketSnapshots(rows);
    return NextResponse.json({
      ok: true,
      snapshots,
      fetchedAt: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "실시간 시세 조회 중 문제가 발생했습니다.",
      },
      { status: 500 },
    );
  }
}
