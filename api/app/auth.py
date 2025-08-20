# auth.py
"""In-memory authentication helpers used by the demo application.

The module defines a tiny user database and utilities for password and PIN
authentication. It issues JSON Web Tokens (JWTs) for authenticated users and
includes helpers for role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from argon2 import PasswordHasher

SECRET_KEY = "supersecret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

ph = PasswordHasher()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    """Schema returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    role: str | None = None


class TokenData(BaseModel):
    """Data extracted from a decoded JWT token."""

    username: Optional[str] = None
    role: Optional[str] = None


class User(BaseModel):
    """Public user model exposed by API dependencies."""

    username: str
    role: str


class UserInDB(User):
    """User record stored in the in-memory database."""

    password_hash: str
    pin_hash: Optional[str] = None


# In-memory users for demo purposes
# Passwords and PINs are pre-hashed using Argon2 for simplicity.
fake_users_db: dict[str, UserInDB] = {
    "admin@example.com": UserInDB(
        username="admin@example.com",
        role="super_admin",
        password_hash=ph.hash("adminpass"),
    ),
    "cashier1": UserInDB(
        username="cashier1",
        role="cashier",
        password_hash=ph.hash("cashierpass"),
        pin_hash=ph.hash("1234"),
    ),
    "kitchen1": UserInDB(
        username="kitchen1",
        role="kitchen",
        password_hash=ph.hash("kitchenpass"),
        pin_hash=ph.hash("5678"),
    ),
    "cleaner1": UserInDB(
        username="cleaner1",
        role="cleaner",
        password_hash=ph.hash("cleanpass"),
        pin_hash=ph.hash("4321"),
    ),
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if the plain password matches the stored hash."""

    try:
        return ph.verify(hashed_password, plain_password)
    except Exception:
        return False


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Validate username/password and return the user if correct."""

    user = fake_users_db.get(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def authenticate_pin(username: str, pin: str) -> Optional[UserInDB]:
    """Validate username/PIN and return the user if correct."""

    user = fake_users_db.get(username)
    if not user or not user.pin_hash:
        return None
    if not verify_password(pin, user.pin_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT containing ``data`` and an expiration."""

    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Decode the JWT token and return the associated user."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    user = fake_users_db.get(token_data.username)
    if user is None:
        raise credentials_exception
    return user


def role_required(*roles: str):
    """Dependency factory enforcing that the user has one of ``roles``."""

    def dependency(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges"
            )
        return user

    return dependency
