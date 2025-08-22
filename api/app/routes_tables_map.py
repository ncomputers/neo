"""Routes for managing table floor-map positions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .auth import User, role_required
from .db import SessionLocal
from .models_tenant import Table
from .utils.responses import ok
from .utils.audit import audit


class TablePosition(BaseModel):
    """Coordinates for placing a table on a floor map."""

    x: int
    y: int
    label: str | None = None


router = APIRouter()


@router.post("/api/outlet/{tenant}/tables/{table_id}/position")
@audit("set_table_position")
async def set_table_position(
    tenant: str,
    table_id: uuid.UUID,
    pos: TablePosition,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Persist positional metadata for a table."""

    with SessionLocal() as session:
        table = session.get(Table, table_id)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.pos_x = pos.x
        table.pos_y = pos.y
        table.label = pos.label
        session.commit()
        session.refresh(table)
        return ok(
            {
                "id": str(table.id),
                "x": table.pos_x,
                "y": table.pos_y,
                "label": table.label,
            }
        )


@router.get("/api/outlet/{tenant}/tables/map")
@audit("get_table_map")
async def get_table_map(tenant: str) -> dict:
    """Return coordinates and states for all tables."""

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
    return ok(data)


@router.get("/api/outlet/{tenant}/tables/map/stream")
async def stream_table_map(tenant: str) -> StreamingResponse:
    """Server-Sent Events stream for table map updates."""

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
