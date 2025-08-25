const STATIC_CACHE = 'static-v1';
const STATIC_ASSETS = ['/static/manifest.json'];

// In-memory queue for offline order operations. Each entry carries a client
// generated ``op_id`` so the server can dedupe on reconnect.
let orderQueue = [];

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
          fetch('/pwa/version')
            .then(res => res.json())
            .then(data => data.build)
            .catch(() => undefined)
            .then(build => {
              self.clients.matchAll({ type: 'window' }).then(clients => {
                clients.forEach(client =>
                  client.postMessage({ type: 'UPDATE_READY', build })
                );
              });
            });
        }
      });
    }
  });
});

self.addEventListener('message', event => {
  const data = event.data || {};
  if (data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (data.type === 'QUEUE_ORDER') {
    const op_id = self.crypto?.randomUUID ? self.crypto.randomUUID() : Date.now().toString();
    orderQueue.push({ op_id, ...data.order });
    // Reply with the generated op_id so the UI can show a pending badge.
    event.ports[0]?.postMessage({ op_id });
  }
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
  if (event.tag === 'order-queue' && orderQueue.length) {
    event.waitUntil(
      fetch('/api/outlet/demo/orders/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orders: orderQueue }),
      })
        .then(res => {
          if (!res.ok) throw new Error('Network error');
          return res.json();
        })
        .then(() => {
          const synced = orderQueue.map(o => o.op_id);
          orderQueue = [];
          self.clients.matchAll({ type: 'window' }).then(clients => {
            clients.forEach(client =>
              client.postMessage({ type: 'ORDERS_SYNCED', op_ids: synced })
            );
          });
        })
        .catch(() => {
          /* swallow network errors; retry on next sync */
        })
    );
  }
});
