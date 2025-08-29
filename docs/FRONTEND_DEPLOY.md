# Frontend Deployment

This container bundles the `guest`, `kds`, and `admin` apps behind a single Nginx
server. Each app is served from its own base path (`/guest`, `/kds`, `/admin`) with
history API fallbacks so client-side routing works without additional Nginx
configuration.

## Environment variables
Builds read backend endpoints from the following variables:

- `VITE_API_BASE`
- `VITE_WS_BASE`

Pass them at build time, e.g.

```bash
docker build -f Dockerfile.ui \
  --build-arg VITE_API_BASE=https://api.example.com \
  --build-arg VITE_WS_BASE=wss://ws.example.com \
  -t neo-ui .
```

## Rolling restarts
Deploy new images using rolling restarts to avoid downtime. Replace the running
container with the updated image one instance at a time so requests continue to
be served while the new version starts.

## Cache busting and caching
Static assets (`.js`, `.css`, images, fonts) are fingerprinted and served with a
30‑day cache lifetime. Updating the Docker image generates new hashes so
clients fetch the latest assets, while HTML files are served with `no-store` to
always load the newest manifest.

## Changing roots
Nginx reads its runtime configuration from `deploy/nginx/nginx.conf`, where the
`root` is set to `/usr/share/nginx/html`. Built apps are copied into
subdirectories of that root by `Dockerfile.ui`. To serve the apps from different
paths or to point to a different root, update the `location` blocks or the
`root` directive in the config and adjust the copy paths in the Dockerfile.

