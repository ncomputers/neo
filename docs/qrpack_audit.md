# QR Pack Audit

The system now records each QR pack generation or reprint. When requesting a
pack, supply the following query parameters:

- `pack_id`: unique identifier for the pack
- `count`: number of codes generated
- `requester`: user initiating the request
- `reason`: why the pack was generated

Entries can be reviewed via the admin API:

- `GET /api/admin/qrpacks/logs` – list logs with optional `pack_id`,
  `requester`, or `reason` filters.
- `GET /api/admin/qrpacks/export` – export matching logs as CSV.

Both endpoints require `super_admin` privileges.
