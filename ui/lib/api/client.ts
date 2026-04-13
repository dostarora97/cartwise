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
    // Don't override if caller already set Authorization
    if (request.headers.has("Authorization")) {
      return request;
    }
    if (cachedToken) {
      request.headers.set("Authorization", `Bearer ${cachedToken}`);
    }
    return request;
  },
};

const client = createFetchClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});
client.use(authMiddleware);

export default client;
