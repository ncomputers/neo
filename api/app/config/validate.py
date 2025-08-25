"""Startup environment validation utilities."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

REQUIRED_ENVS = [
    "DB_URL",
    "REDIS_URL",
    "SECRET_KEY",
    "ALLOWED_ORIGINS",
]

logger = logging.getLogger("api.config")


def _mask(value: str) -> str:
    """Return a masked representation of ``value`` for logging."""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def validate_on_boot() -> None:
    """Validate presence and basic format of required environment variables.

    Logs masked values for audit and raises :class:`RuntimeError` when any
    required variable is missing or malformed.
    """

    missing: list[str] = []
    for name in REQUIRED_ENVS:
        value = os.getenv(name)
        if not value:
            missing.append(name)
            continue

        if name.endswith("_URL"):
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                raise RuntimeError(f"{name} must be a valid URL")
        if name == "ALLOWED_ORIGINS":
            origins = [o.strip() for o in value.split(",") if o.strip()]
            if not origins:
                raise RuntimeError("ALLOWED_ORIGINS must list at least one origin")
        if name == "SECRET_KEY" and len(value) < 32:
            raise RuntimeError("SECRET_KEY must be at least 32 characters long")

        logger.info("%s=%s", name, _mask(value))

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(sorted(missing))
        )
