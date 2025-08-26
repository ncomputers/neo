"""Dietary and allergen helpers with filtering support."""

from __future__ import annotations

from typing import Dict, List, Set


def filter_items(items: List[dict], filter_str: str) -> List[dict]:
    """Return items matching ``filter_str``.

    ``filter_str`` is a comma-separated list where each term is of the form
    ``key:value``. Prefix the term with ``-`` to negate it. ``allergen`` is
    normalised to ``allergens``.
    """

    positives: Dict[str, Set[str]] = {}
    negatives: Dict[str, Set[str]] = {}
    for term in filter_str.split(","):
        term = term.strip()
        if not term:
            continue
        negate = term.startswith("-")
        if negate:
            term = term[1:]
        if ":" not in term:
            continue
        key, value = term.split(":", 1)
        key = key.lower()
        value = value.lower()
        if key == "allergen":
            key = "allergens"
        target = negatives if negate else positives
        target.setdefault(key, set()).add(value)

    def matches(item: dict) -> bool:
        for key, vals in positives.items():
            field_vals = [v.lower() for v in item.get(key, [])]
            if not all(v in field_vals for v in vals):
                return False
        for key, vals in negatives.items():
            field_vals = [v.lower() for v in item.get(key, [])]
            if any(v in field_vals for v in vals):
                return False
        return True

    return [item for item in items if matches(item)]
