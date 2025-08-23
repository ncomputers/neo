"""Server-Sent Events stream for table map updates.

Each event emits ``event: table_map`` with a monotonically increasing
``id``. Clients may reconnect using the ``Last-Event-ID`` header to
resume the sequence; when the server lacks history to bridge the gap it
falls back to sending a full snapshot before incremental updates.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from .db import SessionLocal
from .models_tenant import Table

KEEPALIVE_INTERVAL = 15

router = APIRouter()


@router.get(
    "/api/outlet/{tenant}/tables/map/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_table_map(
    tenant: str, last_event_id: str | None = Header(None, convert_underscores=False)
) -> StreamingResponse:
    """Stream table state changes via SSE."""

    from .main import redis_client  # lazy import to avoid circular deps

    channel = f"rt:table_map:{tenant}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    seq = int(last_event_id) + 1 if last_event_id and last_event_id.isdigit() else 1

    async def event_gen():
        nonlocal seq

        # send full snapshot first
        with SessionLocal() as session:
            records = session.query(Table).all()
            data = [
                {
                    "id": str(t.id),
                    "code": t.code,
                    "label": t.label,
                    "x": t.pos_x,
                    "y": t.pos_y,
                    "state": t.state,
                }
                for t in records
            ]
        snapshot = json.dumps({"tables": data})
        yield f"event: table_map\nid: {seq}\ndata: {snapshot}\n\n"
        seq += 1

        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=KEEPALIVE_INTERVAL
                )
                if message is None:
                    yield ":keepalive\n\n"
                    continue
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                yield f"event: table_map\nid: {seq}\ndata: {data}\n\n"
                seq += 1
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(event_gen(), media_type="text/event-stream")
