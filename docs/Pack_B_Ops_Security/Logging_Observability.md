# Logging & Observability

- JSON logs with correlation id per request.
- Sensitive fields redacted (passwords, PINs, tokens, UTR, emails, phone numbers).
- 2xx and guest 4xx logs are sampled to control log volume.
- Metrics: request latency, WS connections, orders/min, failed payments, queue length.
- Dashboards: API p95, KDS lag, DB connections, Redis memory.
