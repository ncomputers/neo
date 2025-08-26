"""User-Agent denylist helpers."""

from __future__ import annotations

UA_DENYLIST = {"curl", "wget"}


def is_denied(ua: str | None) -> bool:
    """Return ``True`` if ``ua`` matches a denylisted identifier."""
    if not ua:
        return False
    ua = ua.lower()
    return any(bad in ua for bad in UA_DENYLIST)
