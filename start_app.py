# start_app.py
"""Run database migrations and launch the API server."""

from __future__ import annotations

import subprocess

from dotenv import load_dotenv
import uvicorn

import config


def main() -> None:
    """Load settings, apply migrations, then start the API."""
    load_dotenv()  # load environment variables from a .env file
    config.get_settings()  # ensure settings are initialized
    subprocess.run(
        ["alembic", "-c", "api/alembic.ini", "upgrade", "head"],
        check=True,
    )
    uvicorn.run("api.app.main:app")


if __name__ == "__main__":
    main()
