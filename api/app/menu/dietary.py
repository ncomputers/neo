"""Shared dietary and allergen fields for menu schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DietaryInfo(BaseModel):
    """Mixin providing dietary tags and allergen information."""

    dietary: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
