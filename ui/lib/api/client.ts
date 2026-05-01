import createFetchClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

let cachedToken: string | null = null;

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
    if (response.status === 401) {
      cachedToken = null;
    }
    return response;
  },
};

const client = createFetchClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL!,
});
client.use(authMiddleware);

export default client;
