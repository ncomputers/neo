from __future__ import annotations

"""Helpers for signing and verifying webhook requests."""

import hashlib
import hmac
import time


def sign(secret: str, timestamp: int, body: bytes) -> str:
    """Return the signature header for a webhook payload.

    Parameters
    ----------
    secret:
        Shared secret used to compute the HMAC digest.
    timestamp:
        UNIX timestamp in seconds.
    body:
        Raw request body in bytes.
    """
    msg = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify(
    secret: str,
    ts: int,
    body: bytes,
    header_sig: str,
    max_skew: int = 300,
) -> bool:
    """Validate a webhook request signature.

    Returns ``True`` if ``header_sig`` matches the expected signature for the
    provided ``secret`` and ``body`` and ``ts`` is within ``max_skew`` seconds of
    the current time.
    """
    if abs(time.time() - ts) > max_skew:
        return False
    expected = sign(secret, ts, body)
    return hmac.compare_digest(expected, header_sig)
