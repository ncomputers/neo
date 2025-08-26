from __future__ import annotations

import hashlib
from typing import Dict

from config import get_settings

from .. import flags


def allocate(device_id: str, experiment: str, variants: Dict[str, int]) -> str:
    """Deterministically assign ``device_id`` to a variant.

    Parameters
    ----------
    device_id:
        Identifier for the device/user.
    experiment:
        Experiment name (included in the hash for stability across experiments).
    variants:
        Mapping of variant name to integer weight.
    """
    total = sum(variants.values())
    if total <= 0:
        return "control"
    key = f"{experiment}:{device_id}".encode()
    bucket = int(hashlib.md5(key).hexdigest(), 16) % total
    cumulative = 0
    for name, weight in variants.items():
        cumulative += weight
        if bucket < cumulative:
            return name
    return "control"


def get_variant(device_id: str, experiment: str, tenant: object | None = None) -> str:
    """Return variant for ``device_id`` under ``experiment``.

    Respects the ``ab_tests`` feature flag and falls back to ``control`` when
    disabled or when the experiment is undefined.
    """
    if not flags.get("ab_tests", tenant):
        return "control"
    settings = get_settings()
    experiments = getattr(settings, "ab_tests", {})
    variants = experiments.get(experiment)
    if not variants:
        return "control"
    return allocate(device_id, experiment, variants)
