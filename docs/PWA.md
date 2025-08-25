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
* A background sync stub named `order-queue` is registered for future offline
  ordering.
* Updates are picked up when the service worker changes.
* When a new build is available, a **New version available** button appears;
  tapping it activates the update and reloads the app.

## Version

`GET /pwa/version` returns build metadata:

```
{"build": "<git sha>", "time": "<build time>"}
```
