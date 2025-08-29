from __future__ import annotations

import html
from typing import Any, Iterable

try:  # Optional dependency
    import bleach
except Exception:  # pragma: no cover - optional
    bleach = None  # type: ignore


def sanitize_html(value: str) -> str:
    """Clean HTML using ``bleach`` if available, else escape."""

    if bleach is None:
        return html.escape(value)
    return bleach.clean(value)


def sanitize_text(value: str) -> str:
    """Escape a plain text string for safe rendering."""

    return html.escape(value)


def redact(data: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    """Redact ``fields`` from ``data`` in-place and return the dict."""

    for field in fields:
        if field in data:
            data[field] = "[redacted]"
    return data
