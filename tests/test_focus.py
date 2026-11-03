"""联动：问法 → 环与字。索引不在这里，留给轮子自己查。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.app import _focus  # noqa: E402
from server.cal import chart_snapshot, now_snapshot  # noqa: E402


def ctx(birth=None):
    c = {'now': now_snapshot(114.93)}
    if birth:
        c['chart'] = chart_snapshot(birth, 114.93, 0)
    return c


def test_jieqi_question_focuses_term_ring():
    c = ctx()
    f = _focus(c, '现在是什么节气？')
    assert f['ring'] == '二十四节气'
    # 「此刻的节气」要算中气：霜降，不是月建用的节「寒露」
    assert f['label'] == c['now']['term']['name']


def test_day_question_focuses_jiazi_ring_with_today_pillar():
    c = ctx()
    f = _focus(c, '今天日柱是什么？')
    assert f['ring'] == '六十甲子'
    assert f['label'] == c['now']['bazi'].split()[2]


def test_hour_question_focuses_branch_ring():
    c = ctx()
    f = _focus(c, '现在什么时辰？')
    assert f['ring'] == '十二地支'
    assert f['label'] == c['now']['bazi'].split()[3][1]


def test_chart_day_pillar_takes_precedence():
    c = ctx('1996-04-18 14:06')
    f = _focus(c, '这个盘的日柱')
    assert f['label'] == '乙酉'


def test_unknown_question_defaults_to_jieqi():
    f = _focus(ctx(), '帮我看看')
    assert f['ring'] == '二十四节气'


def test_empty_context_is_safe():
    assert _focus({}, '随便问问') is None


def test_term_index_matches_ring_order():
    from server.cal import RING_ORDER, now_snapshot
    t = now_snapshot()['term']
    assert RING_ORDER[t['index']] == t['name']
