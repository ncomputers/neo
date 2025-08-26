from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from api.app import routes_privacy_dsar
from api.app.db import SessionLocal, engine
from api.app.models_tenant import AuditTenant


def test_privacy_dsar_export_and_delete():
    app = FastAPI()
    app.include_router(routes_privacy_dsar.router)
    client = TestClient(app)

    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS customers")
        conn.exec_driver_sql("DROP TABLE IF EXISTS invoices")
        conn.exec_driver_sql("DROP TABLE IF EXISTS payments")
        conn.exec_driver_sql(
            "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, allow_analytics BOOLEAN, allow_wa BOOLEAN, created_at DATETIME)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE invoices (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, created_at DATETIME)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE payments (id INTEGER PRIMARY KEY, invoice_id INTEGER, mode TEXT, amount NUMERIC, utr TEXT, verified BOOLEAN, created_at DATETIME)"
        )
        conn.exec_driver_sql(
            "INSERT INTO customers (id, name, phone, email, allow_analytics, allow_wa, created_at) VALUES (1,'Alice','111','a@example.com',0,0,'2023-01-01')"
        )
        conn.exec_driver_sql(
            "INSERT INTO invoices (id, name, phone, email, created_at) VALUES (1,'Alice','111','a@example.com','2023-01-02')"
        )
        conn.exec_driver_sql(
            "INSERT INTO payments (id, invoice_id, mode, amount, utr, verified, created_at) VALUES (1,1,'upi',10,'utr123',0,'2023-01-03')"
        )

    with SessionLocal() as s:
        s.query(AuditTenant).delete()
        s.commit()

    resp = client.post('/privacy/dsar/export', json={'phone': '111'})
    assert resp.status_code == 200
    data = resp.json()['data']
    assert data['customers'][0]['phone'] == '111'
    assert data['payments'][0]['utr'] is None

    with SessionLocal() as s:
        row = s.query(AuditTenant).filter_by(action='dsar_export').first()
        assert row is not None
        assert row.meta['payload']['phone'] == '***'

    resp = client.post('/privacy/dsar/delete', json={'phone': '111', 'dry_run': True})
    counts = resp.json()['data']
    assert counts['customers'] == 1
    assert counts['payments'] == 1

    resp = client.post('/privacy/dsar/delete', json={'phone': '111'})
    assert resp.status_code == 200

    with SessionLocal() as session:
        cust = session.execute(
            text('SELECT name, phone, email, allow_analytics, allow_wa FROM customers')
        ).first()
        inv = session.execute(
            text('SELECT name, phone, email FROM invoices')
        ).first()
        pay = session.execute(text('SELECT utr FROM payments')).first()
    assert cust == (None, None, None, 0, 0)
    assert inv == (None, None, None)
    assert pay == (None,)

    with SessionLocal() as s:
        row = s.query(AuditTenant).filter_by(action='dsar_delete').first()
        assert row is not None
        assert row.meta['payload']['phone'] == '***'
