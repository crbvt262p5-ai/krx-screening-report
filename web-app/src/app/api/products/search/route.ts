import { NextRequest, NextResponse } from "next/server";
import { searchExternalProducts, searchLocalProducts } from "@/lib/search";
import { ProductKind } from "@/lib/types";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";
  const kind = (request.nextUrl.searchParams.get("kind")?.trim() ?? "food") as ProductKind;

  if (!query) {
    return NextResponse.json({ error: "검색어를 입력해 주세요." }, { status: 400 });
  }

  if (kind !== "food" && kind !== "treat") {
    return NextResponse.json({ error: "제품 종류가 올바르지 않습니다." }, { status: 400 });
  }

  try {
    const localResults = await searchLocalProducts(query, kind);
    const externalResults = await searchExternalProducts(query, kind);

    return NextResponse.json({
      query,
      kind,
      localResults,
      externalResults,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "검색 중 문제가 발생했습니다.",
        query,
        kind,
      },
      { status: 502 },
    );
  }
}
