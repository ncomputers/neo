from fastapi import Header, HTTPException

"""Dependency helpers for tenant resolution."""


def get_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    """Return the tenant identifier from ``X-Tenant-ID`` header.

    Args:
        x_tenant_id: The value of the ``X-Tenant-ID`` HTTP header.

    Returns:
        The tenant identifier string.

    Raises:
        HTTPException: If the header is missing.
    """
    # minimal: require X-Tenant-ID; later we can add subdomain resolver
    if not x_tenant_id:
        raise HTTPException(400, "Missing X-Tenant-ID")
    return x_tenant_id
