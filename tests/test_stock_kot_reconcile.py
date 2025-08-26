import csv
import logging
from scripts.stock_kot_reconcile import load_anomalies, send_email


def write_csv(path, rows):
    fieldnames = ["item", "sold_qty", "KOT_cnt", "variance"]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_anomalies_valid(tmp_path):
    path = tmp_path / "report.csv"
    write_csv(
        path,
        [
            {"item": "burger", "sold_qty": "10", "KOT_cnt": "8", "variance": "2"},
            {"item": "pizza", "sold_qty": "5", "KOT_cnt": "2", "variance": "4"},
        ],
    )
    anomalies = load_anomalies(str(path), 3)
    assert anomalies == [
        {"item": "pizza", "sold_qty": "5", "KOT_cnt": "2", "variance": "4"}
    ]


def test_load_anomalies_invalid_rows(tmp_path, caplog):
    path = tmp_path / "bad.csv"
    write_csv(
        path,
        [
            {"item": "a", "sold_qty": "foo", "KOT_cnt": "1", "variance": "2"},
            {"item": "", "sold_qty": "1", "KOT_cnt": "1", "variance": "1"},
            {"sold_qty": "1", "KOT_cnt": "1", "variance": "1"},
            {"item": "b", "sold_qty": "1", "KOT_cnt": "1", "variance": "x"},
        ],
    )
    caplog.set_level(logging.WARNING)
    anomalies = load_anomalies(str(path), 0)
    assert anomalies == []
    assert "missing fields" in caplog.text
    assert "non-numeric" in caplog.text


def test_send_email_uses_smtp_from(monkeypatch):
    sent = {}

    class DummySMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def send_message(self, msg):
            sent["msg"] = msg

    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("OPS_EMAIL", "ops@example.com")
    monkeypatch.setenv("SMTP_FROM", "alerts@example.com")
    monkeypatch.setenv("SMTP_PORT", "25")
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)

    anomalies = [{"item": "i", "sold_qty": "1", "KOT_cnt": "1", "variance": "2"}]
    send_email(anomalies, 1)
    assert sent["msg"]["From"] == "alerts@example.com"
