"""出处原文：引用能不能落到数据里那一条。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import passages  # noqa: E402


def test_datasets_exist():
    for name in ('qiongtong.json', 'ziping.json', 'shenfeng.json'):
        assert (passages.DATA / name).exists(), name
    assert len(passages._load('qiongtong.json').get('entries') or {}) == 10


def test_qiongtong_hits():
    r = passages.lookup('调候·火土 / 穷通宝鉴·乙日辰月')
    assert r['found']
    assert r['loc'].startswith('三春乙木')
    assert '三月乙木' in r['quote']
    assert r['verdict'] in passages.VERDICT
    assert r['gloss'] and r['quote_source']


def test_ziping_hits():
    r = passages.lookup('透于hour / 子平真诠·论用神')
    assert r['found']
    assert r['loc'] == '論用神'
    assert r['quote']
    assert r['title'] == '子平真詮'


def test_shenfeng_hits_and_prefix():
    a = passages.lookup('神峰通考·病药说')
    b = passages.lookup('神峰通考·病药')
    assert a['found'] and b['found']
    assert a['loc'] == b['loc'] == '病药说类'
    assert '何以为之病' in a['quote']


def test_all_gan_zhi_have_entries():
    for gan in '甲乙丙丁戊己庚辛壬癸':
        for zhi in '子丑寅卯辰巳午未申酉戌亥':
            r = passages.lookup(f'穷通宝鉴·{gan}日{zhi}月')
            assert r['found'], (gan, zhi)
            assert r['quote'], (gan, zhi)


def test_jinbuhuan_is_honest_about_missing_context():
    r = passages.lookup('金不换喜·丙')
    assert r['found'] is False
    assert '金不换' in r['reason'] and '定位不到' in r['reason']


def test_lookup_misses():
    assert not passages.lookup('随便一句话')['found']
    assert not passages.lookup('')['found']
    assert not passages.lookup('子平真诠·不存在的篇目')['found']


def test_books_listed():
    assert set(passages.books()) == {'窮通寶鑑', '子平真詮', '神峰通考'}
