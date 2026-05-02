import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
  globalThis.fetch = originalFetch;
});

function makeRequest(params: string, cookies?: Record<string, string>) {
  const url = `http://localhost:3000/auth/connect/swiggy${params}`;
  const req = new NextRequest(url);
  if (cookies) {
    for (const [key, value] of Object.entries(cookies)) {
      req.cookies.set(key, value);
    }
  }
  return req;
}

function getRedirectPath(response: Response): string {
  const location = response.headers.get("location")!;
  const url = new URL(location);
  return url.pathname + url.search;
}

function hasCookieCleared(response: Response, name: string): boolean {
  const setCookie = response.headers.get("set-cookie") ?? "";
  return setCookie.includes(`${name}=;`) || setCookie.includes(`${name}=; `);
}

describe("GET /auth/connect/swiggy", () => {
  let GET: (request: NextRequest) => Promise<Response>;

  beforeEach(async () => {
    const mod = await import("../route");
    GET = mod.GET;
  });

  it("redirects to /invoice?swiggy=error when code missing", async () => {
    const response = await GET(makeRequest("?state=xyz"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/invoice?swiggy=error");
  });

  it("redirects to /invoice?swiggy=error when state missing", async () => {
    const response = await GET(makeRequest("?code=abc"));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/invoice?swiggy=error");
  });

  it("redirects to /invoice?swiggy=error when both missing", async () => {
    const response = await GET(makeRequest(""));
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/invoice?swiggy=error");
  });

  it("redirects to /invoice?provider=swiggy&method=order on successful exchange", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("ok", { status: 200 }),
    );

    const response = await GET(
      makeRequest("?code=abc&state=xyz", { swiggy_code_verifier: "verifier123" }),
    );
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe(
      "/invoice?provider=swiggy&method=order",
    );
    expect(hasCookieCleared(response, "swiggy_code_verifier")).toBe(true);
  });

  it("sends code_verifier from cookie to exchange endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response("ok", { status: 200 }),
    );
    globalThis.fetch = mockFetch;

    await GET(
      makeRequest("?code=abc&state=xyz", { swiggy_code_verifier: "my-verifier" }),
    );

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/v1/auth/swiggy/exchange");
    const body = JSON.parse(options.body);
    expect(body.code).toBe("abc");
    expect(body.state).toBe("xyz");
    expect(body.code_verifier).toBe("my-verifier");
  });

  it("redirects to /invoice?swiggy=error on failed exchange", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("error", { status: 400 }),
    );

    const response = await GET(
      makeRequest("?code=abc&state=xyz", { swiggy_code_verifier: "verifier" }),
    );
    expect(response.status).toBe(307);
    expect(getRedirectPath(response)).toBe("/invoice?swiggy=error");
  });
});
