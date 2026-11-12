// Sorbo funciona aunque la señal esté mala: guarda la app y la última edición.
const VERSION = "sorbo-v1";
const SHELL = [
  "./", "index.html", "styles.css", "app.js", "manifest.webmanifest",
  "assets/fonts/Lora.ttf", "assets/fonts/Inter-Regular.otf", "assets/fonts/Inter-SemiBold.otf",
  "assets/fonts/Inter-Bold.otf", "assets/icons/icon-192.png", "assets/icons/apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin || e.request.method !== "GET") return; // fotos de los medios: directo
  if (url.pathname.endsWith("edition.json")) {
    // La edición: primero internet, si falla la última guardada
    e.respondWith(
      fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(VERSION).then((c) => c.put(e.request, copy));
        return res;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // La app: primero lo guardado, y se actualiza por detrás
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const net = fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(VERSION).then((c) => c.put(e.request, copy));
        return res;
      }).catch(() => hit);
      return hit || net;
    })
  );
});
