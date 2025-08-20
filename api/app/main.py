# main.py

"""In-memory FastAPI application for demo guest ordering and billing."""

from __future__ import annotations

import json
import os
import uuid
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import asyncio
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
import redis.asyncio as redis
from fastapi.responses import JSONResponse
from fastapi import Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from pydantic import BaseModel
from redis.asyncio import from_url
from .db import SessionLocal

from config import get_settings
from .auth import (
    Token,
    User,
    authenticate_pin,
    authenticate_user,
    create_access_token,
    role_required,
)
from .audit import log_event
from .menu import router as menu_router
from .middleware import RateLimitMiddleware
from .middlewares.correlation import CorrelationIdMiddleware
from .utils.responses import ok, err
from .events import (
    alerts_sender,
    ema_updater,
    event_bus,
    report_aggregator,
)

from .utils import PrepTimeTracker
from .models import Table, TableStatus



settings = get_settings()
app = FastAPI()
app.state.redis = from_url(settings.redis_url, decode_responses=True)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RateLimitMiddleware, limit=3)
app.include_router(menu_router, prefix="/menu")


logger = logging.getLogger("api")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start
    log_data = {
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency": round(latency, 4),
        "correlation_id": getattr(request.state, "correlation_id", None),
    }
    logger.info(json.dumps(log_data))
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(err(exc.status_code, exc.detail), status_code=exc.status_code)


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    return JSONResponse(err(500, "Internal Server Error"), status_code=500)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
prep_trackers: dict[str, PrepTimeTracker] = {}




@app.on_event("startup")
async def start_event_consumers() -> None:
    """Launch background tasks for event processing."""

    asyncio.create_task(alerts_sender(event_bus.subscribe("order.placed")))
    asyncio.create_task(ema_updater(event_bus.subscribe("payment.verified")))
    asyncio.create_task(report_aggregator(event_bus.subscribe("table.cleaned")))


# Auth Routes


class EmailLogin(BaseModel):
    """Email/password login payload."""

    username: str
    password: str


class PinLogin(BaseModel):
    """PIN login payload."""

    username: str
    pin: str


@app.post("/login/email", response_model=Token)
async def email_login(credentials: EmailLogin) -> Token:
    """Authenticate using username/password and return a JWT."""

    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    log_event(user.username, "login", "user", master=True)
    return Token(access_token=token, role=user.role)


@app.post("/login/pin", response_model=Token)
async def pin_login(credentials: PinLogin) -> Token:
    """Authenticate using a short numeric PIN."""

    user = authenticate_pin(credentials.username, credentials.pin)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    log_event(user.username, "login", "user", master=True)
    return Token(access_token=token, role=user.role)


@app.get(
    "/admin",
    dependencies=[Depends(role_required("super_admin", "outlet_admin", "manager"))],
)
async def admin_area(
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager"))
):
    """Endpoint accessible to high-privilege roles only."""

    return {"message": f"Welcome {user.username}"}


@app.get(
    "/staff", dependencies=[Depends(role_required("cashier", "kitchen", "cleaner"))]
)
async def staff_area(
    user: User = Depends(role_required("cashier", "kitchen", "cleaner"))
):
    """Endpoint for general staff roles."""

    return {"message": f"Hello {user.username}"}


class CartItem(BaseModel):
    """An item added by a guest to the cart."""

    item: str
    price: float
    quantity: int
    guest_id: Optional[str] = None


class UpdateQuantity(BaseModel):
    """Payload for modifying an order line.

    ``admin`` must be set to ``True`` and ``quantity`` to ``0`` to perform a
    soft-cancel.
    """

    quantity: int
    admin: bool = False


class StaffOrder(BaseModel):
    """Order item placed directly by staff."""

    item: str
    price: float
    quantity: int


tables: Dict[str, Dict[str, List[CartItem]]] = {}  # table_id -> cart and orders


def _tracker(table_code: str) -> PrepTimeTracker:
    """Return the EMA tracker for ``table_code``."""

    return prep_trackers.setdefault(table_code, PrepTimeTracker(window=10))


