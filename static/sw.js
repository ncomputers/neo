const STATIC_CACHE = 'static-v1';
const MENU_CACHE = 'menu-v1';

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll([
      '/static/manifest.json'
    ]))
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(resp => resp || fetch(event.request))
    );
    return;
  }

  if (url.pathname.includes('/menu')) {
    event.respondWith(
      fetch(event.request)
        .then(resp => {
          const clone = resp.clone();
          caches.open(MENU_CACHE).then(cache => cache.put(event.request, clone));
          return resp;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }
});

self.addEventListener('sync', event => {
  if (event.tag === 'order-queue') {
    event.waitUntil(Promise.resolve());
  }
});
