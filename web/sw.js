// Keeps the app and the Python engine on the phone so it opens without a connection.
const VERSION = "__VERSION__";
const CACHE = `garden-tracker-${VERSION}`;

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const list = await (await fetch("precache.json", { cache: "no-store" })).json();
    const cache = await caches.open(CACHE);
    await Promise.allSettled(list.map((u) => cache.add(new Request(u, { cache: "reload" }))));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith("garden-tracker-") && k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;  // weather calls go straight to the network
  e.respondWith((async () => {
    const hit = await caches.match(e.request, { ignoreSearch: true });
    if (hit) return hit;
    try { return await fetch(e.request); } catch { return (await caches.match("index.html")) || Response.error(); }
  })());
});
