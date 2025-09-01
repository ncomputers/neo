# Frontend Deployment

This container bundles the `guest`, `kds`, and `admin` apps behind a single Nginx
server. Each app is served from its own base path (`/guest`, `/kds`, `/admin`) with
history API fallbacks so client-side routing works without additional Nginx
configuration.

## Environment variables
Builds read backend endpoints from the following variables:

- `VITE_API_BASE`
- `VITE_WS_BASE`

At runtime, `CSP_CONNECT_SRC` configures the CSP `connect-src` directive. It should contain a space-separated list of API and WebSocket origins, for example:

```bash
docker run -e CSP_CONNECT_SRC="https://api.example.com https://ws.example.com wss://ws.example.com" \
  -p 80:80 neo-ui
```

Pass the build-time variables when building the image:

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

Fonts are not committed to the repository. Run `scripts/download_fonts.py` to
populate `static/fonts/` before building so the preloaded assets resolve
correctly at runtime.

## Changing roots
Nginx reads its runtime configuration from the template at
`deploy/nginx/nginx.conf.tmpl`, rendered on container start by
`/entrypoint.sh`. The `root` defaults to `/usr/share/nginx/html`. Built apps are
copied into subdirectories of that root by `Dockerfile.ui`. To serve the apps
from different paths or to point to a different root, update the `location`
blocks or the `root` directive in the template and adjust the copy paths in the
Dockerfile.

## Validation

Verify the CSP header exposes the expected connect sources:

```bash
curl -I /guest/ | grep -i content-security-policy
```

The `connect-src` directive should list both API and WebSocket endpoints. Inline
scripts without the generated nonce must be blocked by the browser.

