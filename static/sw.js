const STATIC_CACHE = 'static-v1';
const STATIC_ASSETS = ['/static/manifest.json'];
const INVOICE_CACHE_PREFIX = 'invoice-';
const MAX_INVOICE_CACHE = 50;

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
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
    return;
  }
  if (event.data?.type === 'QUEUE_ORDER_OP') {
    const op = { ...event.data.op, synced: false }
    orderQueue.push(op)
    notifyClients()
    event.waitUntil(self.registration.sync.register('order-queue'))
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

  if (url.pathname.startsWith('/invoice/') && url.pathname.endsWith('/pdf')) {
    const outlet = event.request.headers.get('X-Tenant-ID') || 'default';
    event.respondWith(handleInvoiceRequest(event.request, outlet));
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
    event.waitUntil(flushQueue());
  }
});

const orderQueue = [];

async function handleInvoiceRequest(request, outlet) {
  const cache = await caches.open(`${INVOICE_CACHE_PREFIX}${outlet}`);
  const cached = await cache.match(request);
  if (cached) {
    await cache.delete(request);
    await cache.put(request, cached.clone());
    return cached;
  }
  try {
    const resp = await fetch(request);
    if (resp.ok) {
      await cache.put(request, resp.clone());
      const keys = await cache.keys();
      if (keys.length > MAX_INVOICE_CACHE) {
        await cache.delete(keys[0]);
      }
    }
    return resp;
  } catch (_) {
    return cached || Response.error();
  }
}

async function flushQueue() {
  const pending = orderQueue.filter(op => !op.synced)
  if (!pending.length) return
  const payload = {
    orders: pending.map(op => ({
      op_id: op.op_id,
      table_code: op.table_code,
      items: op.items,
    })),
  }
  try {
    const resp = await fetch('/api/outlet/demo/orders/batch', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (resp.ok) {
      pending.forEach(op => (op.synced = true))
      notifyClients()
    }
  } catch (_) {
    // remain pending on network failure
  }
}

function notifyClients() {
  self.clients.matchAll({ type: 'window' }).then(clients => {
    clients.forEach(client => client.postMessage({ type: 'QUEUE_STATUS', ops: orderQueue }))
  })
}
