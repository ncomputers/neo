"""Repository interface for menu operations."""

from abc import ABC, abstractmethod


class MenuRepo(ABC):
    """Contract for menu-related persistence operations."""

    @abstractmethod
    def list_categories(self):
        """Return all menu categories."""
        raise NotImplementedError

    @abstractmethod
    def list_items(self):
        """Return menu items."""
        raise NotImplementedError

    @abstractmethod
    def toggle_out_of_stock(self, item_id, flag):
        """Toggle the stock availability of a menu item."""
        raise NotImplementedError

    @abstractmethod
    def menu_etag(self, session):
        """Return a hash representing the last menu update."""
        raise NotImplementedError
