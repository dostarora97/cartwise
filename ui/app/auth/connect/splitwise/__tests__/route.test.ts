import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";
import { ONBOARDED_COOKIE } from "@/lib/cookies";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
  globalThis.fetch = originalFetch;
});

function makeRequest(params: string) {
  return new NextRequest(`http://localhost:3000/auth/connect/splitwise${params}`);
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

describe("GET /auth/connect/splitwise", () => {
  let GET: (request: NextRequest) => Promise<Response>;

  beforeEach(async () => {
    const mod = await import("../route");
    GET = mod.GET;
  });

  it("redirects to /onboarding?splitwise=error when code missing", async () => {
    const response = await GET(makeRequest("?state=xyz"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/onboarding?splitwise=error");
  });

  it("redirects to /onboarding?splitwise=error when state missing", async () => {
    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/onboarding?splitwise=error");
  });

  it("redirects to /onboarding?splitwise=error when both missing", async () => {
    const response = await GET(makeRequest(""));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/onboarding?splitwise=error");
  });

  it("sets cookie and redirects to / on successful exchange", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("ok", { status: 200 }),
    );

    const response = await GET(makeRequest("?code=abc&state=xyz"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/");
    expect(hasCookie(response, ONBOARDED_COOKIE)).toBe(true);
  });

  it("redirects to /onboarding?splitwise=error on failed exchange", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("error", { status: 400 }),
    );

    const response = await GET(makeRequest("?code=abc&state=xyz"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/onboarding?splitwise=error");
    expect(hasCookie(response, ONBOARDED_COOKIE)).toBe(false);
  });
});
