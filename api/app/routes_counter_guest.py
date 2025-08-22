"""Guest-facing counter routes.

This module re-exports the guest router from ``routes_counter`` so it can be
mounted independently in the application."""

from __future__ import annotations

from .routes_counter import router

__all__ = ["router"]
