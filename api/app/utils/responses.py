from typing import Any, Dict


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope."""
    return {"ok": True, "data": data}


def err(
    code: int | str,
    message: str,
    details: Dict[str, Any] | None = None,
    hint: str | None = None,
) -> Dict[str, Any]:
    """Return an error envelope."""
    from ..middlewares.request_id import request_id_ctx

    error: Dict[str, Any] = {"code": code, "message": message}
    if hint:
        error["hint"] = hint
    if details:
        error["details"] = details

    return {"ok": False, "request_id": request_id_ctx.get(None), "error": error}
