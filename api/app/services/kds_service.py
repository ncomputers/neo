from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Protocol

from ..models_tenant import OrderStatus


class OrderRepo(Protocol):
    """Minimal interface required for order persistence."""

    def set_status(self, order_id: str, status: OrderStatus) -> None:
        """Persist a new status for an order."""


class HasStatus(Protocol):
    """Entity with a ``status`` attribute."""

    id: str
    status: str


class ItemRepo(Protocol):
    """Persistence interface for order items used by the KDS."""

    def get(self, item_id: str) -> HasStatus:
        """Fetch a single item."""

    def set_status(self, item_id: str, status: str) -> None:
        """Persist a new status for an item."""

    def list_queue(self) -> Iterable[HasStatus]:
        """Return all queue items in any order."""


def accept_order(order_id: str, repo: OrderRepo) -> None:
    """Mark an order as accepted by setting it to ``CONFIRMED``."""

    repo.set_status(order_id, OrderStatus.CONFIRMED)


def bump_item(
    item_id: str,
    next_status: str,
    repo: ItemRepo,
    can_transition: Callable[[str, str], bool],
) -> None:
    """Advance an item to ``next_status`` after validating the transition."""

    item = repo.get(item_id)
    if not can_transition(item.status, next_status):
        raise ValueError(f"cannot transition from {item.status!r} to {next_status!r}")
    repo.set_status(item_id, next_status)


def queue_view(repo: ItemRepo) -> Dict[str, List[HasStatus]]:
    """Return queue items grouped by status for the KDS UI."""

    grouped: Dict[str, List[HasStatus]] = defaultdict(list)
    for item in repo.list_queue():
        grouped[item.status].append(item)
    return dict(grouped)
