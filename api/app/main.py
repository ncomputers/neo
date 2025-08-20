"""Minimal API endpoints for guest ordering and billing.

This module now provides a very small in-memory implementation of a dine-in
ordering flow.  It supports the following operations:

* Multiple guests can add items to a shared cart per table.
* Orders are placed per table and become read-only for guests afterwards.
* Admin users may "soft cancel" an order line by setting its quantity to ``0``.
* Staff are able to place orders on behalf of guests without phones.
* A running bill is maintained for each table and can be settled at any time.

The data model is intentionally simplistic and entirely in-memory to keep the
example self-contained.  It is **not** intended for production use.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from .auth import (
    Token,
    authenticate_pin,
    authenticate_user,
    create_access_token,
    role_required,
    User,
)


from .menu import router as menu_router


app = FastAPI()
app.include_router(menu_router, prefix="/menu")


class EmailLogin(BaseModel):
    username: str
    password: str


class PinLogin(BaseModel):
    username: str
    pin: str


@app.post("/login/email", response_model=Token)
async def email_login(credentials: EmailLogin) -> Token:
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, role=user.role)


@app.post("/login/pin", response_model=Token)
async def pin_login(credentials: PinLogin) -> Token:
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
):
    return {"message": f"Welcome {user.username}"}


@app.get(
    "/staff", dependencies=[Depends(role_required("cashier", "kitchen", "cleaner"))]
)
async def staff_area(
    user: User = Depends(role_required("cashier", "kitchen", "cleaner"))
):
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


tables: Dict[str, Dict[str, List[CartItem]]] = {}


@app.get("/health")
async def health() -> dict[str, str]:
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
    order_item.quantity = 0
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
    table["orders"] = []
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
