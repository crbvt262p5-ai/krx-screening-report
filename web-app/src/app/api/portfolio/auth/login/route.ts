import { NextResponse, type NextRequest } from "next/server";
import {
  createPortfolioSessionToken,
  isPortfolioAuthConfigured,
  PORTFOLIO_SESSION_COOKIE,
  PORTFOLIO_SESSION_MAX_AGE,
  verifyPortfolioPassword,
} from "@/lib/portfolio-auth";

function safeNextPath(value: FormDataEntryValue | null) {
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//")
    ? value
    : "/portfolio";
}

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const password = formData.get("password");
  const nextPath = safeNextPath(formData.get("next"));

  if (!isPortfolioAuthConfigured()) {
    return NextResponse.redirect(new URL("/portfolio/login?error=config", request.url), 303);
  }

  if (typeof password !== "string" || !(await verifyPortfolioPassword(password))) {
    const loginUrl = new URL("/portfolio/login", request.url);
    loginUrl.searchParams.set("error", "invalid");
    loginUrl.searchParams.set("next", nextPath);
    return NextResponse.redirect(loginUrl, 303);
  }

  const token = await createPortfolioSessionToken();
  if (!token) {
    return NextResponse.redirect(new URL("/portfolio/login?error=config", request.url), 303);
  }

  const response = NextResponse.redirect(new URL(nextPath, request.url), 303);
  response.cookies.set(PORTFOLIO_SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: PORTFOLIO_SESSION_MAX_AGE,
    path: "/",
  });
  return response;
}
