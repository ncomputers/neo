# Housekeeping API

Two endpoints allow cleaners or administrators to manage table availability.
Each action is recorded in the tenant audit log with the acting staff member and
target table or room:

- `POST /api/outlet/{tenant}/housekeeping/table/{table_id}/start_clean`
  Marks the table as `PENDING_CLEANING`.
- `POST /api/outlet/{tenant}/housekeeping/table/{table_id}/ready`
  Marks the table as `AVAILABLE` and records the cleaning timestamp.

Additional endpoints allow managing hotel room availability:

- `POST /api/outlet/housekeeping/room/{room_id}/start_clean`
  Marks the room as `PENDING_CLEANING`.
- `POST /api/outlet/housekeeping/room/{room_id}/ready`
  Marks the room as `AVAILABLE` and records the cleaning timestamp.

Guest POST requests under `/g/` and `/h/` are blocked unless the table or room state is `AVAILABLE`.
