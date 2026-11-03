"""月相：与独立实现（ephem）对表，并验几个硬事实。"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import moon  # noqa: E402


def test_elongation_cycle_bounds():
    e = moon.elongation(datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc))
    assert 0 <= e < 360


def test_phase_names_cover_circle():
    names = [moon.phase_name(d) for d in range(0, 360, 1)]
    assert set(names) == {'新月', '蛾眉月', '上弦', '盈凸', '满月', '亏凸', '下弦', '残月'}


def test_phase_name_boundaries():
    assert moon.phase_name(0) == '新月'
    assert moon.phase_name(180) == '满月'
    assert moon.phase_name(90) == '上弦'
    assert moon.phase_name(270) == '下弦'


def test_illumination_matches_phase():
    s = moon.snapshot(datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc))
    assert 0 <= s['illum'] <= 1
    if s['name'] == '满月':
        assert s['illum'] > 0.9
    if s['name'] == '新月':
        assert s['illum'] < 0.1


def test_against_ephem():
    ephem = pytest.importorskip('ephem')
    for dt in (datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc),
               datetime(2020, 6, 21, 5, 43, tzinfo=timezone.utc),
               datetime(1996, 4, 18, 6, 6, tzinfo=timezone.utc)):
        ours = moon.snapshot(dt)
        m = ephem.Moon()
        m.compute(dt.replace(tzinfo=None))
        ref_illum = m.phase / 100.0
        # ephem 的 phase 是「被照亮的百分比」
        assert abs(ours['illum'] - ref_illum) < 0.03, (dt, ours['illum'], ref_illum)


def test_synodic_age_within_month():
    s = moon.snapshot(datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc))
    assert 0 <= s['age_days'] < 29.54


def test_now_snapshot_includes_moon():
    from server.cal import now_snapshot
    n = now_snapshot()
    assert set(n['moon']) >= {'elong_deg', 'name', 'illum', 'waxing', 'age_days'}
    assert n['moon']['name'] in {p[1] for p in moon.PHASES}


def test_year_events_counts():
    ev = moon.year_events(2026)
    news = [e for e in ev if e['kind'] == '朔']
    fulls = [e for e in ev if e['kind'] == '望']
    assert 12 <= len(news) <= 13
    assert 12 <= len(fulls) <= 13
    assert len(ev) == len(news) + len(fulls)
    assert [e['at'] for e in ev] == sorted(e['at'] for e in ev)


def test_synodic_spacing():
    news = [e['at'] for e in moon.year_events(2026) if e['kind'] == '朔']
    gaps = [(news[i + 1] - news[i]).total_seconds() / 86400 for i in range(len(news) - 1)]
    for g in gaps:
        assert 29.2 < g < 29.9, g


def test_full_moon_about_half_month_after_new():
    ev = moon.year_events(2026)
    for i, e in enumerate(ev[:-1]):
        if e['kind'] == '朔':
            nxt = ev[i + 1]
            if nxt['kind'] == '望':
                gap = (nxt['at'] - e['at']).total_seconds() / 86400
                # 半个朔望月不是常数：月行有迟疾，13.9–15.6 天都出现过
                assert 13.5 < gap < 15.7, gap


def test_year_events_match_ephem():
    ephem = pytest.importorskip('ephem')
    from datetime import timedelta
    ev = moon.year_events(2026)
    checked = 0
    for e in ev:
        if e['kind'] != '望':
            continue
        utc = e['at'] - timedelta(hours=8)
        ref = ephem.next_full_moon(utc - timedelta(days=2))
        diff = abs((ref.datetime() - utc).total_seconds()) / 60.0
        assert diff < 15, (e['at'], ref, diff)
        checked += 1
    assert checked >= 10
