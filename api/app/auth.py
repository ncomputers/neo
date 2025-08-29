# auth.py

"""Simple in-memory authentication demo for FastAPI routes."""

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Global secrets purely for demonstration purposes
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
valid_refresh_tokens: set[str] = set()

ph = PasswordHasher()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    """JWT access token returned after authentication."""

    access_token: str
    token_type: str = "bearer"
    role: str | None = None


class TokenData(BaseModel):
    """Extracted token claims used for authorization."""

    username: Optional[str] = None
    role: Optional[str] = None


class User(BaseModel):
    """Application user with an associated role."""

    username: str
    role: str


class UserInDB(User):
    """Internal model storing password and optional PIN hashes."""

    password_hash: str
    pin_hash: Optional[str] = None


# In-memory user store; real apps should query a database
fake_users_db: dict[str, UserInDB] = {
    "admin@example.com": UserInDB(
        username="admin@example.com",
        role="super_admin",
        password_hash=ph.hash("adminpass"),
    ),
    "owner@example.com": UserInDB(
        username="owner@example.com",
        role="owner",
        password_hash=ph.hash("ownerpass"),
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
    """Check a plaintext password against a stored hash."""

    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except VerificationError as exc:  # pragma: no cover - unexpected
        logger.error("argon2 verification error: %s", exc)
        raise


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Return user if credentials match, else ``None``."""

    user = fake_users_db.get(username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def authenticate_pin(username: str, pin: str) -> Optional[UserInDB]:
    """Authenticate a user using a short numeric PIN."""

    user = fake_users_db.get(username)
    if not user or not user.pin_hash:
        return None
    if not verify_password(pin, user.pin_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT containing the provided claims."""

    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(sub: str) -> str:
    """Create a refresh token with rotation support."""

    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "jti": jti, "type": "refresh", "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    valid_refresh_tokens.add(jti)
    return token


def rotate_refresh_token(token: str) -> tuple[str, str]:
    """Validate ``token`` and issue new access and refresh tokens."""

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise ValueError("wrong type")
        jti = payload.get("jti")
        sub = payload.get("sub")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    if jti not in valid_refresh_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token reuse"
        )
    valid_refresh_tokens.remove(jti)
    access = create_access_token({"sub": sub, "role": fake_users_db[sub].role})
    refresh = create_refresh_token(sub)
    return access, refresh


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Resolve the user from a bearer token or raise ``HTTPException``."""

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
    except jwt.PyJWTError:  # pragma: no cover - library handles detailed errors
        raise credentials_exception
    user = fake_users_db.get(token_data.username)
    if user is None:
        raise credentials_exception
    return user


def role_required(*roles: str):
    """Dependency factory enforcing that the current user has one of ``roles``."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges"
            )
        return user

    return dependency
