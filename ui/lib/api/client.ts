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
    if (response.status === 401 && typeof window !== "undefined") {
      cachedToken = null;
      window.location.href = "/login";
    }
    return response;
  },
};

const client = createFetchClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});
client.use(authMiddleware);

export default client;
