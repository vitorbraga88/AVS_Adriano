/* AVS service worker — network-first para HTML/JS/CSS; cache como fallback.
   NUNCA cacheia POST nem /api/* nem /relatorios/* (dados dinâmicos). */
var CACHE = "avs-v1";

self.addEventListener("install", function (e) {
  self.skipWaiting();
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/relatorios/")) return;
  if (url.origin !== self.location.origin) return; // deixa CDNs seguirem o padrão do browser

  e.respondWith(
    fetch(req).then(function (resp) {
      if (resp && resp.status === 200) {
        var clone = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(req, clone); });
      }
      return resp;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        return hit || caches.match("/");
      });
    })
  );
});
