"""Repository interface for invoice operations."""

from abc import ABC, abstractmethod


class InvoicesRepo(ABC):
    """Contract for invoice generation and retrieval."""

    @abstractmethod
    def generate_invoice(self, session_id):
        """Generate an invoice for a dining session."""
        raise NotImplementedError

    @abstractmethod
    def get_invoice(self, number):
        """Retrieve an invoice by its number."""
        raise NotImplementedError

    @abstractmethod
    def add_payment(self, invoice_number, amount):
        """Record a payment against an invoice."""
        raise NotImplementedError
