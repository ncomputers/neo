from __future__ import annotations

"""Block guest POSTs when the room is not available."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..db import SessionLocal
from ..models_tenant import Room
from ..utils.responses import err


class RoomStateGuard(BaseHTTPMiddleware):
    """Deny guest POST requests for rooms that aren't AVAILABLE."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path.startswith("/h/"):
            parts = request.url.path.split("/")
            if len(parts) > 2 and parts[2]:
                token = parts[2]
                with SessionLocal() as session:
                    room = session.query(Room).filter_by(code=token).one_or_none()
                if room is not None and room.state != "AVAILABLE":
                    return JSONResponse(
                        err("ROOM_LOCKED", "Room not ready"), status_code=423
                    )
        return await call_next(request)


# Backwards compatibility until callers are updated.
RoomStateGuardMiddleware = RoomStateGuard
