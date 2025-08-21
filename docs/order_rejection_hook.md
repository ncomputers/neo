# Order Rejection Hook

The API tracks repeated request failures per IP address using a Redis-backed
blocklist. Call `api.app.hooks.order_rejection.on_rejected` whenever an order
is rejected to increment the counter. Middleware can later consult
`security.blocklist.is_blocked` to determine if the address should be blocked.
