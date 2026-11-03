"""海外时区：同一段钟表时间，标准经线不同，时柱就该不同。

这是 P2 最后一块：库只认东八区，我们用一个等价代换把当地标准时折进去。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.cal import chart_snapshot, effective_longitude  # noqa: E402


def hour_zhi(chart):
    return chart['quad']['hour'][1]


def test_effective_longitude_is_identity_in_china():
    assert effective_longitude(114.93) == 114.93
    assert effective_longitude(87.62, 120.0) == 87.62


def test_effective_longitude_shifts_by_meridian():
    assert round(effective_longitude(139.69, 135.0), 2) == 124.69
    assert round(effective_longitude(-74.0, -75.0), 2) == 121.0


def test_tokyo_noon_is_wu_hour_not_wei():
    # 东京 12:00 → 真太阳时约 12:17 → 午时；若按东八区算会跑到 13:17 变未时
    ok = chart_snapshot('2023-06-21 12:00', 139.69, 1, standard_longitude=135.0)
    bad = chart_snapshot('2023-06-21 12:00', 139.69, 1, standard_longitude=120.0)
    assert hour_zhi(ok) == '午'
    assert hour_zhi(bad) == '未'
    assert ok['true_solar'].startswith('2023-06-21 12:1')
    assert any(w['kind'] == 'tz' for w in bad['warnings'])
    assert not any(w['kind'] == 'tz' for w in ok['warnings'])


def test_new_york_noon_is_not_previous_midnight():
    ok = chart_snapshot('2023-06-21 12:00', -74.0, 0, standard_longitude=-75.0)
    bad = chart_snapshot('2023-06-21 12:00', -74.0, 0, standard_longitude=120.0)
    assert ok['true_solar'].startswith('2023-06-21 12:0')
    assert bad['true_solar'].startswith('2023-06-20 23:')
    assert hour_zhi(ok) == '午'
    assert hour_zhi(bad) == '子'


def test_day_pillar_correct_for_overseas():
    # 纽约 12:00 仍是当地的 6 月 21 日，日柱不该被换算成北京时间的次日
    ny = chart_snapshot('2023-06-21 12:00', -74.0, 0, standard_longitude=-75.0)
    cn = chart_snapshot('2023-06-21 12:00', 116.40, 0)
    assert ny['quad']['day'] == cn['quad']['day']


def test_urumqi_stays_on_china_standard_time():
    c = chart_snapshot('2023-03-22 09:00', 87.62, 0)
    assert c['true_solar'].startswith('2023-03-22 06:4')
    assert not any(w['kind'] == 'tz' for w in c['warnings'])
