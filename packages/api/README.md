# API Client

Typed API helpers and realtime hooks.

## Adding endpoints

Add types and functions in `src/endpoints.ts` and export them from `src/index.ts`.
Use `apiFetch` for REST calls and `useSSE` / `useWS` for realtime.

## Realtime hooks

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
