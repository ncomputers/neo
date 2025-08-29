# Frontend Deployment

This container bundles the `guest`, `kds`, and `admin` apps behind a single Nginx server.

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

## Cache busting
Static assets are fingerprinted and served with a long cache lifetime. Updating
the Docker image generates new hashes so clients fetch the latest assets, while
`index.html` is served with `no-cache` to always load the newest manifest.
