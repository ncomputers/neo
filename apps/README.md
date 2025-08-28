# Apps

Each app is a Vite + React shell.

## Running

```bash
pnpm install
pnpm dev --filter @neo/guest   # Guest PWA
pnpm dev --filter @neo/kds     # Kitchen Display
pnpm dev --filter @neo/admin   # Admin console
```

Set `VITE_API_BASE` and `VITE_WS_BASE` in the app's `.env` file.
