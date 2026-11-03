"""运行指标：计数、耗时、事件，以及 /api/metrics 的形状。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import metrics  # noqa: E402


@pytest.fixture(autouse=True)
def clean():
    metrics.reset()
    yield
    metrics.reset()


def test_normalize_paths():
    assert metrics.normalize('/api/now') == '/api/now'
    assert metrics.normalize('/api/now/') == '/api/now'
    assert metrics.normalize('/') == '/'
    assert metrics.normalize('/index.html') == '/'
    assert metrics.normalize('/src/chat.js') == 'static'


def test_record_counts_and_latency():
    metrics.record('GET', '/api/now', 200, 12.0)
    metrics.record('GET', '/api/now', 200, 30.0)
    metrics.record('GET', '/api/now', 500, 400.0)
    s = metrics.snapshot()
    r = s['routes']['GET /api/now']
    assert r['count'] == 3
    assert r['avg_ms'] == pytest.approx(147.3, abs=0.2)
    assert r['max_ms'] == pytest.approx(400.0)
    assert s['status'] == {'GET /api/now 200': 2, 'GET /api/now 500': 1}
    assert r['p50_ms'] <= r['p95_ms']


def test_slow_requests_recorded():
    metrics.record('POST', '/api/chat', 200, 5000.0)
    s = metrics.snapshot()
    assert len(s['slow']) == 1
    assert s['slow'][0]['route'] == 'POST /api/chat'


def test_bump_events():
    metrics.bump('guard_hit')
    metrics.bump('guard_hit', 2)
    metrics.bump('degraded')
    s = metrics.snapshot()
    assert s['events']['guard_hit'] == 3
    assert s['events']['degraded'] == 1


def test_snapshot_shape():
    s = metrics.snapshot()
    for k in ('uptime_s', 'routes', 'status', 'events', 'slow'):
        assert k in s
    assert s['uptime_s'] >= 0


def test_api_metrics_endpoint(client):
    client.get('/api/now')
    client.get('/api/now')
    d = client.get('/api/metrics').json()
    assert set(d) >= {'uptime_s', 'routes', 'status', 'events', 'slow'}
    assert any('GET /api/now' in k for k in d['routes']), d['routes']
    assert d['routes']['GET /api/now']['count'] >= 2


def test_metrics_token_guard(client, monkeypatch):
    monkeypatch.setenv('XJI_METRICS_TOKEN', 'sekrit')
    assert client.get('/api/metrics').status_code == 403
    assert client.get('/api/metrics?token=wrong').status_code == 403
    ok = client.get('/api/metrics?token=sekrit')
    assert ok.status_code == 200 and 'routes' in ok.json()
