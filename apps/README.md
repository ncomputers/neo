# Apps

Each app is a Vite + React shell.

## Install

```bash
pnpm install
```

## Develop

```bash
pnpm dev --filter @neo/guest   # Guest PWA
pnpm dev --filter @neo/kds     # Kitchen Display
pnpm dev --filter @neo/admin   # Admin console
```

## Build

```bash
pnpm build --filter @neo/guest
pnpm build --filter @neo/kds
pnpm build --filter @neo/admin
```

## Test

```bash
pnpm test --filter @neo/guest
pnpm test --filter @neo/kds
pnpm test --filter @neo/admin
```

## Environment

Set `VITE_API_BASE` and `VITE_WS_BASE` in each app's `.env` file.
Serve the built apps over HTTPS with a valid `manifest.webmanifest` and
`sw.js` service worker to satisfy PWA requirements.
