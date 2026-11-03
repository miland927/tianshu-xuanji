"""《紫微斗数全书》卷二「十二宫逐星论断」原文。

数据来自 tianzhi-classics 的 `ziwei/entries/ziweiquanshu-gong.json`（289 条：宫 × 星）。
书里的宫名与现在通行叫法有两处不同：**妻妾**（今作夫妻）、**奴仆**（今作交友）。
这里做名目对照，不做改写——原文照录。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'classics' / 'ziweiquanshu-gong.json'

# 今名 → 书中原名
ALIAS = {'夫妻': '妻妾', '交友': '奴仆', '朋友': '奴仆'}


@lru_cache(maxsize=1)
def _book() -> dict:
    if not DATA.exists():
        return {'items': []}
    return json.loads(DATA.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _index() -> dict[tuple[str, str], dict]:
    out = {}
    for it in _book().get('items') or []:
        p, s = it.get('palace'), it.get('star')
        if p and s:
            out[(p, s)] = it
    return out


def count() -> int:
    return len(_index())


def palaces() -> list[str]:
    return sorted({p for p, _ in _index()})


def lookup(palace: str, star: str) -> dict:
    book_palace = ALIAS.get(palace, palace)
    it = _index().get((book_palace, star))
    if not it:
        return {'found': False,
                'reason': f'《紫微斗数全书》里没有「{book_palace}·{star}」这一条'}
    return {
        'found': True,
        'palace': it.get('palace'),
        'palace_alias': palace if palace != book_palace else '',
        'star': it.get('star'),
        'stars': it.get('stars') or [],
        'text': it.get('text') or '',
        'branches': it.get('branches') or [],
        'male': it.get('male') or '',
        'female': it.get('female') or '',
        'xian': it.get('xian') or '',
        'edition': (_book().get('edition') or ''),
        'source': 'tianzhi-classics · ziwei/entries/ziweiquanshu-gong.json',
    }


def lookup_any(palace: str, stars: list[str]) -> dict:
    """一宫可能有两颗主星；按给的次序取第一个查得到的。"""
    for s in stars or []:
        r = lookup(palace, s)
        if r['found']:
            return r
    names = '、'.join(stars or []) or '这些星'
    book = ALIAS.get(palace, palace)
    return {'found': False, 'reason': f'《全书》里没有「{book}」与「{names}」的组合'}
