const STATIC_CACHE = 'static-v2';
const STATIC_ASSETS = ['/pwa/', '/static/offline.html', '/static/manifest.json'];
const INVOICE_CACHE_PREFIX = 'invoice-';
const MAX_INVOICE_CACHE = 50;
const QUEUE_DB = 'request-queue';
const QUEUE_STORE = 'requests';
const API_QUEUE_TAG = 'api-queue';

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim().then(() => checkPendingRequests()));
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
  if (event.data?.type === 'BG_SYNC_ENQUEUE') {
    event.waitUntil(
      enqueueRequest(event.data.req).then(() =>
        self.registration.sync.register(API_QUEUE_TAG)
      )
    )
    return
  }
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  if (event.request.mode === 'navigate') {
    if (url.pathname.startsWith('/admin') || url.pathname.startsWith('/kds')) {
      event.respondWith(fetch(event.request));
      return;
    }
    event.respondWith(
      fetch(event.request, { cache: 'no-store' })
        .then(response => {
          if (!url.pathname.endsWith('/index.html')) {
            const copy = response.clone();
            caches.open(STATIC_CACHE).then(cache => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() =>
          caches.match(event.request).then(
            cached => cached || caches.match('/static/offline.html')
          )
        )
    );
    return;
  }

  if (
    event.request.method === 'POST' &&
    (url.pathname.startsWith('/api/guest/') || url.pathname.startsWith('/api/counter/'))
  ) {
    event.respondWith(handleApiRequest(event.request));
    return;
  }

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

  if (url.origin === location.origin && url.pathname.startsWith('/pwa/')) {
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
    event.waitUntil(flushQueue());
  }
  if (event.tag === API_QUEUE_TAG) {
    event.waitUntil(flushRequestQueue());
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

async function handleApiRequest(request) {
  const key = self.crypto?.randomUUID ? self.crypto.randomUUID() : Math.random().toString(36).slice(2);
  const headers = new Headers(request.headers);
  headers.set('Idempotency-Key', key);
  const req = new Request(request, { headers });

  try {
    return await fetch(req);
  } catch (_) {
    const body = await req.clone().arrayBuffer();
    await enqueueRequest({ key, url: req.url, method: req.method, headers: Array.from(headers.entries()), body });
    await self.registration.sync.register(API_QUEUE_TAG);
    return new Response(JSON.stringify({ queued: true }), {
      status: 202,
      headers: { 'content-type': 'application/json' },
    });
  }
}

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(QUEUE_DB, 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(QUEUE_STORE, { keyPath: 'key' });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function enqueueRequest(data) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, 'readwrite');
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.objectStore(QUEUE_STORE).put(data);
  });
}

async function readAllRequests() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, 'readonly');
    const req = tx.objectStore(QUEUE_STORE).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function deleteRequest(key) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, 'readwrite');
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.objectStore(QUEUE_STORE).delete(key);
  });
}

async function flushRequestQueue() {
  const items = await readAllRequests();
  for (const item of items) {
    try {
      await fetch(item.url, {
        method: item.method,
        headers: new Headers(item.headers),
        body: item.body,
      });
      await deleteRequest(item.key);
    } catch (_) {
      // keep for retry
    }
  }
}

async function checkPendingRequests() {
  try {
    const db = await openDB();
    const tx = db.transaction(QUEUE_STORE, 'readonly');
    const store = tx.objectStore(QUEUE_STORE);
    const countReq = store.count();
    return new Promise(resolve => {
      countReq.onsuccess = () => {
        if (countReq.result > 0) {
          self.registration.sync.register(API_QUEUE_TAG);
        }
        resolve();
      };
      countReq.onerror = () => resolve();
    });
  } catch (_) {
    // ignore
  }
}
