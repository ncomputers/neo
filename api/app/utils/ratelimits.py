"""Central rate limit policies."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    """Rate limit configuration."""

    rate_per_min: float
    burst: int


def _policy(name: str, rate: float, burst: int) -> Policy:
    prefix = f"RL_{name.upper()}"
    rpm = float(os.getenv(f"{prefix}_RPM", rate))
    b = int(os.getenv(f"{prefix}_BURST", burst))
    return Policy(rate_per_min=rpm, burst=b)


def guest_order() -> Policy:
    """Limit guest orders."""
    return _policy("guest_order", 60, 100)


def magic_link_ip() -> Policy:
    """Throttle magic link attempts per IP."""
    return _policy("magic_link_ip", 2, 2)


def magic_link_email() -> Policy:
    """Throttle magic link emails."""
    return _policy("magic_link_email", 5 / 60, 5)


def qrpack() -> Policy:
    """Control QR pack generation."""
    return _policy("qrpack", 1, 1)


def exports() -> Policy:
    """Limit export generation."""
    return _policy("exports", 5 / 60, 5)


def two_factor_verify() -> Policy:
    """Throttle 2FA verification attempts."""
    return _policy("two_factor_verify", 5, 5)


__all__ = [
    "Policy",
    "guest_order",
    "magic_link_ip",
    "magic_link_email",
    "qrpack",
    "exports",
    "two_factor_verify",
]
