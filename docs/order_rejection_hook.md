# Order Rejection Hook

The API tracks repeated request failures per tenant and IP address using a
Redis-backed blocklist. Call
`api.app.hooks.order_rejection.on_rejected(tenant, ip, redis)` whenever an
order is rejected to increment the counter. The `GuestBlockMiddleware` consults
`security.blocklist.is_blocked(redis, tenant, ip)` to determine if the address
should be blocked.

After three rejected orders from the same IP within 24 hours for a tenant the
address is cooled down for fifteen minutes and further guest `POST /g/*`
requests return an `IP_BLOCKED` (HTTP 429) envelope. Admins may clear an
address with `POST /api/outlet/{tenant}/security/unblock_ip`.
