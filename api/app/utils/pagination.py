from __future__ import annotations

"""Reusable helpers for cursor-based pagination."""

from dataclasses import dataclass
from typing import Optional

from fastapi import Query

# Hard cap to protect against overly large responses
MAX_LIMIT = 100


@dataclass
class Pagination:
    """Simple pagination container."""

    limit: int = MAX_LIMIT
    cursor: Optional[int] = None


def pagination(
    limit: int = Query(MAX_LIMIT, ge=1), cursor: Optional[int] = Query(None, ge=1)
) -> Pagination:
    """Return sanitised pagination parameters.

    ``limit`` is capped at :data:`MAX_LIMIT` and ``cursor`` is left as ``None``
    when not provided.
    """

    return Pagination(limit=min(limit, MAX_LIMIT), cursor=cursor)
