from __future__ import annotations

"""Block guest POSTs when the table is not available."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..db import SessionLocal
from ..models_tenant import Table
from ..utils.responses import err
from ..routes_metrics import table_locked_denied_total
from ..i18n import get_catalog, select_language


class TableStateGuardMiddleware(BaseHTTPMiddleware):
    """Deny guest POST requests for tables that aren't AVAILABLE."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path.startswith("/g/"):
            parts = request.url.path.split("/")
            if len(parts) > 2 and parts[2]:
                token = parts[2]
                with SessionLocal() as session:
                    table = session.query(Table).filter_by(code=token).one_or_none()
                if table is not None and table.state != "AVAILABLE":
                    table_locked_denied_total.inc()
                    lang = select_language(request.headers.get("Accept-Language"))
                    msg = get_catalog(lang)["errors"]["TABLE_LOCKED"]
                    return JSONResponse(
                        err("TABLE_LOCKED", msg), status_code=423
                    )
        return await call_next(request)
