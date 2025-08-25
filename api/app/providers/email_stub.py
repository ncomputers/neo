"""Stub Email provider used for development and tests."""

from typing import Any, Dict, Optional


def send(event: Any, payload: Dict[str, Any], target: Optional[str]) -> None:
    subject = payload.get("subject", "")
    print(f"email to {target}: {subject}")
