# PWA API Configuration

The PWA reads its API base URL and tenant identifier from environment
variables so that requests automatically include a tenant header.

## Setup

1. Copy `pwa/.env.example` to `pwa/.env`.
2. Set `VITE_API_BASE` to the backend base URL (e.g. `http://localhost:4000`).
3. Set `VITE_TENANT_ID` to the tenant value to send in the `X-Tenant-ID` header.
4. Start the development server with `npm run dev`.

All API calls use `apiFetch` which prefixes `VITE_API_BASE` and injects the
`X-Tenant-ID` header automatically.
