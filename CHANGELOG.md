# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- Enforce environment validation at application startup and audit required
  variables during the CI lint step.
- Lock out staff PIN login for 15 minutes after 5 failed attempts per user/IP
  and log lock/unlock events.
- Require staff PIN rotation every 90 days with a warning emitted after 80 days.

