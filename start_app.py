# start_app.py
"""Run database migrations and launch the API server."""

from __future__ import annotations

import subprocess
import sys

import uvicorn
from dotenv import load_dotenv

import config


def main() -> None:
    """Load settings, apply migrations, then start the API."""
    load_dotenv()  # load environment variables from a .env file
    config.get_settings()  # ensure settings are initialized
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
    uvicorn.run("api.app.main:app")


if __name__ == "__main__":
    main()
