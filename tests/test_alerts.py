"""告警规则：把指标翻成「要不要管」。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import alerts  # noqa: E402


def snap(status=None, routes=None, events=None, slow=None, breaker=None, cost=None):
    return {'status': status or {}, 'routes': routes or {}, 'events': events or {},
            'slow': slow or [], 'breaker': breaker or {'state': 'closed'},
            'cost': cost or {}}


def test_over_budget_warns():
    d = alerts.evaluate(snap(status={'POST /api/chat 200': 5},
                             cost={'over_budget': True, 'estimated_cny': 3.2, 'daily_budget_cny': 2}))
    hit = [a for a in d['alerts'] if a['code'] == 'over_budget']
    assert hit and '3.2' in hit[0]['detail']


def test_missing_usage_is_info():
    d = alerts.evaluate(snap(status={'POST /api/chat 200': 5}, cost={'requests_without_usage': 2}))
    hit = [a for a in d['alerts'] if a['code'] == 'no_usage']
    assert hit and hit[0]['level'] == 'info'


def codes(d):
    return [a['code'] for a in d['alerts']]


def test_no_traffic():
    d = alerts.evaluate(snap())
    assert d['ok'] is True
    assert codes(d) == ['no_traffic']


def test_healthy():
    d = alerts.evaluate(snap(status={'GET /api/now 200': 100}))
    assert d['ok'] is True
    assert d['alerts'] == []
    assert d['error_rate'] == 0


def test_error_rate_needs_samples():
    # 样本太少：2 次里 1 次 500，不报 error
    d = alerts.evaluate(snap(status={'GET /x 200': 1, 'GET /x 500': 1}))
    assert 'error_rate' not in codes(d)
    # 样本够了才报
    d = alerts.evaluate(snap(status={'GET /x 200': 18, 'GET /x 500': 2}))
    assert 'error_rate' in codes(d)
    assert d['ok'] is False


def test_slow_route():
    routes = {'GET /api/chat': {'count': 10, 'p95_ms': 3200}}
    d = alerts.evaluate(snap(status={'GET /api/chat 200': 10}, routes=routes))
    assert 'slow_route' in codes(d)
    assert d['ok'] is True  # warn 不算 error


def test_slow_route_needs_calls():
    routes = {'GET /api/chat': {'count': 2, 'p95_ms': 9000}}
    assert 'slow_route' not in codes(alerts.evaluate(snap(status={'GET /api/chat 200': 2}, routes=routes)))


def test_degraded_and_guard():
    d = alerts.evaluate(snap(status={'POST /api/chat 200': 30}, events={'degraded': 2, 'guard_hit': 3}))
    assert 'degraded' in codes(d) and 'guard_hit' in codes(d)


def test_rate_limit_spike():
    d = alerts.evaluate(snap(status={'POST /api/chat 429': 30}, events={'rate_limited': 30}))
    assert 'rate_limited' in codes(d)


def test_sorting_error_first():
    d = alerts.evaluate(snap(status={'GET /x 500': 30, 'GET /x 200': 10},
                             routes={'GET /x': {'count': 40, 'p95_ms': 2000}},
                             events={'guard_hit': 1}))
    levels = [a['level'] for a in d['alerts']]
    assert levels == sorted(levels, key=lambda x: {'error': 0, 'warn': 1, 'info': 2}[x])


def test_breaker_open_is_a_warning():
    d = alerts.evaluate(snap(status={'POST /api/chat 200': 10},
                             breaker={'state': 'open', 'retry_in_s': 42.0}))
    hit = [a for a in d['alerts'] if a['code'] == 'circuit_open']
    assert hit and '42' in hit[0]['detail']


def test_api_alerts_endpoint(client):
    client.get('/api/now')
    d = client.get('/api/alerts').json()
    assert set(d) >= {'ok', 'alerts', 'total', 'errors', 'error_rate'}
    assert d['total'] >= 1
