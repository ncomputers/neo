# Changelog

All notable changes to this project will be documented in this file.

## v1.0.0-rc1 - 2025-08-25


## Unreleased

### Added

- Cache last 50 invoice PDFs per outlet for offline review.
- Collect CSP violation reports via `/csp/report` with paginated admin viewer and query/token redaction.
- /time/skew endpoint returns server epoch for client clock skew detection.
- Guard hot queries with a p95 regression check.
- Enforce environment validation at application startup and audit required
  variables during the CI lint step.
- Lock out staff PIN login for 15 minutes after 5 failed attempts per user/IP
  and log lock/unlock events.
- Require staff PIN rotation every 90 days with a warning emitted after 80 days.
- Soft-delete support for menu items and tables with restore endpoints and
  status included in exports.
- Bandit, pip-audit, and ruff GitHub Actions workflows to block risky code and dependencies.

- Request-id middleware with JSON log configuration for request correlation.

- Admin APIs to soft-delete and restore tables and menu items with optional
  inclusion of deleted records via ``include_deleted``.
- Admin endpoints to test webhook destinations and replay webhooks from the
  notification outbox.
- Admin endpoint to probe webhook SLA, capturing TLS details and latency and
  storing reports for later review.
- Webhook rule creation probes target latency and TLS, warning on slow or
  self-signed endpoints.
- Controlled cancellation flow with `/orders/{id}/void/request` and `/void/approve` endpoints, reversing stock, adjusting invoices and auditing each step.
- Printable invoice and KOT templates consume middleware-provided CSP nonces on inline styles to harden rendering.
- Add tests ensuring CSP nonces are applied on printable invoice and KOT pages.
- Slow query logging with WARNs above the configurable threshold and 1% sampling of regular queries.
- Locust profiles with locked p95 targets and nightly staging perf sanity.
- Idempotent offline order queue using client-side `op_id` dedupe.
- Dry-run mode for soft-deleted purge script with nightly CI report.
- Stricter `/api/admin/preflight` checks for soft-delete indexes, quotas,
  webhook breaker metrics, and replica health.
- Extra tenant isolation and signed media tests to enforce cross-tenant boundaries.
- Per-coupon usage caps (per day/guest/outlet) with valid-from/to windows and
  usage auditing, returning helpful hints when limits are exceeded.>>>>>>> main
- Owner dashboard displays licensing usage bars for tables, items, images, and exports.
- Guests opting into WhatsApp receive order status updates when orders are
  accepted, out for delivery, or ready.
- Fetch PWA icons (192x192 and 512x512) via script with iOS meta tags for better install prompts.
- OWASP ZAP baseline security scan against staging with auth paths allowlisted.

- Optional PostHog/Mixpanel analytics with per-tenant consent and PII redaction.

- WhatsApp guest notifications are gated by the `WHATSAPP_GUEST_UPDATES_ENABLED`
  environment variable.
- Status updates are sent via the WhatsApp provider with retry/backoff and
  audit logging, gated by the `FLAG_WA_ENABLED` feature flag.
- Menu items support JSON-defined modifiers and combos with server-side pricing.
- Admin endpoint `/admin/tenant/sandbox` bootstraps demo tenants without PII
  and auto-expires after seven days.
- Menu items expose dietary and allergen tags with guest filter support.
- Feature-flagged menu modifiers and combos with server-side pricing (`FLAG_SIMPLE_MODIFIERS`).
- Centralised helpers for applying modifier pricing and dietary/allergen filters.

- Admin dashboard panel shows quota usage bars for tables, items, images, and exports with a
  "Request more" email link.

  "Request more" link.
- Track per-route SLO metrics, expose `/admin/ops/slo` endpoint and Grafana dashboard.
- Owner dashboard includes SLA/ops widget with uptime, webhook success rate,
  breaker open time, and median KOT prep time.

- Script to bulk seed a large dataset for local scale testing.

- Feature-flagged happy-hour pricing via scheduled `happy_hour_windows` (day/time windows) with best-overlap discounting and coupons disabled during discount windows.
- JSON logger redacts phone numbers, emails, and UTR values.
- `LOG_SAMPLE_2XX` controls sampling of successful request logs.

### Changed

- 429 responses for magic-link, guest order, exports, and webhook test now include retry hints.

### Fixed

- Bundle Noto Sans fonts for printable invoices and KOTs, covering the ₹ sign and Gujarati/Hindi glyphs.



## v1.0.0-rc - 2025-08-25

- Initial release candidate.

