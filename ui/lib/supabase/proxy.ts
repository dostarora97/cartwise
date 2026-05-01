import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  console.log("[Proxy] START", pathname);

  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          const cookies = request.cookies.getAll();
          console.log("[Proxy] getAll cookies:", cookies.map(c => c.name).join(", "));
          return cookies;
        },
        setAll(cookiesToSet) {
          console.log("[Proxy] setAll cookies:", cookiesToSet.map(c => c.name).join(", "));
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // IMPORTANT: Do not run code between createServerClient and getClaims()
  const { data } = await supabase.auth.getClaims();
  const user = data?.claims;

  const isPublicRoute =
    pathname.startsWith("/login") ||
    pathname.startsWith("/auth") ||
    pathname.startsWith("/onboarding");

  console.log("[Proxy] getClaims result:", { hasUser: !!user, isPublicRoute, pathname });

  if (!user && !isPublicRoute) {
    console.log("[Proxy] REDIRECT → /login (no user, not public)");
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  if (user && pathname === "/login") {
    console.log("[Proxy] REDIRECT → / (user on login page)");
    const url = request.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }

  console.log("[Proxy] PASS THROUGH");
  return supabaseResponse;
}
