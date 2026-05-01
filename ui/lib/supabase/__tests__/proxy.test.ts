import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";
import { ONBOARDED_COOKIE } from "@/lib/cookies";

vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({
    auth: {
      getClaims: vi.fn(),
    },
  })),
}));

import { createServerClient } from "@supabase/ssr";
import { updateSession } from "../proxy";

const mockGetClaims = vi.fn();

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

  mockGetClaims.mockReset();
  vi.mocked(createServerClient).mockReturnValue({
    auth: { getClaims: mockGetClaims },
  } as never);
});

function makeRequest(path: string, cookies?: Record<string, string>) {
  const url = `http://localhost:3000${path}`;
  const req = new NextRequest(url);
  if (cookies) {
    for (const [name, value] of Object.entries(cookies)) {
      req.cookies.set(name, value);
    }
  }
  return req;
}

function getRedirectPath(response: Response): string | null {
  const location = response.headers.get("location");
  if (!location) return null;
  return new URL(location).pathname + new URL(location).search;
}

describe("updateSession (proxy auth routing)", () => {
  describe("no session", () => {
    beforeEach(() => {
      mockGetClaims.mockResolvedValue({ data: { claims: null } });
    });

    it("redirects protected route to /login", async () => {
      const response = await updateSession(makeRequest("/meal-plan"));
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/login");
    });

    it("passes through /login", async () => {
      const response = await updateSession(makeRequest("/login"));
      expect(response.status).toBe(200);
    });

    it("passes through /auth/callback", async () => {
      const response = await updateSession(makeRequest("/auth/callback"));
      expect(response.status).toBe(200);
    });

    it("passes through /onboarding", async () => {
      const response = await updateSession(makeRequest("/onboarding"));
      expect(response.status).toBe(200);
    });
  });

  describe("with session", () => {
    beforeEach(() => {
      mockGetClaims.mockResolvedValue({
        data: { claims: { sub: "user-123", email: "test@test.com" } },
      });
    });

    it("redirects /login to /", async () => {
      const response = await updateSession(makeRequest("/login"));
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/");
    });

    it("redirects protected route to /onboarding when no cookie", async () => {
      const response = await updateSession(makeRequest("/meal-plan"));
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/onboarding");
    });

    it("passes through protected route when cookie present", async () => {
      const response = await updateSession(
        makeRequest("/meal-plan", { [ONBOARDED_COOKIE]: "1" }),
      );
      expect(response.status).toBe(200);
    });

    it("redirects /onboarding to / when cookie present", async () => {
      const response = await updateSession(
        makeRequest("/onboarding", { [ONBOARDED_COOKIE]: "1" }),
      );
      expect(response.status).toBe(307);
      expect(getRedirectPath(response)).toBe("/");
    });

    it("passes through /onboarding when no cookie", async () => {
      const response = await updateSession(makeRequest("/onboarding"));
      expect(response.status).toBe(200);
    });

    it("passes through nested protected routes with cookie", async () => {
      const response = await updateSession(
        makeRequest("/invoice/123", { [ONBOARDED_COOKIE]: "1" }),
      );
      expect(response.status).toBe(200);
    });
  });
});
