import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";
import { ONBOARDED_COOKIE, RETURN_TO_COOKIE } from "@/lib/cookies";

const mockExchangeCodeForSession = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    auth: {
      exchangeCodeForSession: mockExchangeCodeForSession,
    },
  })),
}));

const originalFetch = globalThis.fetch;

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
  mockExchangeCodeForSession.mockReset();
  globalThis.fetch = originalFetch;
});

function makeRequest(params: string) {
  return new NextRequest(`http://localhost:3000/auth/callback${params}`);
}

function makeRequestWithCookies(params: string, cookies: Record<string, string>) {
  const req = new NextRequest(`http://localhost:3000/auth/callback${params}`);
  for (const [name, value] of Object.entries(cookies)) {
    req.cookies.set(name, value);
  }
  return req;
}

function getRedirectPath(response: Response): string {
  const location = response.headers.get("location")!;
  const url = new URL(location);
  return url.pathname + url.search;
}

function hasCookie(response: Response, name: string): boolean {
  const setCookie = response.headers.get("set-cookie") ?? "";
  return setCookie.includes(`${name}=`);
}

describe("GET /auth/callback", () => {
  let GET: (request: NextRequest) => Promise<Response>;

  beforeEach(async () => {
    const mod = await import("../route");
    GET = mod.GET;
  });

  it("redirects to /login when no code param", async () => {
    const response = await GET(makeRequest(""));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/login");
  });

  it("redirects to /login when session exchange fails", async () => {
    mockExchangeCodeForSession.mockResolvedValue({ data: { session: null } });
    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/login");
  });

  it("redirects to /login?error=backend when fetch throws", async () => {
    mockExchangeCodeForSession.mockResolvedValue({
      data: { session: { access_token: "tok" } },
    });
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("network"));

    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/login?error=backend");
  });

  it("redirects to /login?error=backend when backend returns 500", async () => {
    mockExchangeCodeForSession.mockResolvedValue({
      data: { session: { access_token: "tok" } },
    });
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("error", { status: 500 }),
    );

    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/login?error=backend");
  });

  it("redirects to /onboarding when backend returns 404 (new user)", async () => {
    mockExchangeCodeForSession.mockResolvedValue({
      data: { session: { access_token: "tok" } },
    });
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "User not found" }), { status: 404 }),
    );

    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/onboarding");
  });

  it("sets cookie and redirects to / when splitwise_connected", async () => {
    mockExchangeCodeForSession.mockResolvedValue({
      data: { session: { access_token: "tok" } },
    });
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ splitwise_connected: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/");
    expect(hasCookie(response, ONBOARDED_COOKIE)).toBe(true);
  });

  it("redirects to /onboarding without cookie when not connected", async () => {
    mockExchangeCodeForSession.mockResolvedValue({
      data: { session: { access_token: "tok" } },
    });
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ splitwise_connected: false }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/onboarding");
    expect(hasCookie(response, ONBOARDED_COOKIE)).toBe(false);
  });

  describe("returnTo cookie consumption", () => {
    beforeEach(() => {
      mockExchangeCodeForSession.mockResolvedValue({
        data: { session: { access_token: "tok" } },
      });
      globalThis.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ splitwise_connected: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    it("redirects to returnTo cookie value when splitwise_connected", async () => {
      const response = await GET(
        makeRequestWithCookies("?code=abc", { [RETURN_TO_COOKIE]: "/import?supplier=cartwise/starter" }),
      );
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/import?supplier=cartwise/starter");
    });

    it("falls back to / when returnTo cookie is invalid", async () => {
      const response = await GET(
        makeRequestWithCookies("?code=abc", { [RETURN_TO_COOKIE]: "https://evil.com" }),
      );
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/");
    });

    it("falls back to / when returnTo cookie is a protocol-relative URL", async () => {
      const response = await GET(
        makeRequestWithCookies("?code=abc", { [RETURN_TO_COOKIE]: "//evil.com/path" }),
      );
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/");
    });

    it("falls back to / when returnTo cookie points to auth route", async () => {
      const response = await GET(
        makeRequestWithCookies("?code=abc", { [RETURN_TO_COOKIE]: "/login" }),
      );
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/");
    });

    it("deletes returnTo cookie after consuming it", async () => {
      const response = await GET(
        makeRequestWithCookies("?code=abc", { [RETURN_TO_COOKIE]: "/meal-plan" }),
      );
      const setCookie = response.headers.get("set-cookie") ?? "";
      expect(setCookie).toContain(`${RETURN_TO_COOKIE}=`);
      expect(setCookie).toContain("Max-Age=0");
    });
  });
});
