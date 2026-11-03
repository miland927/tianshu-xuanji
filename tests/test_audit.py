"""审计日志的测试：字段齐、隐私默认、能写能读、能清理。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import audit  # noqa: E402


def test_versions_stable_and_complete():
    v1, v2 = audit.versions(), audit.versions()
    assert v1 == v2
    assert set(v1) == {'core', 'model', 'prompt', 'rules', 'cal'}
    assert v1['core'] != 'unknown'


def test_birth_masked_by_default(monkeypatch):
    monkeypatch.setattr(audit, 'STORE_BIRTH', False)
    m = audit.mask_birth('1996-04-18 14:06')
    assert 'birth' not in m
    assert m['birth_day'] == '1996-04-18'
    assert len(m['birth_hash']) == 8


def test_birth_kept_when_opted_in(monkeypatch):
    monkeypatch.setattr(audit, 'STORE_BIRTH', True)
    m = audit.mask_birth('1996-04-18 14:06')
    assert m['birth'] == '1996-04-18 14:06'


def test_write_then_read_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'AUDIT_DIR', tmp_path)
    rid = audit.write({'id': 'x1', 'ms': 12, 'status': 'ok', 'in': '问', 'out': '答'})
    files = list(tmp_path.glob('*.jsonl'))
    assert files, '没写文件'
    rec = json.loads(files[0].read_text(encoding='utf-8').splitlines()[0])
    assert rid == 'x1'
    assert rec['in'] == '问' and rec['out'] == '答'
    assert 'versions' in rec and 'ts' in rec


def test_purge_removes_old_files(tmp_path, monkeypatch):
    import os
    import time

    monkeypatch.setattr(audit, 'AUDIT_DIR', tmp_path)
    old = tmp_path / '2020-01-01.jsonl'
    old.write_text('{}\n', encoding='utf-8')
    stamp = time.time() - 40 * 86400
    os.utime(old, (stamp, stamp))
    gone = audit.purge(30)
    assert '2020-01-01.jsonl' in gone
    assert not old.exists()


def test_derived_keeps_explanations_but_not_birth():
    from server.app import _derived
    from server.cal import chart_snapshot

    d = _derived(chart_snapshot('1996-04-18 14:06', 114.93, 0))
    assert d['strength']['label'] == '中和'
    assert d['geju'] == '偏印格'
    assert d['evidence'][0] == '旺衰·中和'
    assert '1996-04-18' not in json.dumps(d, ensure_ascii=False)
    assert _derived(None) == {}


def test_scrub_masks_datetime_in_text():
    s = audit.scrub('我 1996-04-18 14:06 出生，想看看盘')
    assert '14:06' not in s
    assert '1996-04-18 14:06' not in s
    assert '〔已隐去〕' in s


def test_scrub_masks_explicit_secret():
    s = audit.scrub('生于 1996-04-18 14:06 的人', secrets=['1996-04-18 14:06'])
    assert '1996-04-18 14:06' not in s


def test_scrub_keeps_calendar_facts():
    # 回答里出现节气时刻是正常的，不该被当成生辰抹掉
    s = audit.scrub('立冬在 2026-11-07 17:52 交节', secrets=['1996-04-18 14:06'], generic=False)
    assert '2026-11-07 17:52' in s


def test_scrub_generic_masks_any_datetime():
    s = audit.scrub('立冬在 2026-11-07 17:52 交节')
    assert '2026-11-07 17:52' not in s


def test_scrub_handles_none_and_plain():
    assert audit.scrub('') == ''
    assert audit.scrub('今天天气不错') == '今天天气不错'
