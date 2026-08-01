import { NextResponse, type NextRequest } from "next/server";
import {
  isPortfolioAuthConfigured,
  PORTFOLIO_SESSION_COOKIE,
  verifyPortfolioSession,
} from "@/lib/portfolio-auth";

const PUBLIC_AUTH_PATHS = new Set([
  "/portfolio/login",
  "/api/portfolio/auth/login",
  "/api/portfolio/auth/logout",
]);

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_AUTH_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  if (!isPortfolioAuthConfigured()) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "포트폴리오 보안 설정이 필요합니다." }, { status: 503 });
    }

    const loginUrl = new URL("/portfolio/login", request.url);
    loginUrl.searchParams.set("error", "config");
    return NextResponse.redirect(loginUrl);
  }

  const token = request.cookies.get(PORTFOLIO_SESSION_COOKIE)?.value;
  if (await verifyPortfolioSession(token)) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "로그인이 필요합니다." }, { status: 401 });
  }

  const loginUrl = new URL("/portfolio/login", request.url);
  loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/portfolio/:path*", "/api/portfolio/:path*"],
};
