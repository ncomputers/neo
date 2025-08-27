from __future__ import annotations

"""Helpers for building safe SQL clauses."""

from sqlalchemy import and_, column, literal

ALLOWED_FIELDS = {"id", "name", "phone", "email", "created_at"}


def build_where_clause(filters: dict[str, str]):
    """Return a SQLAlchemy boolean expression for a safe ``WHERE`` clause."""
    conditions = []
    for k, v in filters.items():
        if k not in ALLOWED_FIELDS:
            continue
        conditions.append(column(k) == v)
    return and_(*conditions) if conditions else literal(True)
