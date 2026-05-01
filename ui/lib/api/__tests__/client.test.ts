import { describe, it, expect, vi, beforeEach } from "vitest";
import { ONBOARDED_COOKIE } from "@/lib/cookies";

let capturedMiddleware: {
  onRequest: (ctx: { request: Request }) => Promise<Request>;
  onResponse: (ctx: { response: Response }) => Promise<Response>;
};

vi.mock("openapi-fetch", () => ({
  default: vi.fn(() => ({
    use: vi.fn((mw: unknown) => {
      capturedMiddleware = mw as typeof capturedMiddleware;
    }),
  })),
}));

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
  vi.resetModules();
});

async function loadModule() {
  const mod = await import("../client");
  return mod;
}

describe("API client auth middleware", () => {
  describe("onRequest", () => {
    it("adds Authorization header when token is set", async () => {
      const { setAuthToken } = await loadModule();
      setAuthToken("my-token");

      const request = new Request("http://localhost:8000/api/v1/test");
      const result = await capturedMiddleware.onRequest({ request });
      expect(result.headers.get("Authorization")).toBe("Bearer my-token");
    });

    it("does not overwrite existing Authorization header", async () => {
      const { setAuthToken } = await loadModule();
      setAuthToken("my-token");

      const request = new Request("http://localhost:8000/api/v1/test", {
        headers: { Authorization: "Bearer existing" },
      });
      const result = await capturedMiddleware.onRequest({ request });
      expect(result.headers.get("Authorization")).toBe("Bearer existing");
    });

    it("does not add header when no token cached", async () => {
      await loadModule();

      const request = new Request("http://localhost:8000/api/v1/test");
      const result = await capturedMiddleware.onRequest({ request });
      expect(result.headers.has("Authorization")).toBe(false);
    });
  });

  describe("onResponse", () => {
    it("clears cookie on 401 in browser context", async () => {
      await loadModule();

      const mockDocument = { cookie: "" };
      vi.stubGlobal("document", mockDocument);

      const response = new Response("", { status: 401 });
      await capturedMiddleware.onResponse({ response });

      expect(mockDocument.cookie).toContain(ONBOARDED_COOKIE);
      expect(mockDocument.cookie).toContain("expires=Thu, 01 Jan 1970");

      vi.unstubAllGlobals();
    });

    it("does nothing on 200 response", async () => {
      const { setAuthToken } = await loadModule();
      setAuthToken("my-token");

      const response = new Response("", { status: 200 });
      await capturedMiddleware.onResponse({ response });

      // Token should still be set — verify by making a request
      const request = new Request("http://localhost:8000/api/v1/test");
      const result = await capturedMiddleware.onRequest({ request });
      expect(result.headers.get("Authorization")).toBe("Bearer my-token");
    });

    it("clears cached token on 401", async () => {
      const { setAuthToken } = await loadModule();
      setAuthToken("my-token");

      const response = new Response("", { status: 401 });
      await capturedMiddleware.onResponse({ response });

      // Token should be cleared
      const request = new Request("http://localhost:8000/api/v1/test");
      const result = await capturedMiddleware.onRequest({ request });
      expect(result.headers.has("Authorization")).toBe(false);
    });
  });
});
