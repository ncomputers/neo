# main.py

# flake8: noqa

"""In-memory FastAPI application for demo guest ordering and billing."""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import redis.asyncio as redis
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


class _LoopPolicy(asyncio.DefaultEventLoopPolicy):
    def get_event_loop(self):
        try:
            return super().get_event_loop()
        except RuntimeError:
            loop = self.new_event_loop()
            self.set_event_loop(loop)
            return loop


asyncio.set_event_loop_policy(_LoopPolicy())
from redis.asyncio import from_url
from sqlalchemy import func
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from config import get_settings

from . import db as app_db
from . import domain as app_domain
from . import models_tenant as app_models_tenant
from . import repos_sqlalchemy as app_repos_sqlalchemy
from . import utils as app_utils
from .audit import log_event
from .auth import (
    Token,
    User,
    authenticate_pin,
    authenticate_user,
    create_access_token,
    role_required,
)
from .config.validate import validate_on_boot
from .db import SessionLocal, replica
from .events import alerts_sender, ema_updater, event_bus, report_aggregator
from .hooks import order_rejection
from .hooks.table_map import publish_table_state
from .i18n import get_msg, resolve_lang
from .menu import router as menu_router
from .middleware import RateLimitMiddleware
from .middlewares import (
    APIKeyAuthMiddleware,
    GuestBlockMiddleware,
    GuestRateLimitMiddleware,
    HTMLErrorPagesMiddleware,
    HttpErrorCounterMiddleware,
    IdempotencyMetricsMiddleware,
    IdempotencyMiddleware,
    LicensingMiddleware,
    LoggingMiddleware,
    MaintenanceMiddleware,
    PinSecurityMiddleware,
    PrometheusMiddleware,
    RequestIdMiddleware,
    TableStateGuardMiddleware,
    realtime_guard,
)
from .middlewares.room_state_guard import RoomStateGuard
from .middlewares.security import SecurityMiddleware
from .middlewares.subscription_guard import SubscriptionGuard
from .models_tenant import Table
from .obs import capture_exception, init_sentry
from .obs.logging import configure_logging
from .otel import init_tracing
from .routes_accounting_exports import router as accounting_exports_router

from .routes_accounting import router as accounting_router
from .routes_admin_devices import router as admin_devices_router
from .routes_admin_menu import router as admin_menu_router
from .routes_admin_ops import router as admin_ops_router
from .routes_admin_pilot import router as admin_pilot_router

from .routes_admin_menu import router as admin_menu_router
from .routes_admin_ops import router as admin_ops_router
from .routes_admin_pilot import router as admin_pilot_router
from .routes_admin_print import router as admin_print_router
from .routes_admin_privacy import router as admin_privacy_router
from .routes_admin_qrpack import router as admin_qrpack_router
from .routes_admin_qrposter_pack import router as admin_qrposter_router
from .routes_admin_support import router as admin_support_router
from .routes_admin_support_console import router as admin_support_console_router
from .routes_admin_webhooks import router as admin_webhooks_router


from .routes_admin_devices import router as admin_devices_router
from .routes_print_test import router as print_test_router
from .routes_integrations import router as integrations_router
from .routes_alerts import router as alerts_router
from .routes_api_keys import router as api_keys_router
from .routes_auth_2fa import router as auth_2fa_router
from .routes_auth_magic import router as auth_magic_router
from .routes_backup import router as backup_router
from .routes_billing import router as billing_router
from .routes_checkout_gateway import router as checkout_router
from .routes_counter_admin import router as counter_admin_router
from .routes_counter_guest import router as counter_guest_router
from .routes_csp_report import router as csp_router
from .routes_dashboard import router as dashboard_router
from .routes_dashboard_charts import router as dashboard_charts_router
from .routes_daybook_pdf import router as daybook_pdf_router
from .routes_digest import router as digest_router
from .routes_dlq import router as dlq_router
from .routes_export_all import router as export_all_router
from .routes_exports import router as exports_router
from .routes_feedback import router as feedback_router
from .routes_gst_monthly import router as gst_monthly_router
from .routes_guest_bill import router as guest_bill_router
from .routes_guest_consent import router as guest_consent_router
from .routes_guest_menu import router as guest_menu_router
from .routes_guest_order import router as guest_order_router
from .routes_guest_receipts import router as guest_receipts_router
from .routes_help import router as help_router
from .routes_hotel_guest import router as hotel_guest_router
from .routes_hotel_housekeeping import router as hotel_hk_router
from .routes_housekeeping import router as housekeeping_router
from .routes_integrations import router as integrations_router

