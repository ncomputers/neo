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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
