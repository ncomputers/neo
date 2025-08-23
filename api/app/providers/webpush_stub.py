from __future__ import annotations

"""Stub Web Push provider that logs delivery."""

import logging

logger = logging.getLogger("webpush")


def send(event, payload, target) -> None:
    """Log a web push delivery stub."""
    logger.info("web-push dispatched")
