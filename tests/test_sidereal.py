"""恒星时与二十八宿：公式对不对、分界闭不闭合、算出来的宿对不对。"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import sidereal  # noqa: E402


def test_julian_date_epoch():
    assert sidereal.julian_date(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)) == pytest.approx(2451545.0, abs=1e-9)


def test_gmst_at_j2000():
    # Meeus 12.4 在 J2000.0 处的常数项
    assert sidereal.gmst_deg(2451545.0) % 360 == pytest.approx(280.46061837 % 360, abs=1e-6)


def test_sidereal_day_rate():
    # 一天后恒星时约前进 360.9856°
    a = sidereal.gmst_deg(2451545.0)
    b = sidereal.gmst_deg(2451546.0)
    assert ((b - a) % 360) == pytest.approx(0.9856, abs=0.001)


def test_spans_close_the_circle():
    sp = sidereal.spans()
    assert len(sp) == 28
    assert sum(sidereal.widths()) == pytest.approx(360.0, abs=1e-9)
    # spans() 里每段保留三位小数，累计误差到 1e-2 量级
    assert sum(s['width'] for s in sp) == pytest.approx(360.0, abs=0.02)
    assert sp[-1]['end'] == pytest.approx(sp[0]['start'], abs=0.01)


def test_xiu_at_covers_every_degree():
    for deg in range(0, 360, 7):
        x = sidereal.xiu_at(float(deg))
        assert 0 <= x['index'] < 28
        assert 0 <= x['into'] < x['width'] + 1e-6


def test_xiu_boundary_is_consistent():
    x = sidereal.xiu_at(sidereal.XI_START_DEG)
    assert x['name'] == '角' and x['into'] == pytest.approx(0.0, abs=0.02)


def test_lst_matches_ephem():
    ephem = pytest.importorskip('ephem')
    for dt in (datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
               datetime(2026, 11, 3, 16, 6, tzinfo=timezone.utc)):
        ours = sidereal.lst_deg(dt, 139.69)
        obs = ephem.Observer()
        obs.lon, obs.lat = '139.69', '35.0'
        obs.date = dt.replace(tzinfo=None)
        ref = float(obs.sidereal_time()) * 180 / 3.141592653589793
        assert abs(((ours - ref + 180) % 360) - 180) < 0.02


def test_now_snapshot_carries_sidereal():
    from server.cal import now_snapshot
    n = now_snapshot(139.69)
    assert 'sidereal' in n
    assert n['sidereal']['xiu']['name'] in [name for name, _ in sidereal.XIU]
    assert n['sidereal']['lst_hms'].count('h') == 1
