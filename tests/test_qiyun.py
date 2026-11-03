"""起运材料：把「怎么算」的原料摆给模型，不给第二个互相打架的岁数。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.cal import chart_snapshot  # noqa: E402

BIRTH = '1996-04-18 14:06'


def q(birth=BIRTH, gender=0):
    return chart_snapshot(birth, 114.93, gender)['qiyun']


def test_forward_for_yang_male():
    r = q()
    assert r['forward'] is True
    assert r['anchor']['name'] == '立夏'          # 生日之后的下一个节
    assert 16 < r['days'] < 18
    assert r['library_age'] == 6


def test_reverse_for_yang_female():
    r = q(gender=1)
    assert r['forward'] is False
    assert r['anchor']['name'] == '清明'          # 生日之前的上一个节
    assert 13 < r['days'] < 14
    assert r['library_age'] == 5


def test_fields_present():
    r = q()
    for k in ('forward', 'basis', 'anchor', 'span', 'days', 'rule', 'library_age',
              'age_meaning', 'note'):
        assert k in r, k
    assert '三日折一年' in r['rule']
    assert '虚岁' in r['age_meaning']


def test_no_competing_age():
    """不提供第二个起运岁数：两份实现边界上会差一岁，摆出来只会让人猜。"""
    r = q()
    assert 'computed_age' not in r and 'agrees' not in r


def test_anchor_matches_library_month_jieqi():
    from datetime import datetime

    from tianzhi_core.calendar import jieqi
    birth = datetime(1996, 4, 18, 14, 6)
    name, at = jieqi.next_jie(birth)
    r = q()
    assert r['anchor']['name'] == name
    assert r['anchor']['at'] == at.strftime('%Y-%m-%d %H:%M')


def test_library_age_is_int_virtual_age():
    for birth, gender in (('1990-06-01 12:00', 1), ('2000-01-01 00:30', 0),
                          ('1984-11-20 06:20', 1)):
        r = q(birth, gender)
        assert isinstance(r['library_age'], int)
        assert 1 <= r['library_age'] <= 12
