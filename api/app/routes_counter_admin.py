"""Admin-facing counter routes.

This module re-exports the admin router from ``routes_counter`` for direct
mounting in the application."""

from __future__ import annotations

from .routes_counter import router_admin as router

__all__ = ["router"]
