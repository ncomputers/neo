"""Test configuration for API tests."""
import os

os.environ.setdefault("SECRET_KEY", "x" * 32)
