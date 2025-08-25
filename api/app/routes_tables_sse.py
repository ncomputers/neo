"""Server-Sent Events stream for table map updates.

Each event emits ``event: table_map`` with a monotonically increasing
``id``. Clients may reconnect using the ``Last-Event-ID`` header to
resume the sequence; when the server lacks history to bridge the gap it
falls back to sending a full snapshot before incremental updates.
"""

from __future__ import annotations

import json

import asyncio
from collections import defaultdict

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from config import get_settings
from .routes_metrics import sse_clients_gauge

from .db import SessionLocal
from .models_tenant import Table

KEEPALIVE_INTERVAL = 15

router = APIRouter()

settings = get_settings()
sse_connections: dict[str, int] = defaultdict(int)


@router.get(
    "/api/outlet/{tenant}/tables/map/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_table_map(
    tenant: str,
    request: Request,
    last_event_id: str | None = Header(None, convert_underscores=False),
) -> StreamingResponse:
    """Stream table state changes via SSE."""

    from .main import redis_client  # lazy import to avoid circular deps

    ip = request.client.host if request.client else "?"
    if sse_connections[ip] >= settings.max_conn_per_ip:
        raise HTTPException(status_code=429, detail="RETRY")
    sse_connections[ip] += 1

    channel = f"rt:table_map:{tenant}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    seq = int(last_event_id) + 1 if last_event_id and last_event_id.isdigit() else 1
    sse_clients_gauge.inc()

    async def event_gen():
        nonlocal seq
        queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=100)

        async def reader():
            nonlocal seq
            try:
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=KEEPALIVE_INTERVAL
                    )
                    if message is None:
                        try:
                            queue.put_nowait(":keepalive\n\n")
                        except asyncio.QueueFull:
                            await queue.put("DROP")
                            break
                        continue
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    try:
                        queue.put_nowait(
                            f"event: table_map\nid: {seq}\ndata: {data}\n\n"
                        )
                        seq += 1
                    except asyncio.QueueFull:
                        await queue.put("DROP")
                        break
            finally:
                await queue.put(None)

        reader_task = asyncio.create_task(reader())

        try:
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

            while True:
                item = await queue.get()
                if item is None:
                    break
                if item == "DROP":
                    raise HTTPException(status_code=429, detail="RETRY")
                yield item
        finally:
            reader_task.cancel()
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            sse_clients_gauge.dec()
            sse_connections[ip] -= 1

    return StreamingResponse(event_gen(), media_type="text/event-stream")
