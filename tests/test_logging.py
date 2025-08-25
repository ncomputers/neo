import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.app.main import app


def test_log_line_has_request_id(caplog):
    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="api"):
        client.get("/health")
    line = caplog.messages[0]
    data = json.loads(line)
    assert data["request_id"]
