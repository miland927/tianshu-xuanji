"""《遁甲演义》原文：奇门的「格」能落到书里那一节。

数据来自 tianzhi-classics 的 `qimen/entries/dunjiayanyi.json`
（维基文库录文，四库全书本文渊阁；共 80 节）。

书里用旧字形（竒、隂、陽、擊、儀、網…），`_norm` 把两边都折到同一形再比，
所以「三奇得使」能对上书里的「三竒得使」，「六仪击刑」对上「六儀擊刑」。
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'classics' / 'dunjiayanyi.json'

TRAD = str.maketrans({
    '竒': '奇', '隂': '阴', '陽': '阳', '嵗': '岁', '螣': '腾', '蹻': '跷',
    '㸃': '点', '兊': '兑', '尅': '克', '夘': '卯', '佈': '布', '倂': '并',
    '擊': '击', '儀': '仪', '網': '网', '張': '张', '門': '门', '宫': '宫',
    '遯': '遁', '隠': '隐', '塲': '场', '昬': '昏', '寳': '宝', '竅': '窍',
    '鄰': '邻', '㐫': '凶', '兇': '凶', '衆': '众', '災': '灾', '䘮': '丧',
    '龍': '龙', '風': '风', '雲': '云', '馬': '马', '時': '时', '開': '开',
    '關': '关', '閉': '闭', '驚': '惊', '傷': '伤', '見': '见', '東': '东',
    '車': '车', '鳥': '鸟', '飛': '飞', '髙': '高', '並': '并', '呌': '叫',
})


def _norm(s: str) -> str:
    s = (s or '').translate(TRAD)
    s = re.sub(r'[（(][^）)]*[）)]', '', s)
    return re.sub(r'[\s·・.。，,]', '', s)


@lru_cache(maxsize=1)
def _book() -> dict:
    if not DATA.exists():
        return {'items': []}
    return json.loads(DATA.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _index() -> dict[str, dict]:
    out = {}
    for it in _book().get('items') or []:
        for name in (it.get('chapter'), (it.get('key') or '').split('|')[-1]):
            n = _norm(name)
            if n and n not in out:
                out[n] = it
    return out


def count() -> int:
    return len(_book().get('items') or [])


def lookup_cite(cite: str) -> dict:
    """按 tianzhi-core 给的 cite 取原文，形如「遁甲演義·卷二|小隔并嵗隔月隔日隔時隔」。

    格名与书里的篇名未必逐字相同（返首/回首、投江/入江、格/隔），
    所以以库自己给的 cite 为准，不靠格名去猜。
    """
    if not cite:
        return {'found': False, 'reason': '这一格没有给引用'}
    chapter = cite.split('|')[-1].strip()
    r = lookup(chapter)
    if r['found']:
        r['cite'] = cite
    return r


def lookup(name: str) -> dict:
    key = _norm(name)
    it = _index().get(key)
    if not it:
        # 书名偶有长短不一（「小隔并岁隔月隔日隔时隔」对「小隔」）；退一步找包含关系
        for k, v in _index().items():
            if key and (key in k or k in key):
                it = v
                break
    if not it:
        return {'found': False, 'reason': f'《遁甲演义》里没有「{name}」这一节'}
    return {
        'found': True,
        'chapter': it.get('chapter'),
        'vol': it.get('vol'),
        'key': it.get('key'),
        'text': it.get('text') or '',
        'title': _book().get('title') or '遁甲演義',
        'edition': _book().get('edition') or '',
        'source': 'tianzhi-classics · qimen/entries/dunjiayanyi.json',
    }
