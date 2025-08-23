from __future__ import annotations

"""Base interface for notification providers."""

from typing import Optional


def send(event: Optional[str], payload: dict, target: Optional[str]) -> None:
    """Send ``payload`` for ``event`` to ``target``.

    Provider modules should implement this function.
    """
    raise NotImplementedError
