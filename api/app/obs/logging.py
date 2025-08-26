import json
import logging
from datetime import datetime
from typing import Any

from ..middlewares.request_id import request_id_ctx


class RequestIdFilter(logging.Filter):
    """Attach request id from context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        record.req_id = request_id_ctx.get(None)
        return True


class JsonFormatter(logging.Formatter):
    """Render logs as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        data: dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "req_id": getattr(record, "req_id", None),
            "tenant": getattr(record, "tenant", None),
            "user": getattr(record, "user", None),
            "route": getattr(record, "route", None),
            "status": getattr(record, "status", None),
            "latency_ms": getattr(record, "latency_ms", None),
            "msg": record.getMessage(),
        }
        return json.dumps(data)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON formatting."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
