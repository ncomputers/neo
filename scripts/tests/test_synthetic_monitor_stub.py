import json
import os
import subprocess


def test_stub_run(tmp_path):
    env = {
        "DRY_RUN": "1",
        "SYN_TENANT_ID": "demo",
        "SYN_TABLE_CODE": "t1",
        "SYN_MENU_ITEM_IDS": "1,2,3",
        "API_BASE_URL": "http://localhost",
        "AUTH_TOKEN": "test-token",
    }
    env.update(os.environ)
    out = subprocess.run(
        ["python", "scripts/synthetic_order_monitor.py"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    metrics = json.loads(out.stdout.strip().splitlines()[-1])
    assert metrics["success"] is True
    assert metrics["step_failed"] is None
    assert metrics["http_status_map"]["refund_1"] == 200
    assert metrics["http_status_map"]["refund_2"] == 200


def test_stub_run_staging_vars(tmp_path):
    env = {
        "DRY_RUN": "1",
        "SYN_MENU_ITEM_IDS": "1,2,3",
        "API_BASE_URL_STAGING": "http://localhost",
        "SYN_TENANT_ID_STAGING": "demo",
        "SYN_TABLE_CODE_STAGING": "t1",
        "AUTH_TOKEN_STAGING": "test-token",
    }
    env.update(os.environ)
    out = subprocess.run(
        ["python", "scripts/synthetic_order_monitor.py"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    metrics = json.loads(out.stdout.strip().splitlines()[-1])
    assert metrics["success"] is True
    assert metrics["step_failed"] is None
    assert metrics["http_status_map"]["refund_1"] == 200
    assert metrics["http_status_map"]["refund_2"] == 200

