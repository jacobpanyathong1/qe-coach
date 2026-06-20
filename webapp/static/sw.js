// Service worker — offline support for the QE Academy PWA.
const CACHE = "qe-v10";
const SHELL = [
  "/", "/app.js", "/styles.css", "/manifest.webmanifest",
  "/icons/icon-192.png", "/icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);

  // Large book PDFs: stream from the network, never cache (would bloat the cache).
  if (url.pathname.startsWith("/pdfs/")) return;

  // Media (diagrams/figures) are immutable — cache-first, fill cache on first view.
  if (url.pathname.startsWith("/media/")) {
    e.respondWith(caches.open(CACHE).then(async (c) => {
      const hit = await c.match(e.request);
      if (hit) return hit;
      const res = await fetch(e.request);
      c.put(e.request, res.clone());
      return res;
    }));
    return;
  }

  // API — network-first so progress stays fresh, fall back to cache when offline.
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(
      fetch(e.request)
        .then((res) => { caches.open(CACHE).then((c) => c.put(e.request, res.clone())); return res; })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // App shell / static — cache-first.
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
