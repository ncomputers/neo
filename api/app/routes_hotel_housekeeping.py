from __future__ import annotations

"""Hotel housekeeping routes.

This shim exposes the generic housekeeping router under a hotel-specific
module name."""

from .routes_housekeeping import router

__all__ = ["router"]
