"""Test configuration for API tests."""
import os

import api.app.db as app_db

# Provide default settings so tests can run without requiring a full
# environment configuration.
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
# Use an in-memory SQLite database when explicit connection URLs are not
# supplied. This mirrors the behaviour in top-level tests and prevents
# import-time failures when DATABASE_URL or POSTGRES_MASTER_URL are missing.
os.environ.setdefault("POSTGRES_MASTER_URL", "sqlite+aiosqlite:///:memory:")

app_db.SessionLocal, app_db.engine = app_db.create_test_session()
