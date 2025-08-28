import subprocess
import sys


def _upgrade(url: str) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "api/alembic.ini",
            "-x",
            f"db_url={url}",
            "upgrade",
            "head",
        ],
        check=True,
    )


def test_migrations_support_async_and_sync(tmp_path):
    async_db = tmp_path / "async.db"
    sync_db = tmp_path / "sync.db"
    _upgrade(f"sqlite+aiosqlite:///{async_db}")
    _upgrade(f"sqlite:///{sync_db}")
