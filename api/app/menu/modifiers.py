"""Helper functions for server-priced modifiers and optional combos."""

from __future__ import annotations

from typing import Iterable, List, Tuple


def apply_modifiers(
    base_price: float,
    chosen_ids: Iterable[int],
    available: List[dict] | None,
    combos: List[dict] | None = None,
) -> Tuple[float, List[dict]]:
    """Return the price with applied modifiers and the chosen modifier objects.

    Parameters
    ----------
    base_price:
        Original price of the menu item.
    chosen_ids:
        Iterable of modifier identifiers selected by the client.
    available:
        List of modifier definitions from the menu item. Each modifier should
        be a mapping containing ``id`` and ``delta`` keys.
    combos:
        Optional combos defined on the item. Present for future extension; not
        used by current tests but included for completeness.
    """

    chosen: List[dict] = []
    extra = 0.0
    for mid in chosen_ids:
        for mod in available or []:
            if mod.get("id") == mid:
                chosen.append(mod)
                extra += float(mod.get("delta", 0))
                break
    # Combos are intentionally ignored for now; server-priced combos would be
    # applied here when implemented.
    return base_price + extra, chosen
