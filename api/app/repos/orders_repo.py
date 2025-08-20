"""Repository interface for order operations."""

from abc import ABC, abstractmethod


class OrdersRepo(ABC):
    """Contract for order persistence and manipulation."""

    @abstractmethod
    def create_order(self, table_code, items):
        """Create a new order for a table."""
        raise NotImplementedError

    @abstractmethod
    def list_active(self):
        """List all active orders."""
        raise NotImplementedError

    @abstractmethod
    def update_status(self, order_id, status):
        """Update the status of an order."""
        raise NotImplementedError

    @abstractmethod
    def add_round(self, order_id, items):
        """Add a new round of items to an existing order."""
        raise NotImplementedError
