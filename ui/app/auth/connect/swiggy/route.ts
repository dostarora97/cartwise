import { NextResponse, type NextRequest } from "next/server";

function baseUrl(request: NextRequest): string {
  const proto = request.headers.get("x-forwarded-proto") || "http";
  const host =
    request.headers.get("x-forwarded-host") ||
    request.headers.get("host") ||
    "localhost:3000";
  return `${proto}://${host}`;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const origin = baseUrl(request);

  console.log("[SwiggyCallback] GET entry:", {
    url: request.url,
    code: code ? `${code.slice(0, 20)}...` : null,
    state: state ? `${state.slice(0, 30)}...` : null,
    origin,
    allParams: Object.fromEntries(searchParams.entries()),
  });

  if (!code || !state) {
    console.error("[SwiggyCallback] missing code or state, redirecting to error");
    return NextResponse.redirect(
      new URL("/orders/new?swiggy=error", origin),
    );
  }

  // Read code_verifier from cookie
  const codeVerifier =
    request.cookies.get("swiggy_code_verifier")?.value ?? "";

  console.log("[SwiggyCallback] code_verifier from cookie:", {
    present: !!codeVerifier,
    length: codeVerifier.length,
  });

  const apiUrl = process.env.NEXT_PUBLIC_API_URL!;
  const redirectUri = `${origin}/auth/connect/swiggy`;

  const exchangeBody = {
    code,
    state,
    code_verifier: codeVerifier,
    redirect_uri: redirectUri,
  };

  console.log("[SwiggyCallback] calling exchange:", {
    url: `${apiUrl}/api/v1/auth/swiggy/exchange`,
    redirect_uri: redirectUri,
    code_length: code.length,
    state_length: state.length,
    code_verifier_length: codeVerifier.length,
  });

  const resp = await fetch(`${apiUrl}/api/v1/auth/swiggy/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(exchangeBody),
  });

  const responseBody = await resp.text();
  console.log("[SwiggyCallback] exchange response:", {
    status: resp.status,
    statusText: resp.statusText,
    headers: Object.fromEntries(resp.headers.entries()),
    body: responseBody,
  });

  if (resp.ok) {
    const successUrl = "/orders/new?provider=swiggy&method=order";
    console.log("[SwiggyCallback] success, redirecting to:", successUrl);
    const response = NextResponse.redirect(
      new URL(successUrl, origin),
    );
    // Clear the code_verifier cookie
    response.cookies.set("swiggy_code_verifier", "", {
      path: "/",
      maxAge: 0,
    });
    return response;
  }

  console.error("[SwiggyCallback] exchange failed, redirecting to error:", {
    status: resp.status,
    body: responseBody,
  });
  return NextResponse.redirect(
    new URL("/orders/new?swiggy=error", origin),
  );
}
