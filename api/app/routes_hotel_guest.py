from __future__ import annotations

"""Hotel guest-facing routes.

This module re-exports the existing guest-hotel router under a new name so it
can be mounted in the main application."""

from .routes_guest_hotel import router

__all__ = ["router"]
