import importlib.util
import sys

import pytest
import responses

spec = importlib.util.spec_from_file_location(
    "emit_test_alert", "scripts/emit_test_alert.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_emit_alert_success(monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alert.local")
    monkeypatch.setattr(sys, "argv", ["emit_test_alert.py"])
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://alert.local", status=200)
        rsps.add(
            responses.POST, "http://alert.local/api/v1/alerts", json={}, status=200
        )
        module.main()


def test_emit_alert_unreachable(monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_URL", "http://alert.local")
    monkeypatch.setattr(sys, "argv", ["emit_test_alert.py"])
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://alert.local", status=500)
        with pytest.raises(SystemExit, match="unreachable"):
            module.main()
