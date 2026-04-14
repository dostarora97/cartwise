/// <reference lib="webworker" />
import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { Serwist } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: defaultCache,
});

// Handle Web Share Target API — intercept POST to /share
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (event.request.method === "POST" && url.pathname === "/share") {
    event.respondWith(
      (async () => {
        const formData = await event.request.formData();
        const file = formData.get("invoice") as File | null;

        if (file) {
          // Store the shared file in Cache API for the page to pick up
          const cache = await caches.open("shared-files");
          await cache.put(
            "/shared-invoice",
            new Response(file, {
              headers: {
                "Content-Type": file.type,
                "X-File-Name": file.name,
              },
            })
          );
        }

        // Redirect to the share page
        return Response.redirect("/invoice?received=true", 303);
      })()
    );
    return;
  }
});

serwist.addEventListeners();
