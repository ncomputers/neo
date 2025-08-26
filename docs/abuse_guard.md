# Abuse Guard

`security.abuse_guard.guard` protects guest order endpoints from abusive
traffic.

- **IP cooldown**: After three rejected orders from the same IP within a day the
  address is cooled down for fifteen minutes. Cooldowns emit a Prometheus
  metric `abuse_ip_cooldown{ip="1.2.3.4"}` with the remaining TTL and the API
  responds with an `ABUSE_COOLDOWN` error hinting `Try again in Xs`.
- **User-Agent denylist**: Requests from known bad agents such as `curl` and
  `wget` are rejected.
- **Geo sanity hint**: If the reported `X-Geo-City` header does not match the
  tenant's `X-Tenant-City`, the mismatch is surfaced in the error hint to aid
  troubleshooting.

Call `abuse_guard.guard(request, tenant_id, redis)` at the start of guest order
processing to enforce these checks.
