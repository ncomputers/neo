"""Error reporting helpers."""

from __future__ import annotations

import logging
import os
from typing import Optional

try:  # pragma: no cover - optional dependency
    import sentry_sdk
except Exception:  # pragma: no cover - sentry not installed
    sentry_sdk = None  # type: ignore

logger = logging.getLogger("obs")


def init_sentry(dsn: Optional[str] = None, env: Optional[str] = None) -> None:
    """Initialize Sentry if a DSN is provided and SDK is available."""
    dsn = dsn or os.getenv("ERROR_DSN")
    if not dsn or sentry_sdk is None:
        if dsn and sentry_sdk is None:
            logger.warning("sentry-sdk not installed; skipping init")
        else:
            logger.info("ERROR_DSN not set; error sink disabled")
        return
    sentry_sdk.init(dsn=dsn, environment=env)


def capture_exception(exc: Exception) -> None:
    """Forward an exception to Sentry if configured, else log it."""
    if sentry_sdk and sentry_sdk.Hub.current.client is not None:
        sentry_sdk.capture_exception(exc)
    else:
        logger.exception("Unhandled exception", exc_info=exc)
