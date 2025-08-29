"""Tests for NPS feedback API."""

from __future__ import annotations

import pathlib
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.auth import create_access_token  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.models_master import FeedbackNPS  # noqa: E402
from api.app.routes_support import router as support_router  # noqa: E402

app = FastAPI()
app.include_router(support_router)


def test_support_feedback() -> None:
    client = TestClient(app)
    token = create_access_token({"sub": "owner@example.com", "role": "owner"})
    resp = client.post(
        "/support/feedback",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "demo"},
        json={"score": 9, "comment": "Great", "feature_request": True},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "thanks"
    with SessionLocal() as session:
        rows = session.query(FeedbackNPS).all()
        assert len(rows) == 1
        assert rows[0].score == 9
        assert rows[0].feature_request is True
