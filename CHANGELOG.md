# Changelog

All notable changes to this project will be documented in this file.

## v1.0.0-rc1 - 2025-08-25


## Unreleased

### Added

- Guard hot queries with a p95 regression check.
- Enforce environment validation at application startup and audit required
  variables during the CI lint step.
- Lock out staff PIN login for 15 minutes after 5 failed attempts per user/IP
  and log lock/unlock events.
- Require staff PIN rotation every 90 days with a warning emitted after 80 days.
- Soft-delete support for menu items and tables with restore endpoints and
  status included in exports.
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
- Menu items support JSON-defined modifiers and combos with server-side pricing.
- Admin dashboard panel shows quota usage bars for tables, items, images, and exports with a
  "Request more" link.
- Track per-route SLO metrics, expose `/admin/ops/slo` endpoint and Grafana dashboard.

- Script to bulk seed a large dataset for local scale testing.

- Support happy-hour pricing via scheduled discount windows.



## v1.0.0-rc - 2025-08-25

- Initial release candidate.

