"""紫微原文：宫 × 星能不能对上《全书》那一节。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import ziwei_src as z  # noqa: E402


def test_dataset_size():
    assert z.count() == 289
    assert len(z.palaces()) == 12


def test_ming_gong_ziwei():
    r = z.lookup('命宫', '紫微')
    assert r['found']
    assert r['text'].startswith('紫微土')
    assert r['branches'] and r['male'] and r['female']


def test_alias_modern_and_book_names():
    # 今名「夫妻」在书里是「妻妾」；「交友」是「奴仆」
    a = z.lookup('夫妻', '太阳')
    b = z.lookup('妻妾', '太阳')
    assert a['found'] and b['found']
    assert a['palace'] == '妻妾' and a['palace_alias'] == '夫妻'
    assert a['text'] == b['text']
    assert z.lookup('交友', '天机')['palace'] == '奴仆'


def test_lookup_any_prefers_first_hit():
    r = z.lookup_any('命宫', ['不存在的星', '紫微'])
    assert r['found'] and r['star'] == '紫微'


def test_missing():
    assert not z.lookup('命宫', '不存在')['found']
    assert not z.lookup_any('命宫', ['不存在'])['found']
    assert 'reason' in z.lookup_any('命宫', [])
