"""Shared helpers for guest request guards."""

from __future__ import annotations


def _is_guest_post(path: str, method: str) -> bool:
    """Return True if the request is a guest POST to /g/*, /h/*, or /c/*."""
    return method == "POST" and (
        path.startswith("/g/") or path.startswith("/h/") or path.startswith("/c/")
    )
