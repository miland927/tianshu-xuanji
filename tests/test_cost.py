"""成本核算：只用上游给的 usage；预算超了就不再打上游。"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server.app as app_module  # noqa: E402
import server.cost as cost  # noqa: E402
from server.cost import Ledger  # noqa: E402


class FakeDay:
    def __init__(self, d):
        self.d = d

    def __call__(self):
        return self.d


@pytest.fixture()
def ledger(monkeypatch):
    L = Ledger(today=FakeDay(date(2026, 11, 3)))
    monkeypatch.setattr(cost, 'LEDGER', L)
    monkeypatch.setattr(app_module.cost, 'LEDGER', L)
    return L


def test_empty(ledger):
    s = ledger.snapshot()
    assert s['requests'] == 0 and s['prompt_tokens'] == 0
    assert s['estimated_cny'] == 0.0 and s['over_budget'] is False


def test_records_usage(ledger):
    ledger.record({'prompt_tokens': 1000, 'completion_tokens': 200})
    s = ledger.snapshot()
    assert s['requests'] == 1 and s['prompt_tokens'] == 1000 and s['completion_tokens'] == 200
    # 默认价 2/8 元每百万
    assert s['estimated_cny'] == pytest.approx((1000 * 2 + 200 * 8) / 1e6, abs=1e-6)


def test_missing_usage_counted_separately(ledger):
    ledger.record(None)
    s = ledger.snapshot()
    assert s['requests'] == 1 and s['requests_without_usage'] == 1
    assert s['prompt_tokens'] == 0 and s['estimated_cny'] == 0.0


def test_day_rollover(ledger, monkeypatch):
    ledger.record({'prompt_tokens': 10, 'completion_tokens': 10})
    assert ledger.snapshot()['prompt_tokens'] == 10
    ledger._today = FakeDay(date(2026, 11, 4))
    s = ledger.snapshot()
    assert s['day'] == '2026-11-04' and s['prompt_tokens'] == 0


def test_price_override(ledger, monkeypatch):
    monkeypatch.setenv('XJI_PRICE_IN', '0')
    monkeypatch.setenv('XJI_PRICE_OUT', '0')
    ledger.record({'prompt_tokens': 10 ** 6, 'completion_tokens': 10 ** 6})
    assert ledger.snapshot()['estimated_cny'] == 0.0


def test_budget_flag(ledger, monkeypatch):
    monkeypatch.setenv('XJI_PRICE_IN', '100')
    monkeypatch.setenv('XJI_DAILY_BUDGET', '1')
    assert ledger.snapshot()['over_budget'] is False
    ledger.record({'prompt_tokens': 20_000, 'completion_tokens': 0})   # 2 元
    s = ledger.snapshot()
    assert s['over_budget'] is True and s['daily_budget_cny'] == 1.0


def test_metrics_exposes_cost(client):
    d = client.get('/api/metrics').json()
    assert 'cost' in d and 'estimated_cny' in d['cost']


# ---- 端到端：假上游回一段带 usage 的流 ----

class FakeResp:
    status_code = 200

    def __init__(self, lines):
        self._lines = lines

    async def aread(self):
        return b''

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class FakeStream:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *a):
        return False


class FakeClient:
    def __init__(self, resp):
        self._resp = resp

    def stream(self, *a, **kw):
        return FakeStream(self._resp)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def test_chat_records_usage_from_stream(client, ledger, monkeypatch):
    lines = [
        'data: {"choices":[{"delta":{"content":"此刻霜降。"}}]}',
        'data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":321,"completion_tokens":45}}',
        'data: [DONE]',
    ]
    monkeypatch.setattr(app_module, 'API_KEY', 'sk-fake')
    monkeypatch.setattr(app_module.httpx, 'AsyncClient', lambda *a, **kw: FakeClient(FakeResp(lines)))

    r = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': '此刻什么节气？'}]})
    assert r.status_code == 200
    assert '此刻霜降' in r.text
    s = ledger.snapshot()
    assert s['prompt_tokens'] == 321 and s['completion_tokens'] == 45
    assert s['requests'] == 1 and s['requests_without_usage'] == 0


def test_chat_blocks_when_over_budget(client, ledger, monkeypatch):
    monkeypatch.setenv('XJI_PRICE_IN', '1000')
    monkeypatch.setenv('XJI_DAILY_BUDGET', '0.5')
    ledger.record({'prompt_tokens': 1000, 'completion_tokens': 0})   # 1 元 > 0.5
    monkeypatch.setattr(app_module, 'API_KEY', 'sk-fake')

    r = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': '在吗'}]})
    assert 'budget_exhausted' in r.text
    assert 'event: degraded' in r.text
