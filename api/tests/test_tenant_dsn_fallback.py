import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.db.tenant import build_dsn


def test_build_dsn_uses_sync_url_when_template_missing(monkeypatch):
    monkeypatch.delenv("POSTGRES_TENANT_DSN_TEMPLATE", raising=False)
    monkeypatch.setenv("SYNC_DATABASE_URL", "postgresql+asyncpg://u:p@host:5432/main")
    assert (
        build_dsn("demo")
        == "postgresql+asyncpg://u:p@host:5432/main_demo"
    )
