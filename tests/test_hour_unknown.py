"""不知道几点生：只给日期也能排，时柱标「？？」，并告诉模型时柱不作数。"""
import pytest

from server import cal, compare


def test_date_only_is_hour_unknown():
    dt, known = cal.parse_birth('1996-04-18')
    assert (dt.hour, dt.minute, known) == (12, 0, False)
    assert cal.parse_birth('1996-04-18 14:06')[1] is True
    with pytest.raises(ValueError):
        cal.parse_birth('1996/4/18')


def test_chart_masks_hour_pillar_and_warns():
    full = cal.chart_snapshot('1996-04-18 14:06', 120.0)
    c = cal.chart_snapshot('1996-04-18', 120.0)
    assert c['hour_known'] is False and full['hour_known'] is True
    # 年、月、日三柱和有时辰时一样，时柱不给
    assert c['bazi'].split()[:3] == full['bazi'].split()[:3]
    assert c['bazi'].split()[3] == '？？'
    assert c['warnings'][0]['kind'] == 'hour_unknown'


def test_compare_accepts_date_only():
    d = compare.compare('1996-04-18', 120.0)
    assert all(v['bazi'].endswith('？？') for v in d['variants'])
