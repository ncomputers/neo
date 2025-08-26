"""Utilities for menu domain features such as modifiers and dietary filters."""

from fastapi import APIRouter

from .modifiers import apply_modifiers
from .dietary import filter_items

# Placeholder router so ``api.app.main`` can include menu routes
router = APIRouter()

__all__ = ["apply_modifiers", "filter_items", "router"]
