"""发给模型的读数不带英文字段名；模型漏出来的就地换掉（走查 P1-2）。"""
import json
import re

from server import cal, zh
from server.persona import system_prompt


def _ctx(birth='1988-08-08 08:08'):
    return {'now': cal.now_snapshot(114.06, 22.54, 120), 'chart': cal.chart_snapshot(birth, 114.06, 0),
            'risk': [], 'gender_label': '男'}


def test_model_view_has_no_english_words():
    for b in ('1988-08-08 08:08', '1996-04-18 14:06', '2010-10-10 22:10', '1990-01-01'):
        blob = json.dumps(zh.model_view(_ctx(b)), ensure_ascii=False)
        words = set(re.findall(r'[A-Za-z_]{2,}', blob))
        assert not words, f'{b}: {sorted(words)[:20]}'


def test_breakdown_keys_read_as_chinese():
    assert zh._key('zhi.冲.month|午冲month支子') == '地支冲月·午冲月支子'
    assert zh._key('ten_god|丙对乙为伤官') == '十神·丙对乙为伤官'
    assert zh.model_view({'source': 'day支未藏丁', 'side': 'drain'}) == {'来源': '日支未藏丁', '方向': '克泄耗'}


def test_scrub_fixes_leaks_seen_in_audit():
    assert zh.scrub('〔午冲year支子〕') == '〔午冲年支子〕'
    assert zh.scrub('〔zhi.冲.year〕') == '〔地支冲年〕'
    assert zh.scrub('读数记 ten_god 为伤官') == '读数记 十神 为伤官'
    assert zh.scrub('〔current·stance〕') == '〔今年·定调〕'
    # 认不得的英文不动
    assert zh.scrub('deepseek 与 AI') == 'deepseek 与 AI'


def test_system_prompt_forbids_english_and_markdown():
    p = system_prompt('{}', [])
    assert '只说中文' in p and 'Markdown' in p
