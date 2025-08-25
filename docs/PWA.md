# Progressive Web App

The guest interface exposes a small Progressive Web App (PWA).
It can be installed on supported browsers and continues to work
with limited offline capability.

## Installation

1. Visit the guest application in a modern browser.
2. Use the browser's **Add to Home Screen** or **Install App** option.
3. The app metadata comes from [`static/manifest.json`](../static/manifest.json).

The manifest references placeholder icon URLs. Replace these with hosted branding assets when available.

## Offline & Updates

The service worker at [`static/sw.js`](../static/sw.js) uses a
cache‑first strategy for static assets and falls back to cached
menu data when the network is unavailable. For API endpoints serving
menu data a network‑first strategy keeps content fresh.

To publish updates, bump cache versions in the service worker and
deploy the updated files. Clients will fetch the new service worker on
next load and activate after all tabs using the old worker close.
