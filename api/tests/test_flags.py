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


def test_env_overrides_tenant(monkeypatch):
    class Tenant:
        enable_hotel = True

    monkeypatch.setenv("FLAG_HOTEL_MODE", "0")
    assert flags.get("hotel_mode", Tenant()) is False


def test_remote_override(monkeypatch):
    monkeypatch.delenv("FLAG_HOTEL_MODE", raising=False)
    flags.set_override("hotel_mode", True)
    assert flags.get("hotel_mode") is True
    flags.set_override("hotel_mode", False)
    assert flags.get("hotel_mode") is False


def test_env_overrides_remote(monkeypatch):
    flags.set_override("hotel_mode", False)
    monkeypatch.setenv("FLAG_HOTEL_MODE", "1")
    assert flags.get("hotel_mode") is True
