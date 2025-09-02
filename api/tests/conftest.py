"""Test configuration for API tests."""
import os

import api.app.db as app_db

os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")

app_db.SessionLocal, app_db.engine = app_db.create_test_session()
