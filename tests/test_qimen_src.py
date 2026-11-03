"""奇门原文：格能不能落到《遁甲演义》那一节。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import qimen_src as q  # noqa: E402


def test_dataset():
    assert q.count() == 80


def test_lookup_by_chapter_name():
    r = q.lookup('地遁')
    assert r['found'] and r['vol'] == 2
    assert '開門六乙合六己' in r['text']


def test_old_glyphs_normalize():
    # 书里写「三竒得使」「六儀擊刑」，今天写「三奇得使」「六仪击刑」
    assert q.lookup('三奇得使')['chapter'] == '三竒得使'
    assert q.lookup('六仪击刑')['chapter'] == '六儀擊刑'
    assert q.lookup('青龙回首')['found']


def test_lookup_by_cite():
    # 格名与篇名不一致时，靠库给的 cite 定位
    cases = {
        '遁甲演義·卷二|刑隔': '刑隔',
        '遁甲演義·卷二|朱雀入江': '朱雀入江',
        '遁甲演義·卷二|青龍回首': '青龍回首',
        '遁甲演義·卷二|螣蛇跃蹻': '螣蛇跃蹻',
        '遁甲演義·卷二|小隔并嵗隔月隔日隔時隔': '小隔并嵗隔月隔日隔時隔',
    }
    for cite, chapter in cases.items():
        r = q.lookup_cite(cite)
        assert r['found'], cite
        assert r['chapter'] == chapter
        assert r['text']


def test_all_real_cites_resolve():
    from datetime import datetime

    from tianzhi_core.qimen import qiju
    for dt in (datetime(2026, 11, 3, 15), datetime(2026, 2, 4, 4, 30),
               datetime(2026, 7, 23, 9), datetime(2025, 4, 5, 10)):
        for g in qiju(dt)['geju']:
            assert q.lookup_cite(g['cite'])['found'], (g['name'], g['cite'])


def test_missing():
    assert not q.lookup_cite('')['found']
    assert not q.lookup_cite('遁甲演義·卷二|不存在的篇')['found']
