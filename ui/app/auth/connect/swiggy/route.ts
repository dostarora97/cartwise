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

  if (!code || !state) {
    return NextResponse.redirect(
      new URL("/invoice?swiggy=error", origin),
    );
  }

  // Read code_verifier from cookie
  const codeVerifier =
    request.cookies.get("swiggy_code_verifier")?.value ?? "";

  const apiUrl = process.env.NEXT_PUBLIC_API_URL!;
  const redirectUri = `${origin}/auth/connect/swiggy`;

  const resp = await fetch(`${apiUrl}/api/v1/auth/swiggy/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code,
      state,
      code_verifier: codeVerifier,
      redirect_uri: redirectUri,
    }),
  });

  if (resp.ok) {
    const response = NextResponse.redirect(
      new URL("/invoice?provider=swiggy&method=order", origin),
    );
    // Clear the code_verifier cookie
    response.cookies.set("swiggy_code_verifier", "", {
      path: "/",
      maxAge: 0,
    });
    return response;
  }

  return NextResponse.redirect(
    new URL("/invoice?swiggy=error", origin),
  );
}
