# Rate Limit & Blocklist Policy

- Guest APIs: 60 req/min/IP (burst 100).
- After 3 **rejected** orders within 24h from the same IP for a tenant → blocklist for 24h (configurable) and further requests receive `IP_BLOCKED` (HTTP 429).
- Allow unblock by Super-Admin via `POST /api/outlet/{tenant}/security/unblock_ip`.
- Implementation uses a Redis-backed token bucket (INCR + EXPIRE) to enforce
  burst and sustained rates.
