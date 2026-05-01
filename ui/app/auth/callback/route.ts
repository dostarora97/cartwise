import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

function baseUrl(request: NextRequest): string {
  const proto = request.headers.get("x-forwarded-proto") || "http";
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  return `${proto}://${host}`;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const origin = baseUrl(request);

  if (!code) {
    return NextResponse.redirect(new URL("/login", origin));
  }

  const supabase = await createClient();
  const { data: sessionData } = await supabase.auth.exchangeCodeForSession(code);

  if (!sessionData?.session) {
    return NextResponse.redirect(new URL("/login", origin));
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL!;
  const meResp = await fetch(`${apiUrl}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
  });

  if (meResp.ok) {
    const user = await meResp.json();
    if (user.splitwise_connected) {
      return NextResponse.redirect(new URL("/", origin));
    }
  }

  return NextResponse.redirect(new URL("/onboarding", origin));
}