from .routes_integrations_marketplace import router as integrations_marketplace_router
from .routes_invoice_pdf import router as invoice_pdf_router
from .routes_jobs_status import router as jobs_status_router
from .routes_kot import router as kot_router
from .routes_legal import router as legal_router
from .routes_limits_usage import router as limits_router
from .routes_maintenance import router as maintenance_router
from .routes_media import router as media_router
from .routes_menu_import import router as menu_import_router
from .routes_metrics import router as metrics_router
from .routes_metrics import ws_messages_total
from .routes_ab_tests import router as ab_tests_router
from .routes_onboarding import router as onboarding_router
from .routes_order_void import router as order_void_router
from .routes_orders_batch import router as orders_batch_router
from .routes_outbox_admin import router as outbox_admin_router
from .routes_owner_aggregate import router as owner_aggregate_router
from .routes_owner_analytics import router as owner_analytics_router
from .routes_owner_sla import router as owner_sla_router
from .routes_pilot_feedback import router as pilot_feedback_router
from .routes_pilot_telemetry import router as pilot_telemetry_router
from .routes_postman import router as postman_router
from .routes_preflight import router as preflight_router
from .routes_print import router as print_router
from .routes_print_bridge import router as print_bridge_router
from .routes_print_test import router as print_test_router
from .routes_privacy_dsar import router as privacy_dsar_router
from .routes_push import router as push_router
from .routes_pwa_version import router as pwa_version_router
from .routes_qrpack import router as qrpack_router
from .routes_ready import router as ready_router
from .routes_refunds import router as refunds_router
from .routes_reports import router as reports_router
from .routes_rum_vitals import router as rum_router
from .routes_sandbox_bootstrap import router as sandbox_bootstrap_router
from .routes_security import router as security_router
from .routes_slo import router as slo_router
from .routes_staff import router as staff_router
from .routes_support import router as support_router
from .routes_support_bundle import router as support_bundle_router
from .routes_tables_map import router as tables_map_router
from .routes_tables_qr_rotate import router as tables_qr_rotate_router
from .routes_tables_sse import router as tables_sse_router
from .routes_tenant_close import router as tenant_close_router
from .routes_tenant_sandbox import router as tenant_sandbox_router
from .routes_time_skew import router as time_skew_router
from .routes_troubleshoot import router as troubleshoot_router
from .routes_vapid import router as vapid_router
from .routes_version import router as version_router
from .routes_webhook_tools import router as webhook_tools_router
from .routes_webhooks import router as webhooks_router
from .routes_whatsapp_status import router as whatsapp_status_router
from .services import notifications
from .utils import PrepTimeTracker
from .utils.responses import err, ok

sys.modules.setdefault("db", app_db)
sys.modules.setdefault("domain", app_domain)
sys.modules.setdefault("models_tenant", app_models_tenant)
sys.modules.setdefault("repos_sqlalchemy", app_repos_sqlalchemy)
sys.modules.setdefault("utils", app_utils)
kds_router = importlib.import_module(".routes_kds", __package__).router
kds_expo_router = importlib.import_module(".routes_kds_expo", __package__).router
kds_sla_router = importlib.import_module(".routes_kds_sla", __package__).router
kds_expo_router = importlib.import_module(".routes_kds_expo", __package__).router
superadmin_router = importlib.import_module(".routes_superadmin", __package__).router


class SWStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path == "sw.js":
            response.headers["Service-Worker-Allowed"] = "/"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response


validate_on_boot()
settings = get_settings()
app = FastAPI(
    title="Neo API",
    version="1.0.0-rc",
    servers=[{"url": "/"}],
    openapi_url="/openapi.json",
)
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
app.mount("/static", SWStaticFiles(directory=static_dir), name="static")


@app.get("/status.json")
async def status_json():
    return FileResponse(
        Path(__file__).resolve().parent.parent.parent / "status.json",
        media_type="application/json",
    )
