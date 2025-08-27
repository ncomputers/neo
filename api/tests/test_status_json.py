import asyncio
import json
import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.auth import create_access_token
from api.app.main import app
from api.app.routes_status_json import STATUS_KEY
import api.app.routes_status_json as routes_status_json


def test_get_status_json(tmp_path, monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    status_file = tmp_path / 'status.json'
    status_file.write_text(json.dumps({'state': 'ok', 'message': '', 'components': []}))
    monkeypatch.setattr(routes_status_json, 'STATUS_FILE', status_file)
    client = TestClient(app)
    resp = client.get('/status.json')
    assert resp.status_code == 200
    data = resp.json()
    assert {'state', 'message', 'components'} <= data.keys()


def test_post_status_updates_redis_and_file(tmp_path, monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    status_file = tmp_path / 'status.json'
    monkeypatch.setattr(routes_status_json, 'STATUS_FILE', status_file)
    client = TestClient(app)
    token = create_access_token({'sub': 'admin@example.com', 'role': 'super_admin'})
    payload = {'state': 'degraded', 'message': 'db down', 'components': ['db']}
    resp = client.post('/admin/status', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    stored = json.loads(asyncio.run(app.state.redis.get(STATUS_KEY)))
    assert stored == payload
    assert json.loads(status_file.read_text()) == payload
