# Housekeeping API

Two endpoints allow cleaners or administrators to manage table availability:

- `POST /api/outlet/{tenant}/housekeeping/table/{table_id}/start_clean`
  Marks the table as `PENDING_CLEANING`.
- `POST /api/outlet/{tenant}/housekeeping/table/{table_id}/ready`
  Marks the table as `AVAILABLE` and records the cleaning timestamp.

Guest POST requests under `/g/` are blocked unless the table state is `AVAILABLE`.
