"""Floor map editor and live view routes."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .main import template_globals

from .auth import User, role_required
from .db import SessionLocal
from .models_tenant import Table
from .routes_tables_sse import stream_table_map
from .utils.responses import ok

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals.update(template_globals)


class TableGeom(BaseModel):
    id: uuid.UUID
    pos_x: int | None = None
    pos_y: int | None = None
    width: int | None = 80
    height: int | None = 80
    shape: str | None = "rect"
    zone: str | None = None
    capacity: int | None = None
    label: str | None = None


class FloorPayload(BaseModel):
    tables: List[TableGeom]


@router.get("/admin/floor-map")
async def floor_map_editor(
    request: Request,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
):
    """Render the floor map editor."""
    return templates.TemplateResponse(request, "floor_map.html", {})


@router.post("/admin/floor-map/save")
async def save_floor_map(
    payload: FloorPayload,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Persist geometry and attributes for tables."""
    with SessionLocal() as session:
        updated = 0
        for item in payload.tables:
            tbl = session.get(Table, item.id)
            if tbl is None:
                continue
            tbl.pos_x = item.pos_x
            tbl.pos_y = item.pos_y
            tbl.width = item.width
            tbl.height = item.height
            tbl.shape = item.shape
            tbl.zone = item.zone
            tbl.capacity = item.capacity
            tbl.label = item.label
            updated += 1
        session.commit()
    return ok({"updated": updated})


@router.get("/floor")
async def floor_live(request: Request) -> object:
    """Render the live floor status view."""
    return templates.TemplateResponse(request, "floor_live.html", {})


@router.get(
    "/floor/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def floor_stream(
    tenant: str,
    request: Request = None,  # type: ignore[assignment]
    last_event_id: str | None = Header(None, convert_underscores=False),
) -> StreamingResponse:
    """Proxy to table map SSE for floor viewers."""
    return await stream_table_map(tenant, request, last_event_id)
