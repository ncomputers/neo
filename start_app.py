# start_app.py
"""Run database migrations and launch the API server."""

from __future__ import annotations

import subprocess
import sys

from dotenv import load_dotenv
import uvicorn

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
        )
    except FileNotFoundError:
        print(
            "Install dependencies first: pip install -r api/requirements.txt"
        )
        return
    uvicorn.run("api.app.main:app")


if __name__ == "__main__":
    main()
