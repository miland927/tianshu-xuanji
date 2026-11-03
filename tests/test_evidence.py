"""依据面板的数据源测试：界面上的每一行都必须来自这里，不能前端现编。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.cal import chart_snapshot, now_snapshot  # noqa: E402
from server.evidence import groups  # noqa: E402


def ctx(birth=None, lon=114.93):
    c = {'now': now_snapshot(lon)}
    if birth:
        c['chart'] = chart_snapshot(birth, lon, 0)
    return c


def test_now_only_has_calendar_layer():
    g = groups(ctx())
    assert [x['layer'] for x in g] == ['历法']
    assert all(isinstance(i, str) and i for i in g[0]['items'])


def test_chart_has_all_layers_in_order():
    g = groups(ctx('1996-04-18 14:06'))
    assert [x['layer'] for x in g] == ['历法', '四柱', '旺衰', '格局', '用神', '岁运']


def test_items_are_non_empty_strings():
    for layer in groups(ctx('1996-04-18 14:06')):
        assert layer['items'], f"{layer['layer']} 空了"
        for it in layer['items']:
            assert isinstance(it, str) and it.strip()


def test_yongshen_evidence_reaches_ui():
    g = {x['layer']: x['items'] for x in groups(ctx('1996-04-18 14:06'))}
    joined = ' '.join(g['用神'])
    assert '病·水最旺' in joined and '穷通宝鉴·乙日辰月' in joined


def test_dst_warning_shows_up():
    g = {x['layer']: x['items'] for x in groups(ctx('1990-06-01 12:00'))}
    assert '提示' in g and any('夏令时' in i for i in g['提示'])


def test_no_chart_means_no_fake_layers():
    g = groups({'now': now_snapshot(114.93)})
    assert '格局' not in [x['layer'] for x in g]