async def _broadcast(table_code: str, data: dict) -> None:
    """Publish ``data`` to the table's update channel."""

    channel = f"rt:update:{table_code}"
    try:
        await redis_client.publish(channel, json.dumps(data))
    except Exception:  # pragma: no cover - best effort only
        pass


class OrderRequest(BaseModel):
    tenant_id: str
    open_tables: int


TENANTS: dict[str, dict] = {}  # tenant_id -> tenant info
PAYMENTS: dict[str, dict] = {}  # payment_id -> payment metadata


@app.post("/tenants")
async def create_tenant(name: str, licensed_tables: int) -> dict[str, str]:
    tenant_id = str(uuid.uuid4())
    TENANTS[tenant_id] = {
        "name": name,
        "licensed_tables": licensed_tables,
        "subscription_expires_at": datetime.utcnow(),
    }
    return {"tenant_id": tenant_id}


@app.post("/orders")
async def create_order(request: OrderRequest) -> dict[str, str]:
    tenant = TENANTS.get(request.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if request.open_tables >= tenant["licensed_tables"]:
        raise HTTPException(status_code=403, detail="Licensed table limit exceeded")

    expiry = tenant["subscription_expires_at"]
    if datetime.utcnow() > expiry + timedelta(days=7):
        raise HTTPException(status_code=403, detail="Subscription expired")

    return {"status": "order accepted"}


@app.post("/tenants/{tenant_id}/subscription/renew")
async def renew_subscription(
    tenant_id: str, screenshot: UploadFile = File(...)
) -> dict[str, str]:
    if tenant_id not in TENANTS:
        raise HTTPException(status_code=404, detail="Tenant not found")

    payment_id = str(uuid.uuid4())
    uploads = Path(__file__).resolve().parent / "payments"
    uploads.mkdir(exist_ok=True)
    file_path = uploads / f"{payment_id}_{screenshot.filename}"
    with file_path.open("wb") as buffer:
        buffer.write(await screenshot.read())

    PAYMENTS[payment_id] = {
        "tenant_id": tenant_id,
        "screenshot": str(file_path),
        "verified": False,
    }
    return {"payment_id": payment_id}


@app.post("/tenants/{tenant_id}/subscription/payments/{payment_id}/verify")
async def verify_payment(
    tenant_id: str, payment_id: str, months: int = 1
) -> dict[str, str]:
    payment = PAYMENTS.get(payment_id)
    if payment is None or payment["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment["verified"] = True
    tenant = TENANTS[tenant_id]
    tenant["subscription_expires_at"] = tenant["subscription_expires_at"] + timedelta(
        days=30 * months
    )
    await event_bus.publish(
        "payment.verified", {"tenant_id": tenant_id, "payment_id": payment_id}
    )
    return {"status": "verified"}


@app.get("/health")
async def health() -> dict:
    return ok({"status": "ok"})


@app.websocket("/tables/{table_code}/ws")
async def table_ws(websocket: WebSocket, table_code: str) -> None:
    """Stream order status updates for ``table_code``."""

    await websocket.accept()
    channel = f"rt:update:{table_code}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    tracker = _tracker(table_code)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            prep_time = data.get("prep_time")
            if prep_time is not None:
                data["eta"] = tracker.add_prep_time(float(prep_time))
            await websocket.send_json(data)
    except WebSocketDisconnect:  # pragma: no cover - network disconnect
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


def _table_state(table_id: str) -> Dict[str, List[CartItem]]:
    """Return the mutable state dictionary for a table."""

    return tables.setdefault(table_id, {"cart": [], "orders": []})


# Table Operations


@app.post("/tables/{table_id}/cart")
async def add_to_cart(table_id: str, item: CartItem) -> dict[str, List[CartItem]]:
    """Add an item to a table's cart.

    Multiple guests may add items concurrently by specifying a ``guest_id``.
    """

    table = _table_state(table_id)
    table["cart"].append(item)
    await _broadcast(table_id, {"status": "cart"})
    return {"cart": table["cart"]}


@app.post("/tables/{table_id}/order")
async def place_order(table_id: str) -> dict[str, List[CartItem]]:
    """Move all cart items to the order, locking them from guest edits."""

    table = _table_state(table_id)
    table["orders"].extend(table["cart"])
    table["cart"] = []  # cart is cleared so guests cannot modify placed items
    await event_bus.publish("order.placed", {"table_id": table_id})
    await _broadcast(table_id, {"status": "placed"})

    return {"orders": table["orders"]}


@app.patch("/tables/{table_id}/order/{index}")
async def update_order(
    table_id: str, index: int, payload: UpdateQuantity
) -> dict[str, List[CartItem]]:
    """Allow an admin to soft-cancel an order line by setting ``quantity`` to 0."""

    table = _table_state(table_id)
    try:
        order_item = table["orders"][index]
    except IndexError as exc:  # pragma: no cover - simple bounds check
        raise HTTPException(status_code=404, detail="Order item not found") from exc
    if not payload.admin:
        raise HTTPException(status_code=403, detail="Edits restricted")
    if payload.quantity != 0:
        raise HTTPException(status_code=400, detail="Only soft-cancel allowed")
    order_item.quantity = 0  # mark as cancelled but retain entry for audit
    await _broadcast(table_id, {"status": "updated"})
    log_event("system", "order_update", table_id)

    return {"orders": table["orders"]}


@app.post("/tables/{table_id}/staff-order")
async def staff_place_order(
    table_id: str, item: StaffOrder
) -> dict[str, List[CartItem]]:
    """Staff directly place an order for a guest without a phone."""

    table = _table_state(table_id)
    table["orders"].append(CartItem(**item.model_dump()))
    await _broadcast(table_id, {"status": "staff_order"})
    return {"orders": table["orders"]}


# Billing


@app.get("/tables/{table_id}/bill")
async def bill(table_id: str) -> dict[str, float | List[CartItem]]:
    """Return the running bill for a table."""

    table = _table_state(table_id)
    total = sum(i.price * i.quantity for i in table["orders"] if i.quantity > 0)
    return {"total": total, "orders": table["orders"]}


@app.post("/tables/{table_id}/pay")
async def pay_now(table_id: str) -> dict[str, float]:
    """Settle the current bill and clear outstanding orders."""

    table = _table_state(table_id)
    total = sum(i.price * i.quantity for i in table["orders"] if i.quantity > 0)
    table["orders"] = []  # clearing orders resets table state for next guests
    log_event("system", "payment", table_id)
    return {"total": total}


VALID_ACTIONS = {"waiter", "water", "bill"}


@app.post("/tables/{table_id}/call/{action}")
async def call_staff(table_id: str, action: str) -> dict[str, str]:
    """Queue a staff call request for the given table."""

    if action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail="invalid action")
    # In a full implementation this would persist the request and notify staff.
    return {"table_id": table_id, "action": action, "status": "queued"}


@app.post("/tables/{table_id}/lock")
async def lock_table(table_id: str) -> dict[str, str]:
    """Lock a table after settlement until cleaned."""

    try:
        tid = uuid.UUID(table_id)
    except ValueError as exc:  # pragma: no cover - simple validation
        raise HTTPException(status_code=400, detail="invalid table id") from exc
    with SessionLocal() as session:
        table = session.get(Table, tid)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.status = TableStatus.LOCKED
        session.commit()
        session.refresh(table)
        return {"table_id": table_id, "status": table.status.value}


@app.post("/tables/{table_id}/mark-clean")
async def mark_clean(table_id: str) -> dict[str, str]:
    """Mark a table as cleaned and ready for new guests."""
    await event_bus.publish("table.cleaned", {"table_id": table_id})
    try:
        tid = uuid.UUID(table_id)
    except ValueError:  # non-UUID ids are allowed but skip DB update
        return {"table_id": table_id, "status": TableStatus.AVAILABLE.value}

    with SessionLocal() as session:
        table = session.get(Table, tid)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.status = TableStatus.AVAILABLE
        session.commit()
        session.refresh(table)
        return {"table_id": table_id, "status": table.status.value}

