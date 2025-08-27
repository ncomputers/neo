import json
from ops.scripts import status_page


def test_status_page_toggle(tmp_path, monkeypatch):
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps({"state": "ok", "message": None, "components": [], "incidents": []}))
    monkeypatch.setattr(status_page, "STATUS_FILE", status_file)
    monkeypatch.setattr(status_page, "_post_status", lambda data: None)

    status_page.start_incident("db", "down")
    status_page.start_incident("api", "slow")
    data = json.loads(status_file.read_text())
    assert data["state"] == "degraded"
    assert len(data["incidents"]) == 2

    status_page.resolve_incident("db")
    data = json.loads(status_file.read_text())
    assert data["state"] == "degraded"
    assert len(data["incidents"]) == 1

    status_page.resolve_incident("api")
    data = json.loads(status_file.read_text())
    assert data["state"] == "ok"
    assert data["incidents"] == []
