import json
import logging
import re
from datetime import datetime
from typing import Any

from ..middlewares.request_id import request_id_ctx

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.I)
PHONE_RE = re.compile(r"\b\d{10}\b")
UTR_RE = re.compile(r"(?i)(utr[:=]?\s*)(\d{10})")


def _redact_pii(text: str) -> str:
    """Replace emails, phone numbers, and UTR values with ***."""
    text = EMAIL_RE.sub("***", text)
    text = UTR_RE.sub(lambda m: m.group(1) + "***", text)
    text = PHONE_RE.sub("***", text)
    return text


class RequestIdFilter(logging.Filter):
    """Attach request id from context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        record.req_id = request_id_ctx.get(None)
        return True


class JsonFormatter(logging.Formatter):
    """Render logs as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        msg = _redact_pii(record.getMessage())
        data: dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "req_id": getattr(record, "req_id", None),
            "tenant": getattr(record, "tenant", None),
            "user": getattr(record, "user", None),
            "route": getattr(record, "route", None),
            "status": getattr(record, "status", None),
            "latency_ms": getattr(record, "latency_ms", None),
            "msg": msg,
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
