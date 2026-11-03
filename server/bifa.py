"""《六壬大全》毕法赋原文。

数据来自 tianzhi-classics 的 `liuren/entries/liurendaquan-bifa.json`（四库全书本，据维基文库录文）。
百句赋文，各句之注从卷九、卷十切出。原文照录，未加今译——所以这里也不编今译。

tianzhi-core 给的 `bifa` 只有条号、诗句、我们自己的短规则；这里补的是那句注。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'classics' / 'liurendaquan-bifa.json'


@lru_cache(maxsize=1)
def _book() -> dict:
    if not DATA.exists():
        return {'items': []}
    return json.loads(DATA.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _index() -> dict[int, dict]:
    return {int(it['no']): it for it in (_book().get('items') or []) if 'no' in it}


def count() -> int:
    return len(_index())


def get(no: int) -> dict:
    it = _index().get(int(no))
    if not it:
        return {'found': False, 'reason': f'《毕法赋》没有第 {no} 条'}
    b = _book()
    commentary = it.get('commentary') or ''
    return {
        'found': True,
        'no': it.get('no'),
        'verse': it.get('verse'),
        'vol': it.get('vol'),
        'commentary': commentary,
        'no_commentary': not commentary,
        'book': b.get('book'),
        'edition': b.get('edition') or '',
        'note': b.get('note') or '',
        'source': 'tianzhi-classics · liuren/entries/liurendaquan-bifa.json',
    }
