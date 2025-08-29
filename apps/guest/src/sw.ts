/// <reference lib="webworker" />
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { CacheFirst, NetworkOnly } from 'workbox-strategies';
import { BackgroundSyncPlugin } from 'workbox-background-sync';
import { ExpirationPlugin } from 'workbox-expiration';

// @ts-ignore self is defined in service worker
precacheAndRoute([...self.__WB_MANIFEST, { url: '/offline', revision: null }]);

registerRoute(
  ({ request }) => request.mode === 'navigate',
  async ({ event }) => {
    const fetchEvent = event as FetchEvent;
    try {
      return await fetch(fetchEvent.request);
    } catch {
      const cached = await caches.match('/offline');
      return (cached ?? new Response('Offline', { status: 503 })) as Response;
    }
  }
);

registerRoute(
  '/api/menu',
  new CacheFirst({ cacheName: 'menu' })
);

registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: 'images',
    plugins: [new ExpirationPlugin({ maxEntries: 60 })],
  })
);

const bgSyncPlugin = new BackgroundSyncPlugin('orders', {
  maxRetentionTime: 24 * 60,
  onSync: async ({ queue }) => {
    let entry;
    while ((entry = await queue.shiftRequest())) {
      try {
        const res = await fetch(entry.request);
        const data = await res.json();
        const clients = await (self as any).clients.matchAll();
        clients.forEach((client: any) =>
          client.postMessage({ type: 'ORDER_SYNCED', orderId: data.id })
        );
      } catch (err) {
        await queue.unshiftRequest(entry);
        throw err;
      }
    }
  },
});

registerRoute(
  '/api/orders',
  new NetworkOnly({ plugins: [bgSyncPlugin] }),
  'POST'
);

self.addEventListener('message', (event: any) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    // @ts-ignore
    self.skipWaiting();
  }
});
