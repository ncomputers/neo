"""Server-Sent Events stream for table map updates.

Each event emits ``event: table_map`` with a monotonically increasing
``id``. Clients may reconnect using the ``Last-Event-ID`` header to
resume the sequence; when the server lacks history to bridge the gap it
falls back to sending a full snapshot before incremental updates.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from .db import SessionLocal
from .middlewares.realtime_guard import queue as rt_queue
from .middlewares.realtime_guard import register, unregister
from .models_tenant import Table
from .routes_metrics import sse_clients_gauge

KEEPALIVE_INTERVAL = 15

router = APIRouter()


@router.get(
    "/api/outlet/{tenant}/tables/map/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_table_map(
    tenant: str,
    request: Request = None,  # type: ignore[assignment]
    last_event_id: str | None = Header(None, convert_underscores=False),
) -> StreamingResponse:
    """Stream table state changes via SSE."""

    from .main import redis_client  # lazy import to avoid circular deps

    ip = request.client.host if request and request.client else "?"
    register(ip)

    channel = f"rt:table_map:{tenant}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    seq = (
        int(last_event_id) + 2 if isinstance(last_event_id, str) and last_event_id.isdigit() else 2
    )
    sse_clients_gauge.inc()

    async def event_gen():
        nonlocal seq
        queue: asyncio.Queue[str | None] = rt_queue()

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
                records = (
                    session.query(Table).filter(Table.deleted_at.is_(None)).all()
                )
                data = [
                    {
                        "id": str(t.id),
                        "code": t.code,
                        "label": t.label,
                        "x": t.pos_x,
                        "y": t.pos_y,
                        "state": t.state,
                        "zone": t.zone,
                        "width": t.width,
                        "height": t.height,
                        "shape": t.shape,
                    }
                    for t in records
                ]
            snapshot = json.dumps({"tables": data})
            yield f"event: table_map\nid: {seq - 1}\ndata: {snapshot}\n\n"

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
            sse_clients_gauge.dec()
            unregister(ip)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
