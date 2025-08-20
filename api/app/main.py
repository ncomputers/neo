# main.py
"""Minimal API endpoints for guest ordering and billing.

The API demonstrates a simple in-memory implementation of a dine-in ordering
flow used throughout the tests. It is intentionally lightweight and omits any
database integration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from .auth import (
    Token,
    User,
    authenticate_pin,
    authenticate_user,
    create_access_token,
    role_required,
)
from .menu import router as menu_router
from .models import TableStatus


app = FastAPI()
app.include_router(menu_router, prefix="/menu")


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------


class EmailLogin(BaseModel):
    """Payload for the email/password login endpoint."""

    username: str
    password: str


class PinLogin(BaseModel):
    """Payload for the PIN-based login endpoint."""

    username: str
    pin: str


@app.post("/login/email", response_model=Token)
async def email_login(credentials: EmailLogin) -> Token:
    """Authenticate via email/password and return a JWT."""

    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, role=user.role)


@app.post("/login/pin", response_model=Token)
async def pin_login(credentials: PinLogin) -> Token:
    """Authenticate using a numeric PIN and return a JWT."""

    user = authenticate_pin(credentials.username, credentials.pin)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, role=user.role)


@app.get(
    "/admin",
    dependencies=[Depends(role_required("super_admin", "outlet_admin", "manager"))],
)
async def admin_area(
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager"))
) -> dict[str, str]:
    """Endpoint restricted to admin roles."""

    return {"message": f"Welcome {user.username}"}


@app.get(
    "/staff", dependencies=[Depends(role_required("cashier", "kitchen", "cleaner"))]
)
async def staff_area(
    user: User = Depends(role_required("cashier", "kitchen", "cleaner"))
) -> dict[str, str]:
    """Endpoint restricted to staff roles."""

    return {"message": f"Hello {user.username}"}


# ---------------------------------------------------------------------------
# Table and Billing Operations
# ---------------------------------------------------------------------------


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


# Mutable in-memory table state: {table_id: {"cart": [...], "orders": [...]}}
tables: Dict[str, Dict[str, List[CartItem]]] = {}


class OrderRequest(BaseModel):
    """Minimal request body used when creating orders."""

    tenant_id: str
    open_tables: int


# In-memory tenant and payment registries used by billing endpoints
TENANTS: dict[str, dict] = {}
PAYMENTS: dict[str, dict] = {}


@app.post("/tenants")
async def create_tenant(name: str, licensed_tables: int) -> dict[str, str]:
    """Create a tenant record in the in-memory registry."""

    tenant_id = str(uuid.uuid4())
    TENANTS[tenant_id] = {
        "name": name,
        "licensed_tables": licensed_tables,
        "subscription_expires_at": datetime.utcnow(),
    }
    return {"tenant_id": tenant_id}


@app.post("/orders")
async def create_order(request: OrderRequest) -> dict[str, str]:
    """Validate tenant and table counts before accepting an order."""

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
async def renew_subscription(tenant_id: str, screenshot: UploadFile = File(...)) -> dict[str, str]:
    """Upload a payment proof and record it for later verification."""

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
async def verify_payment(tenant_id: str, payment_id: str, months: int = 1) -> dict[str, str]:
    """Mark a payment as verified and extend the tenant subscription."""

    payment = PAYMENTS.get(payment_id)
    if payment is None or payment["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment["verified"] = True
    tenant = TENANTS[tenant_id]
    tenant["subscription_expires_at"] = tenant["subscription_expires_at"] + timedelta(
        days=30 * months
    )
    return {"status": "verified"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple liveness probe endpoint."""

    return {"status": "ok"}


def _table_state(table_id: str) -> Dict[str, List[CartItem]]:
    """Return the mutable state dictionary for a table."""

    return tables.setdefault(table_id, {"cart": [], "orders": []})


@app.post("/tables/{table_id}/cart")
async def add_to_cart(table_id: str, item: CartItem) -> dict[str, List[CartItem]]:
    """Add an item to a table's cart.

    Multiple guests may add items concurrently by specifying a ``guest_id``.
    """

    table = _table_state(table_id)
    table["cart"].append(item)
    return {"cart": table["cart"]}


@app.post("/tables/{table_id}/order")
async def place_order(table_id: str) -> dict[str, List[CartItem]]:
    """Move all cart items to the order, locking them from guest edits."""

    table = _table_state(table_id)
    table["orders"].extend(table["cart"])
    table["cart"] = []
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
    order_item.quantity = 0  # Soft-cancel by zeroing out quantity
    return {"orders": table["orders"]}


@app.post("/tables/{table_id}/staff-order")
async def staff_place_order(
    table_id: str, item: StaffOrder
) -> dict[str, List[CartItem]]:
    """Staff directly place an order for a guest without a phone."""

    table = _table_state(table_id)
    table["orders"].append(CartItem(**item.model_dump()))
    return {"orders": table["orders"]}


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
    table["orders"] = []  # Clear order list after payment
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

    # Real logic would update the table status in the database.
    return {"table_id": table_id, "status": TableStatus.LOCKED.value}


@app.post("/tables/{table_id}/mark-clean")
async def mark_clean(table_id: str) -> dict[str, str]:
    """Mark a table as cleaned and ready for new guests."""

    # Real logic would update the table status in the database.
    return {"table_id": table_id, "status": TableStatus.AVAILABLE.value}
