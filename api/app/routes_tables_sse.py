"""Server-Sent Events stream for table map updates."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get(
    "/api/outlet/{tenant}/tables/map/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_table_map(tenant: str) -> StreamingResponse:
    """Stream table state changes via SSE."""

    from .main import redis_client  # lazy import to avoid circular deps

    channel = f"rt:table_map:{tenant}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    async def event_gen():
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                yield f"data: {data}\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(event_gen(), media_type="text/event-stream")
