from fastapi.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


def rate_limited(retry_after: int) -> JSONResponse:
    """Return a standardized rate limit response."""
    hint = f"retry in {max(retry_after, 0)}s"
    body = {"code": "RATE_LIMIT", "hint": hint}
    return JSONResponse(body, status_code=HTTP_429_TOO_MANY_REQUESTS)


__all__ = ["rate_limited"]
