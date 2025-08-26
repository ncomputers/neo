# PWA

The guest app can be installed as a Progressive Web App for quicker access and
basic offline support.

## Installation

1. Visit the guest URL on a supported mobile browser.
2. Use the browser's *Add to Home Screen* option.
3. The app installs with the name **Neo QR** and launches full screen.

## Offline & Updates

* Static assets are cached on first load via `sw.js`.
* Run `scripts/download_pwa_icons.py` to fetch icons locally while keeping binaries out of the repo.
* Menu API requests use a network‑first strategy with cached fallback.
* A background sync queue named `order-queue` batches offline additions with a
  client‑generated `op_id` to avoid double submissions. Items show a **pending**
  badge until the service worker syncs them, after which they are marked
  **synced**.
* Invoice PDFs are cached per outlet with an LRU cap of 50 for offline review.
* Updates are picked up when the service worker changes.

## Update UX

When a new build is waiting, the service worker posts an `UPDATE_READY` message
with the build hash. A small banner with a **Refresh** button appears. Clicking
**Refresh** sends `SKIP_WAITING` to the waiting worker and reloads the page,
activating the updated build.

## Version

`GET /pwa/version` returns build metadata:

```
{"build": "<git sha>", "time": "<build time>"}
```
