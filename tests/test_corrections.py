"""勘误台账：读写、校验、命令行三件事。"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import corrections as corr  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(corr, 'LEDGER', tmp_path / 'corrections.jsonl')
    yield


def test_empty_ledger():
    assert corr.load() == []
    assert corr.counts()['open'] == 0


def test_add_and_reload():
    r = corr.add('calc', '/api/year', '差 2 分钟', 'pymeeus 04:04:11', '@someone')
    assert r['id'] == 'c-0001' and r['status'] == 'open'
    rows = corr.load()
    assert len(rows) == 1 and rows[0]['claim'] == '差 2 分钟'


def test_ids_increment():
    corr.add('calc', '/a', 'x', 'y')
    r2 = corr.add('cite', '/b', 'x', 'y')
    assert r2['id'] == 'c-0002'


def test_validate_rejects_bad_kind():
    bad = {'id': 'c-1', 'at': '2026-11-03', 'kind': 'nonsense', 'target': '/a',
           'claim': 'x', 'evidence': 'y', 'status': 'open'}
    assert any('kind' in e for e in corr.validate(bad))


def test_validate_rejects_missing():
    assert corr.validate({'id': 'c-1'}) != []


def test_add_rejects_bad_input():
    with pytest.raises(ValueError):
        corr.add('nope', '/a', 'x', 'y')


def test_api_endpoint(client, tmp_path, monkeypatch):
    monkeypatch.setattr(corr, 'LEDGER', tmp_path / 'c.jsonl')
    d = client.get('/api/corrections').json()
    assert d['count'] == 0 and d['items'] == []
    assert d['doc'] == '/CORRECTIONS.md'
    assert set(d['kinds']) == {'calc', 'cite', 'wording', 'other'}

    corr.add('wording', '/api/chat', '这句话像在预测', '「你会升职」这句')
    d = client.get('/api/corrections').json()
    assert d['count'] == 1 and d['items'][0]['status'] == 'open'
    assert d['counts']['open'] == 1


def test_ledger_file_is_valid_jsonl():
    corr.add('other', '/x', 'claim', 'evidence')
    text = corr.LEDGER.read_text(encoding='utf-8')
    for line in text.splitlines():
        json.loads(line)
