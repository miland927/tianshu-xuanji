"""毕法原文：条号能不能对上《六壬大全》那一句。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import bifa  # noqa: E402


def test_dataset_has_hundred():
    assert bifa.count() == 100, '毕法赋百句'


def test_first_item():
    d = bifa.get(1)
    assert d['found']
    assert d['verse'] == '前後引從陞遷吉'
    assert d['vol'] == 9
    assert len(d['commentary']) > 200
    assert 'edition' in d and d['edition']


def test_vol_ranges():
    vols = {bifa.get(n)['vol'] for n in range(1, 101)}
    assert vols == {9, 10}, '赋文分卷九、卷十'


def test_missing_number():
    d = bifa.get(999)
    assert d['found'] is False and 'reason' in d


def test_every_item_has_verse():
    for n in range(1, 101):
        d = bifa.get(n)
        assert d['found'], n
        assert d['verse'], n


def test_three_items_have_no_commentary_and_we_say_so():
    # 原书（据维基文库录文）这三条没有注；如实标出，不补写
    empty = [n for n in range(1, 101) if not bifa.get(n)['commentary']]
    assert empty == [56, 85, 87], empty
    for n in empty:
        assert bifa.get(n)['no_commentary'] is True
