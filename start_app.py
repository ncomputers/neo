# start_app.py
"""Run database migrations and launch the API server."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import uvicorn
from dotenv import load_dotenv

import config


def main(argv: list[str] | None = None) -> None:
    """Load settings, optionally apply migrations, then start the API."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-db-migrations",
        action="store_true",
        help="Start without running Alembic migrations",
    )
    args = parser.parse_args(argv)

    load_dotenv()  # load environment variables from a .env file

    env_flag = os.getenv("SKIP_DB_MIGRATIONS")
    skip = args.skip_db_migrations or (
        env_flag and env_flag.lower() not in {"0", "false"}
    )
    if skip:
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

    if not skip:
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    "api/alembic.ini",
                    "upgrade",
                    "head",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            conn_errors = (
                "Name or service not known",
                "could not translate host name",
                "Connection refused",
            )
            if any(err in exc.stderr for err in conn_errors):
                if exc.stdout:
                    sys.stdout.write(exc.stdout)
                if exc.stderr:
                    sys.stderr.write(exc.stderr)
                print(
                    "database unavailable; starting without migrations using SQLite",
                    file=sys.stderr,
                )
                os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
            else:
                if exc.stdout:
                    sys.stdout.write(exc.stdout)
                if exc.stderr:
                    sys.stderr.write(exc.stderr)
                print(
                    f"database migration failed (exit code {exc.returncode})",
                    file=sys.stderr,
                )
                raise SystemExit(exc.returncode)
        except FileNotFoundError:
            print("Install dependencies first: pip install -r requirements.txt")
            return

    config.get_settings()  # ensure settings are initialized with any override

    try:
        uvicorn.run(
            "api.app.main:app",
            host="0.0.0.0",  # nosec B104: bind for local development
            port=int(os.getenv("PORT", "8000")),
            log_level="info",
        )
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        print(
            f"Missing dependency: {missing}. Install it with 'pip install {missing}'",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
