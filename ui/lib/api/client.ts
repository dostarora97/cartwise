import createFetchClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

let cachedToken: string | null = null;

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
    // On 401, clear the cached token. Don't hard-redirect — let
    // Supabase attempt a token refresh via onAuthStateChange. If
    // the session is truly gone, the proxy will redirect on next
    // navigation and the auth context will update.
    if (response.status === 401) {
      cachedToken = null;
    }
    return response;
  },
};

const client = createFetchClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});
client.use(authMiddleware);

export default client;
