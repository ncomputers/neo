"""Startup environment validation utilities."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import yaml

REQUIRED_ENVS = [
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
    "ALLOWED_ORIGINS",
]

logger = logging.getLogger("api.config")

DEV_DEFAULTS = {
    "ALLOWED_ORIGINS": "http://localhost",
    "SECRET_KEY": "test-secret",
    "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/master",
    "REDIS_URL": "redis://localhost:6379/0",
}


def _load_flag_config() -> dict[str, bool]:
    """Read ``config/feature_flags.yaml`` into a mapping."""

    path = Path(__file__).resolve().parents[3] / "config" / "feature_flags.yaml"
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        logger.error("Invalid feature flag YAML: %s", exc)
        return {}
    data: dict[str, bool] = {}
    for key, val in raw.items():
        if isinstance(val, bool):
            data[key] = val
        elif isinstance(val, str):
            data[key] = val.strip().lower() in {"1", "true", "yes", "on"}
        else:
            data[key] = bool(val)
    return data


def _mask(value: str) -> str:
    """Return a masked representation of ``value`` for logging."""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def validate_on_boot() -> None:
    """Validate presence and basic format of required environment variables.

    Logs masked values for audit and raises :class:`RuntimeError` when any
    required variable is missing or malformed.
    """

    env = os.getenv("ENV", "dev")

    legacy = os.getenv("POSTGRES_MASTER_URL")
    if legacy and not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = legacy
        logger.warning("POSTGRES_MASTER_URL is deprecated; use DATABASE_URL instead")
    missing: list[str] = []
    for name in REQUIRED_ENVS:
        value = os.getenv(name)
        if not value and env != "prod" and name in DEV_DEFAULTS:
            value = DEV_DEFAULTS[name]
            os.environ.setdefault(name, value)
        if name == "DATABASE_URL" and not os.getenv("POSTGRES_MASTER_URL"):
            os.environ.setdefault("POSTGRES_MASTER_URL", value)
        if not value:
            missing.append(name)
            continue

        if env == "prod":
            if name.endswith("_URL"):
                parsed = urlparse(value)
                if not parsed.scheme or not parsed.netloc:
                    raise RuntimeError(f"{name} must be a valid URL")
            if name == "ALLOWED_ORIGINS":
                origins = [o.strip() for o in value.split(",") if o.strip()]
                if not origins:
                    raise RuntimeError("ALLOWED_ORIGINS must list at least one origin")
            if name == "SECRET_KEY" and len(value) < 32:
                raise RuntimeError("SECRET_KEY must be at least 32 characters long")

        logger.info("%s=%s", name, _mask(value))

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(sorted(missing))
        )

    if env == "prod":
        experimental = [
            "ab_tests",
            "wa_enabled",
            "happy_hour",
            "marketplace",
            "analytics",
        ]
        defaults = _load_flag_config()
        for name in experimental:
            if os.getenv(f"FLAG_{name.upper()}", "0").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }:
                raise RuntimeError(f"{name} feature flag must remain OFF in prod")
            if defaults.get(name):
                raise RuntimeError(f"{name} feature flag must remain OFF in prod")
