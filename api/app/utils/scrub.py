from __future__ import annotations

"""Helpers for scrubbing sensitive fields from payloads."""

from typing import Any

SENSITIVE_KEYS = {"token", "secret", "password", "key", "signature", "auth"}


def scrub_payload(data: Any) -> Any:
    """Recursively scrub secret-ish keys from ``data``.

    Values for keys containing substrings in :data:`SENSITIVE_KEYS` are replaced
    with ``"***"``. Other mapping and sequence values are processed
    recursively.
    """

    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                result[k] = "***"
            else:
                result[k] = scrub_payload(v)
        return result
    if isinstance(data, list):
        return [scrub_payload(i) for i in data]
    return data
