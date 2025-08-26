# Abuse Guard

`security.abuse_guard.guard` protects guest order endpoints from abusive
traffic.

- **IP cooldown**: After three rejected orders from the same IP within a day the
  address is cooled down for fifteen minutes.
- **User-Agent denylist**: Requests from known bad agents such as `curl` and
  `wget` are rejected.
- **Geo sanity hint**: If the reported `X-Geo-City` header does not match the
  tenant's `X-Tenant-City`, the mismatch is surfaced in the error hint to aid
  troubleshooting.

Call `abuse_guard.guard(request, tenant_id, redis)` at the start of guest order
processing to enforce these checks.
