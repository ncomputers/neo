# PWA

The guest app can be installed as a Progressive Web App for quicker access and
basic offline support.

## Installation

1. Visit the guest URL on a supported mobile browser.
2. Use the browser's *Add to Home Screen* option.
3. The app installs with the name **Neo QR** and launches full screen.

## Offline & Updates

* Static assets are cached on first load via `sw.js`.
* Icons are loaded from a remote URL to avoid bundling binaries.
* Menu API requests use a network‑first strategy with cached fallback.
* The service worker queues order operations with a client-generated
  `op_id` and uses background sync (`order-queue`) to POST them in batch.
  The server deduplicates by `op_id` so reconnects won't double-add items,
  and the UI shows a pending/synced badge per line.
* Updates are picked up when the service worker changes.
* When a new build is waiting, the service worker posts an `UPDATE_READY`
  message with the build hash. The guest app shows a **New version available**
  button; tapping it activates the update and reloads the app.

## Version

`GET /pwa/version` returns build metadata:

```
{"build": "<git sha>", "time": "<build time>"}
```
