"""换一派：同一张盘，不同口径，差异必须显式可见。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.compare import VARIANTS, compare  # noqa: E402


def by_key(res, key):
    return next(v for v in res['variants'] if v['key'] == key)


def test_returns_all_variants():
    r = compare('1996-04-18 14:06')
    assert [v['key'] for v in r['variants']] == [v['key'] for v in VARIANTS]
    assert r['variants'][0]['bazi'] == '丙子 壬辰 乙酉 癸未'


def test_late_zi_changes_day_pillar_only_at_23():
    # 23:50 出生：默认归次日，另一派归当日，日柱应当不同
    r = compare('1997-08-15 23:50')
    base = by_key(r, 'baseline')
    same = by_key(r, 'late_zi_same_day')
    assert base['bazi'] != same['bazi']
    # 白天出生则两种口径一致
    r2 = compare('1996-04-18 14:06')
    assert by_key(r2, 'baseline')['bazi'] == by_key(r2, 'late_zi_same_day')['bazi']


def test_true_solar_toggle_shows_up_in_diff():
    # 15:05 出生，真太阳时校正后落到 14:45（未），不校正则仍是 15:05（申）——时柱整位之差
    r = compare('1996-04-18 15:05')
    keys = {d['key'] for d in r['diff']}
    assert 'bazi' in keys
    base = by_key(r, 'baseline')['bazi']
    no_solar = by_key(r, 'no_true_solar')['bazi']
    assert base != no_solar


def test_honest_when_no_difference():
    # 14:06 这张盘，三种口径算出来一样——那就该老实返回空表，不许硬凑
    assert compare('1996-04-18 14:06')['diff'] == []


def test_each_diff_row_explains_who_changed_it():
    r = compare('1996-04-18 15:05')
    assert r['diff']
    for d in r['diff']:
        assert d['changed_by'], f"{d['field']} 变了却没说谁改的"
        assert set(d['values']) == {v['key'] for v in r['variants']}


def test_no_diff_when_all_same():
    # 同一口径重复算，diff 应为空（比对自身一致性）
    from server.compare import _one, VARIANTS as V
    a = _one('2000-06-01 10:00', 114.93, 0, 120.0, V[0]['params'])
    b = _one('2000-06-01 10:00', 114.93, 0, 120.0, V[0]['params'])
    assert a == b
