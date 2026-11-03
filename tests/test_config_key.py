"""网页上配 key：读配置、存 key、清除、掩码不出全文。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server.app as app_module  # noqa: E402

KEY = 'sk-1234567890abcdef1234567890abcdef'


@pytest.fixture(autouse=True)
def clean_runtime_key():
    app_module._runtime_key = ''
    yield
    app_module._runtime_key = ''


def test_config_when_empty(client):
    d = client.get('/api/config').json()
    assert d['key_present'] is False
    assert d['key_source'] == 'none'
    assert d['key_mask'] == ''
    assert '只存在内存' in d['note']


def test_set_key_masks_but_never_echoes(client):
    r = client.post('/api/config/key', json={'key': KEY})
    assert r.status_code == 200
    body = r.json()
    assert body['key_present'] is True and body['key_source'] == 'ui'
    assert body['key_mask'] == 'sk-1…cdef'
    assert KEY not in r.text           # 响应里不许出现全文

    d = client.get('/api/config').json()
    assert d['key_source'] == 'ui'
    assert KEY not in str(d)

    h = client.get('/api/health').json()
    assert h['mock'] is False


def test_clear_key(client, monkeypatch):
    monkeypatch.setattr(app_module, 'API_KEY', '')
    client.post('/api/config/key', json={'key': KEY})
    assert client.get('/api/health').json()['mock'] is False
    r = client.delete('/api/config/key')
    assert r.status_code == 200
    assert client.get('/api/config').json()['key_present'] is False


def test_env_key_is_reported_as_env(client, monkeypatch):
    monkeypatch.setattr(app_module, 'API_KEY', 'sk-envkey1234567890abcdefgh')
    d = client.get('/api/config').json()
    assert d['key_source'] == 'env'
    assert d['key_present'] is True


def test_ui_key_overrides_env(client, monkeypatch):
    monkeypatch.setattr(app_module, 'API_KEY', 'sk-envkey1234567890abcdefgh')
    client.post('/api/config/key', json={'key': KEY})
    assert client.get('/api/config').json()['key_source'] == 'ui'
    client.delete('/api/config/key')
    assert client.get('/api/config').json()['key_source'] == 'env'


def test_rejects_junk(client):
    assert client.post('/api/config/key', json={'key': 'short'}).status_code == 400
    assert client.post('/api/config/key', json={'key': 'sk-1234 5678 90abcdef1234'}).status_code == 400


def test_test_endpoint_requires_key(client):
    assert client.post('/api/config/key/test').status_code == 400
