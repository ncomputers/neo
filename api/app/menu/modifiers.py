"""Pydantic models and helpers for menu modifiers and combo items."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Modifier(BaseModel):
    """A single selectable modifier priced on the server."""

    id: int
    label: str
    price: int = Field(default=0, description="Price delta when selected")


class Combo(BaseModel):
    """Optional combo item that can be attached to a menu item."""

    id: int
    label: str
    price: int = Field(default=0, description="Combo price")


def total_price(
    mods: list[Modifier] | None = None, combos: list[Combo] | None = None
) -> int:
    """Return the total price impact of ``mods`` and ``combos`` selections."""

    total = 0
    for m in mods or []:
        total += m.price
    for c in combos or []:
        total += c.price
    return total
