import { NextResponse, type NextRequest } from "next/server";
import { PORTFOLIO_SESSION_COOKIE } from "@/lib/portfolio-auth";

export async function POST(request: NextRequest) {
  const response = NextResponse.redirect(new URL("/portfolio/login", request.url), 303);
  response.cookies.set(PORTFOLIO_SESSION_COOKIE, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: 0,
    path: "/",
  });
  return response;
}
