import createFetchClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";
import { createClient } from "@/lib/supabase";

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) {
      request.headers.set("Authorization", `Bearer ${session.access_token}`);
    }
    return request;
  },
};

const client = createFetchClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});
client.use(authMiddleware);

export default client;
