# Changelog

All notable changes to this project will be documented in this file.

## v1.0.0-rc1 - 2025-08-25


## Unreleased

### Added

- /time/skew endpoint returns server epoch for client clock skew detection.
- Guard hot queries with a p95 regression check.
- Enforce environment validation at application startup and audit required
  variables during the CI lint step.
- Lock out staff PIN login for 15 minutes after 5 failed attempts per user/IP
  and log lock/unlock events.
- Require staff PIN rotation every 90 days with a warning emitted after 80 days.
- Soft-delete support for menu items and tables with restore endpoints and
  status included in exports.
- Request-id middleware with JSON log configuration for request correlation.
- Admin APIs to soft-delete and restore tables and menu items with optional
  inclusion of deleted records via ``include_deleted``.
- Admin endpoints to test webhook destinations and replay webhooks from the
  notification outbox.
- Printable invoice and KOT templates consume middleware-provided CSP nonces on inline styles to harden rendering.
- Add tests ensuring CSP nonces are applied on printable invoice and KOT pages.
- Slow query logging with WARNs above the configurable threshold and 1% sampling of regular queries.
- Locust profiles with locked p95 targets and nightly staging perf sanity.
- Idempotent offline order queue using client-side `op_id` dedupe.
- Dry-run mode for soft-deleted purge script with nightly CI report.
- Stricter `/api/admin/preflight` checks for soft-delete indexes, quotas,
  webhook breaker metrics, and replica health.
- Owner dashboard displays licensing usage bars for tables, items, images, and exports.
- Guests opting into WhatsApp receive order status updates when orders are
  accepted, out for delivery, or ready.
- WhatsApp guest notifications are gated by the `WHATSAPP_GUEST_UPDATES_ENABLED`
  environment variable.
- Menu items support JSON-defined modifiers and combos with server-side pricing.
- Menu items expose dietary and allergen tags with guest filter support.
- Feature-flagged menu modifiers and combos with server-side pricing (`FLAG_SIMPLE_MODIFIERS`).

- Admin dashboard panel shows quota usage bars for tables, items, images, and exports with a
  "Request more" email link.

  "Request more" link.
- Track per-route SLO metrics, expose `/admin/ops/slo` endpoint and Grafana dashboard.

- Script to bulk seed a large dataset for local scale testing.

- Support happy-hour pricing via scheduled discount windows.

### Fixed

- Bundle Noto Sans fonts for printable invoices and KOTs, covering the ₹ sign and Gujarati/Hindi glyphs.



## v1.0.0-rc - 2025-08-25

- Initial release candidate.

