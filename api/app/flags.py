from __future__ import annotations

"""Central registry for feature flags.

Flags support a three-level precedence order:

1. Environment variable override: ``FLAG_<NAME>``
2. Per-tenant override via model attributes or ``tenant.features`` mapping
3. Default defined in :data:`REGISTRY`
"""

import os
from typing import Any, Dict

# Metadata about supported feature flags.
# ``tenant_attr`` indicates the attribute on the Tenant model used for
# per-tenant overrides.
REGISTRY: Dict[str, Dict[str, Any]] = {
    "hotel_mode": {"default": False, "tenant_attr": "enable_hotel"},
    "counter_mode": {"default": False, "tenant_attr": "enable_counter"},
}


def _env_override(name: str) -> bool | None:
    """Return environment override for ``name`` if set."""
    val = os.getenv(f"FLAG_{name.upper()}")
    if val is None:
        return None
    return val.lower() in {"1", "true", "yes", "on"}


def get(name: str, tenant: Any | None = None) -> bool:
    """Fetch the value for a feature flag.

    Parameters
    ----------
    name:
        Name of the feature flag.
    tenant:
        Optional tenant instance for per-tenant overrides.
    """
    meta = REGISTRY.get(name, {})
    value = bool(meta.get("default", False))

    env_val = _env_override(name)
    if env_val is not None:
        value = env_val

    if tenant is not None:
        attr = meta.get("tenant_attr")
        if attr and hasattr(tenant, attr):
            value = bool(getattr(tenant, attr))
        features = getattr(tenant, "features", None)
        if isinstance(features, dict) and name in features:
            value = bool(features[name])

    return value


__all__ = ["get", "REGISTRY"]
