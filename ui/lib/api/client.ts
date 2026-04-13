import type { QueryClient } from "@tanstack/react-query";
import type { Session } from "@supabase/supabase-js";
import createFetchClient, { type Middleware } from "openapi-fetch";
import { createClient } from "@/lib/supabase/client";
import type { paths } from "./schema";

let cachedToken: string | null = null;

let browserQueryClient: QueryClient | null = null;

/** Called from the React Query provider so 401 recovery can refresh stale queries. */
export function registerApiQueryClient(client: QueryClient | null) {
  browserQueryClient = client;
}

let sessionRecoveryPromise: Promise<boolean> | null = null;

/** Matches GoTrueClient: refresh ~3 ticks before expiry at 30s per tick. */
const SESSION_EXPIRY_MARGIN_MS = 90_000;

function sessionHasUsableAccessToken(session: Session | null): session is Session {
  if (!session?.access_token) {
    return false;
  }
  if (session.expires_at == null) {
    return false;
  }
  return session.expires_at * 1000 - Date.now() >= SESSION_EXPIRY_MARGIN_MS;
}

async function tryRecoverSessionAfter401(): Promise<boolean> {
  if (typeof window === "undefined") {
    return false;
  }
  if (sessionRecoveryPromise) {
    return sessionRecoveryPromise;
  }

  sessionRecoveryPromise = (async () => {
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (sessionHasUsableAccessToken(session)) {
        setAuthToken(session.access_token);
        return true;
      }
      const { data, error } = await supabase.auth.refreshSession();
      if (error || !data.session?.access_token) {
        return false;
      }
      setAuthToken(data.session.access_token);
      return true;
    } catch {
      return false;
    }
  })().finally(() => {
    sessionRecoveryPromise = null;
  });

  return sessionRecoveryPromise;
}

/**
 * Set the auth token for API calls. Called by the auth context
 * when a session is established via onAuthStateChange.
 */
export function setAuthToken(token: string | null) {
  cachedToken = token;
}

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    if (request.headers.has("Authorization")) {
      return request;
    }
    if (cachedToken) {
      request.headers.set("Authorization", `Bearer ${cachedToken}`);
    }
    return request;
  },
  async onResponse({ response }) {
    if (response.status !== 401 || typeof window === "undefined") {
      return response;
    }
    const recovered = await tryRecoverSessionAfter401();
    if (recovered) {
      void browserQueryClient?.invalidateQueries();
      return response;
    }
    setAuthToken(null);
    window.location.href = "/login";
    return response;
  },
};

const client = createFetchClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});
client.use(authMiddleware);

export default client;
