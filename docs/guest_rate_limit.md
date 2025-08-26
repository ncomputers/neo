# Guest Rate Limit Middleware

`GuestRateLimitMiddleware` throttles anonymous guest traffic hitting `/g/*`
endpoints. It uses `security.ratelimit.allow` to enforce a limit of 60 requests
per minute with a burst capacity of 100. When the limit is exceeded, the
middleware responds with HTTP 429 and JSON
`{"code": "RATE_LIMIT", "message": "TooManyRequests", "hint": "retry in Xs"}`.

Guest POST bodies are also capped at 256KB; larger payloads trigger a
`PAYLOAD_TOO_LARGE` (HTTP 413) response.
