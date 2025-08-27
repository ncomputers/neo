from __future__ import annotations

"""L1 support console routes for operations staff."""

import html
import json
import pathlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse

from .auth import User, role_required
from .db import SessionLocal
from .models_master import Tenant
from .models_tenant import Order, Staff, Table
from .services import notifications
from .utils.audit import audit
from .utils.responses import err, ok

router = APIRouter()


_MACRO_FILE = pathlib.Path(__file__).resolve().parents[2] / "docs" / "SUPPORT_MACROS.md"


def _load_macros() -> dict[str, str]:
    """Parse ``SUPPORT_MACROS.md`` into a mapping of title->text."""
    macros: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in _MACRO_FILE.read_text().splitlines():
        if line.startswith("### "):
            if current:
                macros[current] = "\n".join(buf).strip()
            current = line[4:].strip()
            buf = []
        elif line.startswith("- ") and current:
            buf.append(line[2:].strip())
    if current:
        macros[current] = "\n".join(buf).strip()
    return macros


@router.get("/admin/support/console", response_class=HTMLResponse)
@audit("support.console.page")
async def console_page(
    user: User = Depends(role_required("super_admin")),
) -> HTMLResponse:
    """Render the support console HTML page."""
    macros = _load_macros()
    options = "".join(
        f'<option value="{html.escape(text)}">{html.escape(name)}</option>'
        for name, text in macros.items()
    )
    html_body = f"""
    <html>
      <body>
        <h1>Support Console</h1>
        <form id=\"search\">
          <input name=\"tenant\" placeholder=\"tenant id\" required />
          <input name=\"table\" placeholder=\"table code\" />
          <input name=\"order\" placeholder=\"order id\" type=\"number\" />
          <button type=\"submit\">Search</button>
        </form>
        <textarea id=\"reply\" rows=\"10\" cols=\"80\"></textarea>
        <select id=\"macro\">
          <option value=\"\">Insert macro...</option>
          {options}
        </select>
        <script>
        document.getElementById('macro').addEventListener('change', function() {{
            if (this.value) {{
                const ta = document.getElementById('reply');
                ta.value += (ta.value ? '\n' : '') + this.value;
                this.value = '';
            }}
        }});
        </script>
      </body>
    </html>
    """
    return HTMLResponse(html_body)


@router.get("/admin/support/console/search")
@audit("support.console.search")
async def search(
    tenant: str,
    table: str | None = None,
    order: int | None = None,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Lookup tenant, table, or order details scoped to ``tenant``."""

    result: dict = {}
    with SessionLocal() as session:
        t = session.get(Tenant, uuid.UUID(tenant))
        if not t:
            raise HTTPException(status_code=404, detail="tenant not found")
        result["tenant"] = {"id": str(t.id), "name": t.name}
        if table:
            tbl = (
                session.query(Table)
                .filter(Table.code == table, Table.tenant_id == t.id)
                .first()
            )
            if tbl:
                result["table"] = {"id": str(tbl.id), "code": tbl.code}
        if order:
            ord_row = session.get(Order, order)
            if ord_row:
                tbl = session.get(Table, uuid.UUID(int=ord_row.table_id))
                if tbl and tbl.tenant_id == t.id:
                    status = getattr(ord_row.status, "name", str(ord_row.status))
                    result["order"] = {"id": ord_row.id, "status": status}
    return ok(result)


@router.post("/admin/support/console/order/{order_id}/resend_invoice")
@audit("support.console.resend_invoice")
async def resend_invoice(
    order_id: int,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Trigger invoice resend for ``order_id``."""
    try:
        with SessionLocal() as session:
            ord_row = session.get(Order, order_id)
            if not ord_row:
                raise ValueError("order not found")
            tbl = session.get(Table, uuid.UUID(int=ord_row.table_id))
            if not tbl:
                raise ValueError("order not found")
            tenant_id = str(tbl.tenant_id)
        await notifications.enqueue(tenant_id, "invoice.resend", {"order_id": order_id})
    except Exception:
        return err("RESEND_FAILED", "invoice resend failed")
    return ok({"order_id": order_id})


@router.post("/admin/support/console/order/{order_id}/reprint_kot")
@audit("support.console.reprint_kot")
async def reprint_kot(
    order_id: int,
    request: Request,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Reprint a KOT for ``order_id``."""
    try:
        with SessionLocal() as session:
            ord_row = session.get(Order, order_id)
            if not ord_row:
                raise ValueError("order not found")
            tbl = session.get(Table, uuid.UUID(int=ord_row.table_id))
            if not tbl:
                raise ValueError("order not found")
            tenant_id = str(tbl.tenant_id)
        payload = json.dumps(
            {"order_id": order_id, "size": "80mm"}, separators=(",", ":")
        )
        await request.app.state.redis.publish(f"print:kot:{tenant_id}", payload)
    except Exception:
        return err("REPRINT_FAILED", "kot reprint failed")
    return ok({"order_id": order_id})


@router.post("/admin/support/console/order/{order_id}/replay_webhook")
@audit("support.console.replay_webhook")
async def replay_webhook(
    order_id: int,
    confirm: bool = Query(False),
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Replay webhook events for ``order_id``."""
    if not confirm:
        raise HTTPException(status_code=400, detail="confirmation required")
    try:
        with SessionLocal() as session:
            ord_row = session.get(Order, order_id)
            if not ord_row:
                raise ValueError("order not found")
            tbl = session.get(Table, uuid.UUID(int=ord_row.table_id))
            if not tbl:
                raise ValueError("order not found")
            tenant_id = str(tbl.tenant_id)
        await notifications.enqueue(tenant_id, "webhook.replay", {"order_id": order_id})
    except Exception:
        return err("REPLAY_FAILED", "webhook replay failed")
    return ok({"order_id": order_id})


@router.post("/admin/support/console/staff/{staff_id}/unlock_pin")
@audit("support.console.unlock_pin")
async def unlock_pin(
    staff_id: int,
    confirm: bool = Query(False),
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """Unlock a staff member's PIN."""
    if not confirm:
        raise HTTPException(status_code=400, detail="confirmation required")
    with SessionLocal() as session:
        staff = session.get(Staff, staff_id)
        if not staff:
            raise HTTPException(status_code=404, detail="staff not found")
        staff.pin_hash = ""
        session.commit()
    return ok({"staff_id": staff_id})
