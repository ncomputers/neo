import os

# Default to SQLite for tests
os.environ.setdefault("POSTGRES_MASTER_URL", "sqlite:///./test_master.db")
os.environ.setdefault("POSTGRES_TENANT_URL", "sqlite:///./tenant_{tenant_id}.db")
