import { precacheAndRoute } from 'workbox-precaching';

// @ts-ignore self is defined in service worker
precacheAndRoute(self.__WB_MANIFEST);

self.addEventListener('message', (event: any) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    // @ts-ignore
    self.skipWaiting();
  }
});
