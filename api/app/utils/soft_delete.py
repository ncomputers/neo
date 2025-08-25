from datetime import datetime
from typing import Optional
from fastapi import HTTPException


def filter_active(query):
    """Apply deleted_at IS NULL filter to SQLAlchemy query objects."""
    return query.filter_by(deleted_at=None)


def guard_not_deleted(resource, msg: str, code: str = "GONE_RESOURCE") -> None:
    """Ensure ``resource`` is not soft-deleted, else raise 403."""
    if resource and getattr(resource, "deleted_at", None) is not None:
        raise HTTPException(status_code=403, detail={"code": code, "message": msg})


def soft_delete(model_obj, now: Optional[datetime] = None) -> None:
    """Mark ``model_obj`` as deleted by setting ``deleted_at``."""
    model_obj.deleted_at = now or datetime.utcnow()


def restore(model_obj) -> None:
    """Clear the ``deleted_at`` flag for ``model_obj``."""
    model_obj.deleted_at = None
