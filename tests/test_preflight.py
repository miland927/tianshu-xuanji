"""preflight 的 key 掩码：别把 key 打全，也别假装能验没有的 key。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from preflight import mask  # noqa: E402


def test_missing_key():
    assert '未设置' in mask(None)
    assert '未设置' in mask('')


def test_long_key_is_masked():
    m = mask('sk-1234567890abcdef')
    assert '1234567890' not in m          # 中段不出现
    assert m.startswith('sk-1') and 'cdef' in m
    assert '19' in m                       # 长度照实说


def test_short_key_is_barely_shown():
    assert mask('short') == 's***'
