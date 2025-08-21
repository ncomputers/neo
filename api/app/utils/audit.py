from __future__ import annotations

"""Simple audit logging decorator."""

from functools import wraps
import inspect
import typing
from typing import Any, Callable

from fastapi import Request

from api.app.db import SessionLocal
from api.app.models_tenant import AuditTenant


def audit(action: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate a route handler to persist an audit entry on success.

    When the wrapped handler returns a response produced by
    ``utils.responses.ok`` an ``AuditTenant`` row is inserted capturing the
    actor, request path and JSON payload. The decorator ensures a
    :class:`~fastapi.Request` object is available to record these details.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(func)
        hints = typing.get_type_hints(func)
        params: list[inspect.Parameter] = []
        if "request" not in sig.parameters:
            params.append(
                inspect.Parameter(
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Request,
                )
            )
        for p in sig.parameters.values():
            ann = hints.get(p.name, p.annotation)
            params.append(p.replace(annotation=ann))
        new_sig = sig.replace(parameters=params)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            bound = new_sig.bind_partial(*args, **kwargs)
            request: Request = bound.arguments["request"]
            try:
                payload = await request.json()
            except Exception:  # pragma: no cover - non JSON or no body
                payload = None
            bound.apply_defaults()
            call_kwargs = {
                k: v for k, v in bound.arguments.items() if k in sig.parameters
            }
            result = await func(**call_kwargs)
            if isinstance(result, dict) and result.get("ok") is True:
                actor = getattr(bound.arguments.get("user"), "username", "guest")
                meta = {"path": request.url.path, "payload": payload}
                with SessionLocal() as session:
                    session.add(
                        AuditTenant(actor=actor, action=action, meta=meta)
                    )
                    session.commit()
            return result

        wrapper.__signature__ = new_sig
        return wrapper

    return decorator
