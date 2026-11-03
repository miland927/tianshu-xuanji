"""夏令时检测的测试。跑：.venv\\Scripts\\python.exe -m pytest tests -q"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.dst import dst_offset, in_dst, warning, windows  # noqa: E402


def test_1990_summer_is_dst():
    assert dst_offset(datetime(1990, 6, 1, 12)) == timedelta(hours=1)


def test_1990_winter_is_not():
    assert dst_offset(datetime(1990, 12, 1, 12)) == timedelta(0)


def test_1995_has_no_dst():
    assert not in_dst(datetime(1995, 6, 1, 12))


def test_windows_cover_1986_to_1991():
    ws = windows('Asia/Shanghai', 1980, 1995)
    years = sorted({w[0].year for w in ws})
    assert years == [1986, 1987, 1988, 1989, 1990, 1991]


def test_window_bounds_are_hours_and_ordered():
    ws = windows('Asia/Shanghai', 1980, 1995)
    for start, end in ws:
        assert start < end
        assert start.minute == 0 and start.second == 0


def test_warning_payload():
    w = warning(datetime(1988, 7, 1, 9, 30))
    assert w and w['kind'] == 'dst' and w['offset_minutes'] == 60
    assert '夏令时' in w['text']
    assert warning(datetime(2001, 7, 1, 9, 30)) is None
