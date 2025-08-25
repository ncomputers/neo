"""Stub Slack provider that posts messages to a webhook."""

import os
from typing import Any, Dict, Optional

import requests


def send(event: Any, payload: Dict[str, Any], target: Optional[str]) -> None:
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        raise RuntimeError("SLACK_WEBHOOK_URL not configured")
    text = payload.get("text") or payload.get("message") or ""
    requests.post(url, json={"text": text}, timeout=5).raise_for_status()
