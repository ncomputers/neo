from __future__ import annotations

import base64
import os

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")


def _jwk_from_secret(secret: str) -> dict[str, str]:
    """Return a minimal symmetric JWK for the given secret."""

    k = base64.urlsafe_b64encode(secret.encode()).rstrip(b"=").decode()
    return {"kty": "oct", "k": k, "kid": "1"}


@router.get("/jwks.json")
async def jwks() -> dict[str, list[dict[str, str]]]:
    """Expose a JSON Web Key Set for token verification."""

    return {"keys": [_jwk_from_secret(SECRET_KEY)]}
