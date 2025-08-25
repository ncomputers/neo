from __future__ import annotations

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import flags  # noqa: E402


def test_default_flag():
    assert flags.get("hotel_mode") is False


def test_env_override(monkeypatch):
    monkeypatch.setenv("FLAG_HOTEL_MODE", "1")
    assert flags.get("hotel_mode") is True


def test_tenant_override(monkeypatch):
    monkeypatch.delenv("FLAG_HOTEL_MODE", raising=False)

    class Tenant:
        enable_hotel = True

    assert flags.get("hotel_mode", Tenant()) is True


def test_tenant_overrides_env(monkeypatch):
    class Tenant:
        enable_hotel = False

    monkeypatch.setenv("FLAG_HOTEL_MODE", "1")
    assert flags.get("hotel_mode", Tenant()) is False
