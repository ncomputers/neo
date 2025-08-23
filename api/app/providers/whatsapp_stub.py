"""Stub WhatsApp provider used for development and tests."""

from typing import Any, Dict, Optional


def send(event: Any, payload: Dict[str, Any], target: Optional[str]) -> None:
    print(f"whatsapp to {target}: {payload}")
