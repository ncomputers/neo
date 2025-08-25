from typing import Any, Dict


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope."""
    return {"ok": True, "data": data}


def err(code: int, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return an error envelope."""
    from ..middlewares.logging import request_id_ctx

    return {
        "ok": False,
        "request_id": request_id_ctx.get(None),
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
