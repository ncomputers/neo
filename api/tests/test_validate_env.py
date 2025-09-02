import os

from api.app.config.validate import validate_on_boot


def test_missing_envs(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "dev")
    try:
        validate_on_boot()
    except RuntimeError as exc:
        assert "DATABASE_URL" in str(exc)
        assert "REDIS_URL" in str(exc)
    else:
        raise AssertionError("Missing envs did not raise")


def test_dev_sqlite_flag(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DEV_SQLITE", "1")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "dev")
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    validate_on_boot()
    assert os.getenv("DATABASE_URL").startswith("sqlite")


def test_legacy_postgres_master(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_MASTER_URL", "postgresql://legacy")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "dev")
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    validate_on_boot()
    assert os.getenv("DATABASE_URL") == "postgresql://legacy"