init_tracing(app)
asyncio.set_event_loop(asyncio.new_event_loop())
app.state.redis = from_url(settings.redis_url, decode_responses=True)
app.state.export_progress = {}
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(HttpErrorCounterMiddleware)
app.add_middleware(HTMLErrorPagesMiddleware, static_dir=static_dir)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware, limit=3)
app.add_middleware(GuestBlockMiddleware)
app.add_middleware(TableStateGuardMiddleware)
app.add_middleware(RoomStateGuard)
app.add_middleware(GuestRateLimitMiddleware)
app.add_middleware(LicensingMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(IdempotencyMetricsMiddleware)
app.add_middleware(MaintenanceMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(PinSecurityMiddleware)
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(LoggingMiddleware)

subscription_guard = SubscriptionGuard(app)


# Track active WebSocket connections per client IP
ws_connections: dict[str, int] = defaultdict(int)
WS_HEARTBEAT_INTERVAL = 15


@app.middleware("http")
async def subscription_guard_middleware(request: Request, call_next):
    return await subscription_guard(request, call_next)


app.include_router(menu_router, prefix="/menu")


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
configure_logging(getattr(logging, LOG_LEVEL))
logger = logging.getLogger("api")
init_sentry(env=os.getenv("ENV"))


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        exc.detail,
        extra={
            "status": exc.status_code,
            "route": request.url.path,
            "tenant": request.headers.get("X-Tenant"),
            "user": request.headers.get("X-User"),
        },
    )
    return JSONResponse(err(exc.status_code, exc.detail), status_code=exc.status_code)


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    logger.exception(
        "unhandled_error",
        extra={
            "status": 500,
            "route": request.url.path,
            "tenant": request.headers.get("X-Tenant"),
            "user": request.headers.get("X-User"),
        },
    )
    capture_exception(exc)
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


# Replica health monitoring
@app.on_event("startup")
async def start_replica_monitor() -> None:
    await replica.check_replica(app)
    asyncio.create_task(replica.monitor(app))


# Auth Routes


class EmailLogin(BaseModel):
    """Email/password login payload."""

    username: str = Field(..., example="alice@example.com")
    password: str = Field(..., example="secret123")


class PinLogin(BaseModel):
    """PIN login payload."""

    username: str = Field(..., example="alice")
    pin: str = Field(..., example="1234")


@app.post("/login/email", tags=["Auth"], summary="Login with email")
async def email_login(credentials: EmailLogin) -> dict:
    """Authenticate using username/password and return a JWT."""

    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    log_event(user.username, "login", "user", master=True)
    return ok(Token(access_token=token, role=user.role))


@app.post("/login/pin", tags=["Auth"], summary="Login with PIN")
async def pin_login(credentials: PinLogin) -> dict:
    """Authenticate using a short numeric PIN."""

    user = authenticate_pin(credentials.username, credentials.pin)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    log_event(user.username, "login", "user", master=True)
    return ok(Token(access_token=token, role=user.role))


@app.get(
    "/admin",
    dependencies=[Depends(role_required("super_admin", "outlet_admin", "manager"))],
)
async def admin_area(
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager"))
):
    """Endpoint accessible to high-privilege roles only."""

    return ok({"message": f"Welcome {user.username}"})


@app.get(
    "/staff", dependencies=[Depends(role_required("cashier", "kitchen", "cleaner"))]
)
async def staff_area(
    user: User = Depends(role_required("cashier", "kitchen", "cleaner"))
):
    """Endpoint for general staff roles."""

    return ok({"message": f"Hello {user.username}"})


class CartItem(BaseModel):
    """An item added by a guest to the cart."""

    item: str = Field(..., example="Coffee")
    price: float = Field(..., example=2.5)
    quantity: int = Field(..., example=1)
    guest_id: Optional[str] = Field(None, example="guest-1")
    status: str = Field("pending", example="pending")


class UpdateQuantity(BaseModel):
    """Payload for modifying an order line.

    ``admin`` must be set to ``True`` and ``quantity`` to ``0`` to perform a
    soft-cancel.
    """

    quantity: int = Field(..., example=0)
    admin: bool = Field(False, example=True)


class StaffOrder(BaseModel):
    """Order item placed directly by staff."""

    item: str = Field(..., example="Tea")
    price: float = Field(..., example=1.5)
    quantity: int = Field(..., example=1)


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
async def create_tenant(name: str, licensed_tables: int) -> dict:
    tenant_id = str(uuid.uuid4())
    TENANTS[tenant_id] = {
        "name": name,
        "licensed_tables": licensed_tables,
        "subscription_expires_at": datetime.utcnow(),
        "plan": "basic",
        "grace_period_days": 7,
    }
    return ok({"tenant_id": tenant_id})


@app.post("/orders")
async def create_order(request: OrderRequest) -> dict:
    tenant = TENANTS.get(request.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if request.open_tables >= tenant["licensed_tables"]:
        raise HTTPException(status_code=403, detail="Licensed table limit exceeded")

    expiry = tenant["subscription_expires_at"]
    if datetime.utcnow() > expiry + timedelta(days=7):
        raise HTTPException(status_code=403, detail="Subscription expired")

    if os.getenv("POSTGRES_TENANT_DSN_TEMPLATE"):
        try:
            uuid.UUID(request.tenant_id)
        except ValueError:
            pass
        else:
            await notifications.enqueue(
                request.tenant_id, "order.accepted", request.dict()
            )
    return ok({"status": "order accepted"})


@app.post("/tenants/{tenant_id}/subscription/renew")
async def renew_subscription(
    tenant_id: str, screenshot: UploadFile = File(...)
) -> dict:
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
    return ok({"payment_id": payment_id})


@app.post("/tenants/{tenant_id}/subscription/payments/{payment_id}/verify")
async def verify_payment(tenant_id: str, payment_id: str, months: int = 1) -> dict:
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
    return ok({"status": "verified"})


@app.get("/health")
async def health() -> dict:
    return ok({"status": "ok"})


@app.websocket("/tables/{table_code}/ws")
async def table_ws(websocket: WebSocket, table_code: str) -> None:
    """Stream order status updates for ``table_code``."""

    ip = websocket.client.host if websocket.client else "?"
    try:
        realtime_guard.register(ip)
    except HTTPException:
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        return

    await websocket.accept()
    channel = f"rt:update:{table_code}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    tracker = _tracker(table_code)
    queue: asyncio.Queue[dict | None] = realtime_guard.queue()

    async def reader():
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                try:
                    queue.put_nowait(data)
                except asyncio.QueueFull:
                    await websocket.close(
                        code=status.WS_1013_TRY_AGAIN_LATER, reason="RETRY"
                    )
                    while True:
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    await queue.put(None)
                    break
        finally:
            await queue.put(None)

    reader_task = asyncio.create_task(reader())
    hb_task = realtime_guard.heartbeat_task(websocket)

    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            prep_time = item.get("prep_time")
            if prep_time is not None:
                item["eta"] = tracker.add_prep_time(float(prep_time))
            await websocket.send_json(item)
            ws_messages_total.inc()
    except WebSocketDisconnect:  # pragma: no cover - network disconnect
        pass
    finally:
        reader_task.cancel()
        hb_task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        realtime_guard.unregister(ip)


def _table_state(table_id: str) -> Dict[str, List[CartItem]]:
    """Return the mutable state dictionary for a table."""

    return tables.setdefault(table_id, {"cart": [], "orders": []})


def _guard_table_open(table_id: str, lang: str):
    """Return a lock error response if the table isn't available."""

    try:
        tid = uuid.UUID(table_id)
    except ValueError:
        return None
    with SessionLocal() as session:
        table = session.get(Table, tid)
        if table and table.state != "AVAILABLE":
            msg = get_msg(lang, "errors.TABLE_LOCKED")
            return JSONResponse(err("TABLE_LOCKED", msg), status_code=423)
    return None


# Table Operations


@app.get("/tables")
async def list_tables() -> dict[str, list[dict[str, str]]]:
    """Return all tables and their statuses."""

    with SessionLocal() as session:
        records = session.query(Table).filter(Table.deleted_at.is_(None)).all()
        data = [{"id": str(t.id), "name": t.name, "state": t.state} for t in records]
    return {"tables": data}


@app.post("/tables/{table_id}/cart", tags=["Orders"], summary="Add item to cart")
async def add_to_cart(
    table_id: str,
    item: CartItem,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> dict:
    """Add an item to a table's cart.

    Multiple guests may add items concurrently by specifying a ``guest_id``.
    """

    lang = resolve_lang(accept_language)
    if (resp := _guard_table_open(table_id, lang)) is not None:
        return resp
    table = _table_state(table_id)
    table["cart"].append(item)
    await _broadcast(table_id, {"status": "cart"})
    return ok({"cart": table["cart"]})


@app.post("/tables/{table_id}/order", tags=["Orders"], summary="Place order")
async def place_order(
    table_id: str,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> dict:
    """Move all cart items to the order, locking them from guest edits."""

    lang = resolve_lang(accept_language)
    if (resp := _guard_table_open(table_id, lang)) is not None:
        return resp
    table = _table_state(table_id)
    table["orders"].extend(table["cart"])
    table["cart"] = []  # cart is cleared so guests cannot modify placed items
    await event_bus.publish("order.placed", {"table_id": table_id})
    await _broadcast(table_id, {"status": "placed"})

    return ok({"orders": table["orders"]})


@app.patch(
    "/tables/{table_id}/order/{index}",
    tags=["Orders"],
    summary="Update order line",
)
async def update_order(table_id: str, index: int, payload: UpdateQuantity) -> dict:
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

    return ok({"orders": table["orders"]})


@app.post(
    "/tables/{table_id}/staff-order",
    tags=["Orders"],
    summary="Staff place order",
)
async def staff_place_order(table_id: str, item: StaffOrder) -> dict:
    """Staff directly place an order for a guest without a phone."""

    table = _table_state(table_id)
    table["orders"].append(CartItem(**item.model_dump()))
    await _broadcast(table_id, {"status": "staff_order"})
    return ok({"orders": table["orders"]})


@app.get("/orders", tags=["Orders"], summary="List all orders")
async def list_orders() -> dict[str, list[dict]]:
    """Return all orders across tables for staff views."""

    data: list[dict] = []
    for table_id, state in tables.items():
        for idx, item in enumerate(state["orders"]):
            entry = item.model_dump()
            entry.update({"table_id": table_id, "index": idx})
            data.append(entry)
    return {"orders": data}


@app.post(
    "/orders/{table_id}/{index}/accept",
    tags=["Orders"],
    summary="Accept order line",
)
async def accept_order(table_id: str, index: int) -> dict[str, str]:
    """Mark an order line as accepted."""

    table = _table_state(table_id)
    try:
        order_item = table["orders"][index]
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Order item not found") from exc
    order_item.status = "accepted"
    await _broadcast(table_id, {"status": "accepted", "index": index})
    return {"status": "accepted"}


@app.post(
    "/orders/{table_id}/{index}/reject",
    tags=["Orders"],
    summary="Reject order line",
)
async def reject_order(table_id: str, index: int, request: Request) -> dict[str, str]:
    """Mark an order line as rejected."""

    table = _table_state(table_id)
    try:
        order_item = table["orders"][index]
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Order item not found") from exc
    order_item.status = "rejected"
    await _broadcast(table_id, {"status": "rejected", "index": index})

    ip = request.client.host if request.client else "unknown"
    await order_rejection.on_rejected("demo", ip, request.app.state.redis)

    return {"status": "rejected"}


# Billing


@app.get("/tables/{table_id}/bill", tags=["Billing"], summary="Get table bill")
async def bill(table_id: str) -> dict:
    """Return the running bill for a table."""

    table = _table_state(table_id)
    total = sum(i.price * i.quantity for i in table["orders"] if i.quantity > 0)
    return ok({"total": total, "orders": table["orders"]})


@app.post("/tables/{table_id}/pay", tags=["Billing"], summary="Pay table bill")
async def pay_now(table_id: str) -> dict:
    """Settle the current bill and clear outstanding orders."""

    table = _table_state(table_id)
    total = sum(i.price * i.quantity for i in table["orders"] if i.quantity > 0)
    table["orders"] = []  # clearing orders resets table state for next guests
    try:
        tid = uuid.UUID(table_id)
    except ValueError:
        pass
    else:
        with SessionLocal() as session:
            db_table = session.get(Table, tid)
            if db_table is not None:
                db_table.state = "LOCKED"
                session.commit()
    log_event("system", "payment", table_id)
    return ok({"total": total})


VALID_ACTIONS = {"waiter", "water", "bill"}


@app.post(
    "/tables/{table_id}/call/{action}",
    tags=["Staff"],
    summary="Call staff",
)
async def call_staff(table_id: str, action: str) -> dict:
    """Queue a staff call request for the given table."""

    if action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail="invalid action")
    # In a full implementation this would persist the request and notify staff.
    return ok({"table_id": table_id, "action": action, "status": "queued"})


@app.post(
    "/tables/{table_id}/lock",
    tags=["Tables"],
    summary="Lock table",
)
async def lock_table(table_id: str) -> dict:
    """Lock a table after settlement until cleaned."""

    try:
        tid = uuid.UUID(table_id)
    except ValueError as exc:  # pragma: no cover - simple validation
        raise HTTPException(status_code=400, detail="invalid table id") from exc
    with SessionLocal() as session:
        table = session.get(Table, tid)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.state = "LOCKED"
        session.commit()
        session.refresh(table)
    await publish_table_state(table)
    return ok({"table_id": table_id, "state": table.state})


@app.post(
    "/tables/{table_id}/mark-clean",
    tags=["Tables"],
    summary="Mark table clean",
)
async def mark_clean(table_id: str) -> dict:
    """Mark a table as cleaned and ready for new guests."""
    await event_bus.publish("table.cleaned", {"table_id": table_id})
    try:
        tid = uuid.UUID(table_id)
    except ValueError:  # non-UUID ids are allowed but skip DB update
        return ok({"table_id": table_id, "state": "AVAILABLE"})

    with SessionLocal() as session:
        table = session.get(Table, tid)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.state = "AVAILABLE"
        table.last_cleaned_at = func.now()
        session.commit()
        session.refresh(table)
    await publish_table_state(table)
    return ok({"table_id": table_id, "state": table.state})


# Router wiring

# Auth domain
app.include_router(auth_magic_router)
app.include_router(auth_2fa_router)

# Guest domain
app.include_router(guest_menu_router)
app.include_router(guest_order_router)
app.include_router(guest_bill_router)
app.include_router(guest_consent_router)
app.include_router(guest_receipts_router)
app.include_router(counter_guest_router)
app.include_router(hotel_guest_router)
app.include_router(invoice_pdf_router)
app.include_router(billing_router)
app.include_router(onboarding_router)
app.include_router(qrpack_router)
app.include_router(order_void_router)

# KDS/KOT domain
app.include_router(kot_router)
app.include_router(kds_router)
app.include_router(kds_expo_router)
app.include_router(kds_sla_router)
app.include_router(kds_expo_router)

# Admin domain
app.include_router(counter_admin_router)
app.include_router(staff_router)
app.include_router(admin_menu_router)
app.include_router(slo_router)
app.include_router(admin_ops_router)
app.include_router(limits_router)
app.include_router(menu_import_router)
app.include_router(alerts_router)
app.include_router(security_router)
app.include_router(jobs_status_router)
app.include_router(dlq_router)
app.include_router(admin_privacy_router)
app.include_router(privacy_dsar_router)
app.include_router(outbox_admin_router)
app.include_router(webhook_tools_router)
app.include_router(orders_batch_router)
app.include_router(housekeeping_router)
app.include_router(hotel_hk_router)
app.include_router(metrics_router)
app.include_router(ab_tests_router)
app.include_router(rum_router)
app.include_router(owner_analytics_router)
app.include_router(owner_sla_router)
app.include_router(dashboard_router)
app.include_router(dashboard_charts_router)
app.include_router(owner_aggregate_router)
app.include_router(preflight_router)
app.include_router(tables_map_router)
app.include_router(tables_qr_rotate_router)
app.include_router(tables_sse_router)
app.include_router(time_skew_router)
app.include_router(pwa_version_router)
app.include_router(version_router)
app.include_router(ready_router)
app.include_router(troubleshoot_router)
app.include_router(help_router)
app.include_router(support_router)
app.include_router(admin_support_router)
app.include_router(admin_support_console_router)
app.include_router(admin_webhooks_router)
app.include_router(print_test_router)
app.include_router(integrations_router)
app.include_router(integrations_marketplace_router)
app.include_router(slo_router)
app.include_router(support_bundle_router)
app.include_router(legal_router)
app.include_router(maintenance_router)
app.include_router(tenant_close_router)
app.include_router(tenant_sandbox_router)
app.include_router(sandbox_bootstrap_router)
app.include_router(backup_router)
app.include_router(print_router)
app.include_router(print_bridge_router)
app.include_router(push_router)
app.include_router(whatsapp_status_router)
app.include_router(checkout_router)
app.include_router(refunds_router)
app.include_router(feedback_router)
app.include_router(pilot_feedback_router)
app.include_router(pilot_telemetry_router)
app.include_router(media_router)
app.include_router(api_keys_router)
app.include_router(vapid_router)
app.include_router(postman_router)
app.include_router(admin_qrpack_router)
app.include_router(admin_qrposter_router)
app.include_router(admin_devices_router)

# Reports domain
app.include_router(daybook_pdf_router)
app.include_router(digest_router)
app.include_router(reports_router)
app.include_router(csp_router)
app.include_router(accounting_exports_router)
app.include_router(gst_monthly_router)
app.include_router(exports_router)
app.include_router(export_all_router)

if os.getenv("ADMIN_API_ENABLED", "").lower() in {"1", "true", "yes"}:
    app.include_router(superadmin_router)
