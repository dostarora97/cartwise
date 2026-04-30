import { NextResponse, type NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const state = searchParams.get("state");

  if (!code || !state) {
    return NextResponse.redirect(
      new URL("/onboarding?splitwise=error", request.url),
    );
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const redirectUri = `${new URL(request.url).origin}/auth/connect/splitwise`;

  const resp = await fetch(`${apiUrl}/api/v1/auth/splitwise/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
  });

  const path = resp.ok
    ? "/onboarding?splitwise=success"
    : "/onboarding?splitwise=error";
  return NextResponse.redirect(new URL(path, request.url));
}
