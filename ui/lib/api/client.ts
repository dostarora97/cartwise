import createFetchClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

let cachedToken: string | null = null;

export function setAuthToken(token: string | null) {
  console.log("[ApiClient] setAuthToken:", token ? "token set (" + token.substring(0, 15) + "...)" : "null");
  cachedToken = token;
}

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const url = new URL(request.url);
    console.log("[ApiClient] onRequest:", request.method, url.pathname, {
      hasExplicitAuth: request.headers.has("Authorization"),
      hasCachedToken: !!cachedToken,
    });
    if (request.headers.has("Authorization")) {
      return request;
    }
    if (cachedToken) {
      request.headers.set("Authorization", `Bearer ${cachedToken}`);
    }
    return request;
  },
  async onResponse({ request, response }) {
    const url = new URL(request.url);
    console.log("[ApiClient] onResponse:", url.pathname, response.status);
    if (response.status === 401) {
      console.log("[ApiClient] 401 received — clearing cached token");
      cachedToken = null;
    }
    return response;
  },
};

console.log("[ApiClient] init, baseUrl:", process.env.NEXT_PUBLIC_API_URL);
const client = createFetchClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL!,
});
client.use(authMiddleware);

export default client;
