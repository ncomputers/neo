from __future__ import annotations

"""Stub WhatsApp provider that logs payloads."""

import json


def send(event, payload: dict, target):
    print(json.dumps(payload))
