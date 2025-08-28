import importlib
import logging.config
import types

import alembic
import pytest
from sqlalchemy.exc import NoSuchModuleError

import config as app_config


@pytest.fixture
def env(monkeypatch):
    class DummyCM:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    fake_context = types.SimpleNamespace(
        config=types.SimpleNamespace(config_file_name=""),
        get_x_argument=lambda as_dictionary=True: {},
        is_offline_mode=lambda: True,
        configure=lambda **kwargs: None,
        begin_transaction=lambda: DummyCM(),
        run_migrations=lambda: None,
    )
    monkeypatch.setattr(alembic, "context", fake_context)
    monkeypatch.setattr(logging.config, "fileConfig", lambda *a, **k: None)
    fake_settings = types.SimpleNamespace(
        postgres_master_url="postgresql://",
        postgres_tenant_dsn_template="{tenant_id}",
    )
    monkeypatch.setattr(app_config, "get_settings", lambda: fake_settings)
    return importlib.reload(importlib.import_module("api.alembic.env"))


def test_is_async_url_detects_async(env):
    assert env._is_async_url("postgresql+asyncpg://localhost/test") is True


def test_is_async_url_detects_sync(env):
    assert env._is_async_url("postgresql://localhost/test") is False


def test_is_async_url_missing_driver(env, monkeypatch):
    url = "postgresql+asyncpg://localhost/test"
    fake_url = types.SimpleNamespace(
        drivername="postgresql+asyncpg",
        get_dialect=lambda: (_ for _ in ()).throw(NoSuchModuleError("asyncpg")),
    )
    monkeypatch.setattr(env, "make_url", lambda _: fake_url)
    with pytest.raises(RuntimeError, match="Async database driver not installed"):
        env._is_async_url(url)


def test_is_async_url_resolves_sync(env, monkeypatch):
    url = "postgresql+asyncpg://localhost/test"

    class FakeDialect:
        is_async = False

    fake_url = types.SimpleNamespace(
        drivername="postgresql+asyncpg", get_dialect=lambda: FakeDialect
    )
    monkeypatch.setattr(env, "make_url", lambda _: fake_url)
    with pytest.raises(
        RuntimeError, match="Async URL resolved to a synchronous dialect"
    ):
        env._is_async_url(url)
