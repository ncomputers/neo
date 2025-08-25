# Changelog

All notable changes to this project will be documented in this file.

## v1.0.0-rc1 - 2025-08-25

### Other
- PR #313 (#313)
- PR #314 (#314)
- PR #315 (#315)
- PR #316 (#316)

## Unreleased

### Added

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
- Content-Security-Policy nonces for invoice and KOT templates to harden inline styles and scripts.
- Slow query logging with WARNs above the configurable threshold and 1% sampling
  of regular queries.
- Idempotent offline order queue using client-side `op_id` dedupe.
- Dry-run mode for soft-deleted purge script with nightly CI report.

