import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { ONBOARDED_COOKIE, ONBOARDED_VALUE, ONBOARDED_COOKIE_OPTIONS, RETURN_TO_COOKIE, isValidReturnTo } from "@/lib/cookies";

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
  let meResp: Response;
  try {
    meResp = await fetch(`${apiUrl}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
    });
  } catch {
    return NextResponse.redirect(new URL("/login?error=backend", origin));
  }

  if (meResp.ok) {
    const user = await meResp.json();
    if (user.splitwise_connected) {
      const returnTo = request.cookies.get(RETURN_TO_COOKIE)?.value;
      const destination = isValidReturnTo(returnTo) ? returnTo : "/";
      const response = NextResponse.redirect(new URL(destination, origin));
      response.cookies.set(ONBOARDED_COOKIE, ONBOARDED_VALUE, ONBOARDED_COOKIE_OPTIONS);
      response.cookies.set(RETURN_TO_COOKIE, "", { path: "/", maxAge: 0 });
      return response;
    }
    return NextResponse.redirect(new URL("/onboarding", origin));
  }

  if (meResp.status === 404) {
    return NextResponse.redirect(new URL("/onboarding", origin));
  }

  return NextResponse.redirect(new URL("/login?error=backend", origin));
}
