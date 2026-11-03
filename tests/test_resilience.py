"""限流与降级：上游坏了不许留白，来的人太多不许无限制地花钱。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server.app as A  # noqa: E402


def test_rate_limit_blocks_after_quota(monkeypatch):
    monkeypatch.setattr(A, 'RATE_LIMIT', 2)
    monkeypatch.setattr(A, 'RATE_WINDOW', 60)
    A._hits.clear()
    assert A._rate_ok('1.1.1.1')[0] is True
    assert A._rate_ok('1.1.1.1')[0] is True
    ok, retry = A._rate_ok('1.1.1.1')
    assert ok is False and retry > 0


def test_rate_limit_is_per_ip(monkeypatch):
    monkeypatch.setattr(A, 'RATE_LIMIT', 1)
    monkeypatch.setattr(A, 'RATE_WINDOW', 60)
    A._hits.clear()
    assert A._rate_ok('2.2.2.2')[0] is True
    assert A._rate_ok('2.2.2.2')[0] is False
    assert A._rate_ok('3.3.3.3')[0] is True


def test_rate_window_expires(monkeypatch):
    monkeypatch.setattr(A, 'RATE_LIMIT', 1)
    monkeypatch.setattr(A, 'RATE_WINDOW', 0.01)
    A._hits.clear()
    assert A._rate_ok('4.4.4.4')[0] is True
    import time
    time.sleep(0.02)
    assert A._rate_ok('4.4.4.4')[0] is True


def test_fallback_reads_numbers_not_stories():
    from server.cal import chart_snapshot, now_snapshot
    ctx = {'now': now_snapshot(114.93), 'chart': chart_snapshot('1996-04-18 14:06', 114.93, 0)}
    text = A._fallback_text(ctx)
    assert '模型暂时不可用' in text
    assert '丙子 壬辰 乙酉 癸未' in text
    assert '月建' in text
    assert '依据' in text
    # 降级时不许出现判断性措辞
    for bad in ('大凶', '必然', '一定会', '预测'):
        assert bad not in text
