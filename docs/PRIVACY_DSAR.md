# DSAR Privacy Endpoints

Two administrative endpoints expose one-click Data Subject Access Request (DSAR) utilities for an outlet.

- `POST /api/outlet/{tenant}/privacy/dsar/export`
- `POST /api/outlet/{tenant}/privacy/dsar/delete`

Both endpoints accept a JSON body with either a `phone` or `email` field. The delete route also accepts a `dry_run` flag that reports the number of affected rows without modifying data.

All invocations are audited and leverage existing retention/anonymisation helpers.

## DPDP data principal rights

The Digital Personal Data Protection Act grants data principals the right to:

- request access to their personal data and processing details;
- seek correction or erasure of personal data; and
- nominate another individual to exercise these rights when they are unable to do so.

These DSAR endpoints support the exercise of these rights for customers of an outlet.
