"""Lightweight JWT authentication for outlet staff."""

from datetime import timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .auth import ALGORITHM, SECRET_KEY, create_access_token

security = HTTPBearer()
TOKEN_EXPIRE_MINUTES = 5


class StaffToken(BaseModel):
    """JWT returned to authenticated staff."""

    access_token: str
    token_type: str = "bearer"
    role: str
    staff_id: int


class StaffTokenData(BaseModel):
    """Claims extracted from a staff JWT."""

    staff_id: int
    role: str


def create_staff_token(staff_id: int, role: str) -> str:
    """Return a short-lived JWT for ``staff_id`` and ``role``."""

    data = {"staff_id": staff_id, "role": role}
    return create_access_token(data, expires_delta=timedelta(minutes=TOKEN_EXPIRE_MINUTES))


async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> StaffTokenData:
    """Resolve and return staff claims from ``Authorization`` header."""

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc
    staff_id = payload.get("staff_id")
    role = payload.get("role")
    if staff_id is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return StaffTokenData(staff_id=staff_id, role=role)


def role_required(*roles: str):
    """Dependency enforcing that the current staff has one of ``roles``."""

    def dependency(staff: StaffTokenData = Depends(get_current_staff)) -> StaffTokenData:
        if staff.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges",
            )
        return staff

    return dependency


__all__ = [
    "StaffToken",
    "StaffTokenData",
    "create_staff_token",
    "get_current_staff",
    "role_required",
]
