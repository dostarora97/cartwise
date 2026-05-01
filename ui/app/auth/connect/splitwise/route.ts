import { NextResponse, type NextRequest } from "next/server";
import { ONBOARDED_COOKIE, ONBOARDED_VALUE, ONBOARDED_COOKIE_OPTIONS } from "@/lib/cookies";

function baseUrl(request: NextRequest): string {
  const proto = request.headers.get("x-forwarded-proto") || "http";
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  return `${proto}://${host}`;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const origin = baseUrl(request);

  if (!code || !state) {
    return NextResponse.redirect(new URL("/onboarding?splitwise=error", origin));
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL!;
  const redirectUri = `${origin}/auth/connect/splitwise`;

  const resp = await fetch(`${apiUrl}/api/v1/auth/splitwise/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
  });

  if (resp.ok) {
    const response = NextResponse.redirect(new URL("/", origin));
    response.cookies.set(ONBOARDED_COOKIE, ONBOARDED_VALUE, ONBOARDED_COOKIE_OPTIONS);
    return response;
  }

  return NextResponse.redirect(new URL("/onboarding?splitwise=error", origin));
}
