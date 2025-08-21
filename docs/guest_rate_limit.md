# Guest Rate Limit Middleware

`GuestRateLimitMiddleware` throttles anonymous guest traffic hitting `/g/*`
endpoints. It uses `security.ratelimit.allow` to enforce a limit of 60 requests
per minute with a burst capacity of 100. When the limit is exceeded, the
middleware returns `err("RATELIMIT_429", "TooManyRequests")` with HTTP 429.

This middleware is defined but not yet wired into the application stack.
