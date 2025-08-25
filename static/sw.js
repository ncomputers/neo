const STATIC_CACHE = 'static-v1';
const STATIC_ASSETS = ['/static/manifest.json'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
  self.registration.addEventListener('updatefound', () => {
    const newSW = self.registration.installing;
    if (newSW) {
      newSW.addEventListener('statechange', () => {
        if (newSW.state === 'installed') {
          self.clients.matchAll({ type: 'window' }).then(clients => {
            clients.forEach(client => client.postMessage({ type: 'UPDATE_READY' }));
          });
        }
      });
    }
  });
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/api/guest/menu')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const copy = response.clone();
          caches.open(STATIC_CACHE).then(cache => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  if (url.origin === location.origin && url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cached => cached || fetch(event.request))
    );
  }
});

self.addEventListener('sync', event => {
  if (event.tag === 'order-queue') {
    event.waitUntil(Promise.resolve());
  }
});
