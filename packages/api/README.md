# API Client

Typed API helpers and realtime hooks for frontend apps.

## Overview

`@neo/api` wraps `fetch` with helpers for base URLs and headers and exposes
hooks for realtime communication. Consumers typically configure
`VITE_API_BASE` and `VITE_WS_BASE` environment variables to point to the HTTP
and WebSocket servers.

## Adding endpoints and types

Define endpoint functions and `zod` types in `src/endpoints.ts` and export them
from `src/index.ts`. Use `apiFetch` for REST calls and the hooks below for
realtime updates.

## Hooks

### `useSSE`

```tsx
import { useSSE } from '@neo/api';

const { data, error } = useSSE('/api/events', {
  retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000)
});
```

### `useWS`

```tsx
import { useWS } from '@neo/api';

const { data, send } = useWS('wss://example.com/socket', {
  retryDelay: () => 5000
});

send({ type: 'ping' });
```

## Telemetry

### `usePageview`

```tsx
import { usePageview } from '@neo/api';
import { useLocation } from 'react-router-dom';

function App() {
  const { pathname } = useLocation();
  usePageview(pathname);
  return null;
}
```

These utilities are PWA‑friendly; serve your app over HTTPS with a registered
service worker for full functionality.
