# Table Map SSE

The `/api/outlet/{tenant}/tables/map/stream` endpoint streams table map updates using
Server‑Sent Events.

- **Heartbeat**: a comment `:keepalive` is emitted every 15 seconds so idle
  connections stay open.
- **Last-Event-ID**: when reconnecting, clients may send the `Last-Event-ID`
  header. The server will start event numbering from the next sequence and
  transmit a full snapshot before streaming incremental updates.
- **Event format**: each message uses `event: table_map` and an incremental
  `id` field.
- **Snapshot on connect**: the first `table_map` event contains the full list of
  tables under `{"tables": [...]}`. Subsequent events stream individual table
  updates.

