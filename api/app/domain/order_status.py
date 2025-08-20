"""Order status enumeration and allowed transitions."""

from __future__ import annotations

from enum import Enum


class OrderStatus(str, Enum):
    """Enumerate the lifecycle states for an order."""

    PLACED = "placed"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    HOLD = "hold"


TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PLACED: [
        OrderStatus.ACCEPTED,
        OrderStatus.REJECTED,
        OrderStatus.HOLD,
    ],
    OrderStatus.ACCEPTED: [
        OrderStatus.IN_PROGRESS,
        OrderStatus.READY,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.IN_PROGRESS: [OrderStatus.READY, OrderStatus.CANCELLED],
    OrderStatus.READY: [OrderStatus.SERVED, OrderStatus.CANCELLED],
    OrderStatus.SERVED: [],
    OrderStatus.CANCELLED: [],
    OrderStatus.REJECTED: [],
    OrderStatus.HOLD: [
        OrderStatus.ACCEPTED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    ],
}


def can_transition(src: OrderStatus, dst: OrderStatus) -> bool:
    """Return ``True`` if an order can move from ``src`` to ``dst``."""

    return dst in TRANSITIONS.get(src, [])
