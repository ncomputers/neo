# DSAR Privacy Endpoints

Two administrative endpoints expose one-click Data Subject Access Request (DSAR) utilities for an outlet.

- `POST /api/outlet/{tenant}/privacy/dsar/export`
- `POST /api/outlet/{tenant}/privacy/dsar/delete`

Both endpoints accept a JSON body with either a `phone` or `email` field. The delete route also accepts a `dry_run` flag that reports the number of affected rows without modifying data.

All invocations are audited and leverage existing retention/anonymisation helpers.
