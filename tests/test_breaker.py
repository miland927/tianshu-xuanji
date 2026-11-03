"""熔断：三态机、冷却、半开探针，以及接到聊天接口上的效果。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server.app as app_module  # noqa: E402
from server.breaker import Breaker  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def tick(self, s):
        self.t += s


def make(threshold=3, cooldown=60.0):
    c = Clock()
    return Breaker(threshold=threshold, cooldown=cooldown, clock=c), c


def test_starts_closed():
    k, _ = make()
    assert k.state == 'closed'
    assert k.allow() is True


def test_opens_after_threshold():
    k, _ = make()
    k.failure(); k.failure()
    assert k.state == 'closed' and k.failures == 2
    k.failure()
    assert k.state == 'open'
    assert k.allow() is False


def test_success_resets():
    k, _ = make()
    k.failure(); k.failure()
    k.success()
    assert k.state == 'closed' and k.failures == 0
    assert k.allow() is True


def test_half_open_after_cooldown():
    k, c = make()
    for _ in range(3):
        k.failure()
    assert k.allow() is False
    c.tick(61)
    assert k.snapshot()['retry_in_s'] == 0.0
    assert k.allow() is True          # 放一个探针
    assert k.state == 'half_open'
    assert k.allow() is False         # 探针在飞，不给第二个


def test_half_open_success_closes():
    k, c = make()
    for _ in range(3):
        k.failure()
    c.tick(61)
    k.allow()
    k.success()
    assert k.state == 'closed' and k.failures == 0


def test_half_open_failure_reopens():
    k, c = make()
    for _ in range(3):
        k.failure()
    c.tick(61)
    k.allow()
    k.failure()
    assert k.state == 'open'
    assert k.allow() is False
    c.tick(61)
    assert k.allow() is True


def test_retry_in_counts_down():
    k, c = make()
    for _ in range(3):
        k.failure()
    assert k.snapshot()['retry_in_s'] == 60.0
    c.tick(20)
    assert k.snapshot()['retry_in_s'] == 40.0


def test_snapshot_fields():
    k, _ = make()
    s = k.snapshot()
    assert set(s) == {'state', 'failures', 'threshold', 'cooldown_s', 'retry_in_s'}


def test_chat_short_circuits_when_open(client, monkeypatch):
    monkeypatch.setattr(app_module, 'API_KEY', 'sk-fake')   # 让流程走到上游那一支
    monkeypatch.setattr(app_module.breaker, 'BREAKER', Breaker(threshold=1, cooldown=60))
    app_module.breaker.BREAKER.failure()                    # 直接打成一开
    assert app_module.breaker.BREAKER.state == 'open'

    r = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': '此刻什么节气？'}]})
    assert r.status_code == 200
    body = r.text
    assert 'circuit_open' in body
    assert 'event: degraded' in body
    assert 'error:' not in body.split('event: degraded')[1][:200]


def test_metrics_exposes_breaker(client):
    d = client.get('/api/metrics').json()
    assert 'breaker' in d and d['breaker']['state'] in ('closed', 'open', 'half_open')
