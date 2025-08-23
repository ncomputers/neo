"""Base interface for notification providers."""

from typing import Any, Dict, Optional


def send(event: Any, payload: Dict[str, Any], target: Optional[str]) -> None:
    """Deliver an outbound notification.

    Parameters:
        event: Notification event metadata.
        payload: Notification payload to deliver.
        target: Recipient identifier or address.
    """
    raise NotImplementedError
