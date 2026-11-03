"""年度报告：月份排列、五虎遁、与库里流月对得上。"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tianzhi_core.bazi import chart  # noqa: E402

from server import year as y  # noqa: E402

BIRTH = '1996-04-18 14:06'


def test_twelve_months_from_lichun_to_xiaohan():
    r = y.year_report(BIRTH, 2026)
    ms = r['months']
    assert len(ms) == 12
    assert ms[0]['jie'] == '立春' and ms[0]['zhi'] == '寅'
    assert ms[-1]['jie'] == '小寒' and ms[-1]['zhi'] == '丑'
    assert [m['zhi'] for m in ms] == list('寅卯辰巳午未申酉戌亥子丑')


def test_month_ganzhi_matches_library():
    # 五虎遁推出来的月干，应与库在同一个时刻排出的月柱一致
    r = y.year_report(BIRTH, 2026)
    for m in r['months']:
        dt = datetime.strptime(m['at'], '%Y-%m-%d %H:%M:%S')
        c = chart.build_chart(dt + __import__('datetime').timedelta(hours=1), longitude=114.93, gender=0)
        month_pillar = c.bazi.split()[1]
        assert month_pillar == m['gz'], (m['zhi'], month_pillar, m['gz'])


def test_wuhudun_table():
    assert y.month_ganzhi('丙', 0) == '庚寅'
    assert y.month_ganzhi('甲', 0) == '丙寅'
    assert y.month_ganzhi('戊', 0) == '甲寅'
    assert y.month_ganzhi('乙', 11) == '己丑'


def test_score_matches_chart_snapshot():
    from server.cal import chart_snapshot
    snap = chart_snapshot(BIRTH, 114.93, 0)
    r = y.year_report(BIRTH, int(snap['current']['year_gz'] and 2026))
    cur = snap['current']
    if cur['year_gz'] == r['year_gz']:
        assert r['score']['value'] == cur['score']
        assert r['score']['stance'] == cur['stance']


def test_ten_god_uses_day_master():
    r = y.year_report(BIRTH, 2026)
    assert r['day_master'] == '乙'
    assert r['months'][0]['ten_god'] == '正财'  # 乙日见庚


def test_dayun_attached():
    r = y.year_report(BIRTH, 2026)
    assert r['dayun'] and r['dayun']['start_year'] <= 2026 <= r['dayun']['end_year']
    assert all(m['dayun'] == r['dayun']['pillar'] for m in r['months'])


def test_ziwei_block_matches_ziwei_api():
    """年度报告里的紫微块，应与 /api/ziwei/year 是同一份数。"""
    from server.ziwei_year import year_view

    r = y.year_report(BIRTH, 2026)
    z = r['ziwei']
    ref = year_view(BIRTH, 0, 2026)
    assert z['age'] == ref['age'] == 31
    assert z['daxian']['name'] == ref['daxian']['name'] == '福德'
    assert z['liunian']['name'] == ref['liunian']['name'] == '子女'
    assert z['xiaoxian']['name'] == ref['xiaoxian']['name'] == '疾厄'
    assert [(s['hua'], s['star']) for s in z['sihua']] == \
           [(s['hua'], s['star']) for s in ref['sihua']]


def test_ziwei_failure_does_not_break_report(monkeypatch):
    import server.ziwei_year as zy

    def boom(*a, **kw):
        raise RuntimeError('模拟排盘失败')

    monkeypatch.setattr(zy, 'year_view', boom)
    r = y.year_report(BIRTH, 2026)
    assert 'error' in r['ziwei']
    assert len(r['months']) == 12    # 八字那半照旧
