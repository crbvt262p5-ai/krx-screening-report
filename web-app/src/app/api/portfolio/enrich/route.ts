import { NextResponse, type NextRequest } from "next/server";
import { normalizePortfolioRecords, type PortfolioPosition } from "@/lib/portfolio-dashboard";
import { enrichPortfolioRows } from "@/lib/portfolio-enrichment";

export async function POST(request: NextRequest) {
  try {
    const payload = (await request.json()) as { rows?: PortfolioPosition[] };
    const rows = Array.isArray(payload.rows) ? normalizePortfolioRecords(payload.rows) : [];

    if (rows.length === 0) {
      return NextResponse.json({ error: "자동 채울 포트 데이터가 없습니다." }, { status: 400 });
    }

    const result = await enrichPortfolioRows(rows);
    return NextResponse.json({ ok: true, ...result });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "밸류 자동 채우기 중 문제가 발생했습니다.",
      },
      { status: 500 },
    );
  }
}
