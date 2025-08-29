import os
import pathlib
import sys

from fastapi.testclient import TestClient
import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault('POSTGRES_MASTER_URL', 'postgresql://localhost/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost/0')
os.environ.setdefault('SECRET_KEY', 'x' * 32)
os.environ.setdefault('ALLOWED_ORIGINS', '*')

from api.app.main import app
from api.app import audit
from api.app.auth import create_access_token

client = TestClient(app)


def setup_module() -> None:
    app.state.redis = fakeredis.aioredis.FakeRedis()
    audit.Base.metadata.drop_all(bind=audit.engine)
    audit.Base.metadata.create_all(bind=audit.engine)
    audit.log_event('staff', 'order', 'o1')
    audit.log_event('system', 'kds', 'k1')


def test_filters_and_csv() -> None:
    token = create_access_token({'sub': 'admin@example.com', 'role': 'super_admin'})
    headers = {'Authorization': f'Bearer {token}'}
    resp = client.get('/admin/audit?actor=staff&event=order', headers=headers)
    assert resp.status_code == 200
    data = resp.json()['data']
    assert len(data) == 1
    assert data[0]['actor'] == 'staff'

    csv_resp = client.get('/admin/audit?event=kds&format=csv', headers=headers)
    assert csv_resp.status_code == 200
    assert 'kds' in csv_resp.text
    assert csv_resp.headers['content-type'].startswith('text/csv')
