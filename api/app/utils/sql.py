from __future__ import annotations

"""Helpers for building safe SQL clauses."""

ALLOWED_FIELDS = {"id", "name", "phone", "email", "created_at"}

def build_where_clause(filters: dict[str, str]) -> tuple[str, dict]:
    """Return a safe ``WHERE`` clause and parameter mapping."""
    parts: list[str] = []
    params: dict[str, str] = {}
    for i, (k, v) in enumerate(filters.items()):
        if k not in ALLOWED_FIELDS:
            continue
        param = f"p{i}"
        parts.append(f"{k} = :{param}")
        params[param] = v
    return (" AND ".join(parts) or "1=1", params)
