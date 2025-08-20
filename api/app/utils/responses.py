from typing import Any, Dict


def ok(data: Any) -> Dict[str, Any]:
    """Return a success envelope."""
    return {"ok": True, "data": data}


def err(code: int, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return an error envelope."""
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
