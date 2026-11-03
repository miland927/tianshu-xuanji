"""紫微流年：大限、流年宫、小限、四化。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.ziwei_year import year_view  # noqa: E402

BIRTH = '1996-04-18 13:46'


def test_2026():
    r = year_view(BIRTH, 0, 2026)
    assert r['year_gz'] == '丙午'
    assert r['age'] == 31
    assert r['daxian']['zhi'] == '亥' and r['daxian']['name'] == '福德'
    assert r['daxian']['range'] == [26, 35]
    assert r['liunian']['zhi'] == '午' and r['liunian']['name'] == '子女'
    assert r['xiaoxian']['zhi'] == '辰'  # 疾厄
    assert r['ming']['zhi'] == '酉'


def test_sihua_of_bing_year():
    r = year_view(BIRTH, 0, 2026)
    got = [(s['hua'], s['star']) for s in r['sihua']]
    assert got == [('禄', '天同'), ('权', '天机'), ('科', '文昌'), ('忌', '廉贞')]


def test_daxian_moves_with_age():
    # 虚岁 15 仍在命宫大限（6–15），16 岁进父母宫（16–25）
    a = year_view(BIRTH, 0, 2010)
    b = year_view(BIRTH, 0, 2011)
    assert a['age'] == 15 and a['daxian']['name'] == '命宫'
    assert b['age'] == 16 and b['daxian']['name'] == '父母'


def test_before_first_daxian():
    r = year_view(BIRTH, 0, 1997)   # 虚岁 2，火六局 6 岁起运
    assert r['daxian'] is None
    assert r['xiaoxian'] is not None


def test_age_formula():
    r = year_view(BIRTH, 0, 1996)
    assert r['age'] == 1


def test_schema(client):
    d = client.get('/api/ziwei/year?birth=1996-04-18 13:46&gender=0&year=2026').json()
    for k in ('year_gz', 'age', 'daxian', 'liunian', 'xiaoxian', 'sihua', 'ming'):
        assert k in d, k
    assert len(d['sihua']) == 4
    bad = client.get('/api/ziwei/year?birth=bad')
    assert bad.status_code == 400
