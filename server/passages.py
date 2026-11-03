"""出处原文：把「穷通宝鉴·乙日辰月」这类引用，落到典籍数据集里的那一条。

数据来自 tianzhi-classics（MIT）的 `bazi/entries/*.json`，vendored 在 `data/classics/`。
每条含原文、今译（该项目作者所撰，非原书）、以及「原文取用 vs 数据取用」的核对结论。

只做查表，不解释。查不到就如实说查不到，不给可能失效的外链。
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'classics'

GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'

VERDICT = {
    'agree': '原文与数据一致',
    'data_ok': '数据多出的字另有依据',
    'text_wins': '当以原文为准',
    'suspect': '存疑待核',
}

# 简体 → 繁体：只覆盖章节名里会碰到的字，够用就好
TRAD = str.maketrans({
    '论': '論', '诂': '詁', '说': '說', '类': '類', '杀': '殺', '财': '財', '伤': '傷',
    '药': '藥', '气': '氣', '体': '體', '性': '性', '情': '情', '阴': '陰', '阳': '陽',
    '经': '經', '传': '傳', '纲': '綱', '领': '領', '从': '從', '变': '變', '权': '權',
})


def _norm(s: str) -> str:
    return (s or '').translate(TRAD).replace(' ', '')


@lru_cache(maxsize=8)
def _load(name: str) -> dict:
    p = DATA / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding='utf-8'))


@lru_cache(maxsize=8)
def _chapters(name: str) -> list[dict]:
    d = _load(name)
    entries = d.get('entries') if isinstance(d, dict) else d
    if isinstance(entries, dict):
        return [v for v in entries.values() if isinstance(v, dict)]
    return [v for v in (entries or []) if isinstance(v, dict)]


def _chapter_hit(name: str, title: str, cite: str, chapter: str) -> dict:
    want = _norm(chapter)
    for e in _chapters(name):
        ch = _norm(e.get('chapter') or e.get('anchor') or '')
        if ch == want or ch.startswith(want) or want.startswith(ch):
            return {
                'found': True, 'cite': cite, 'title': title,
                'loc': e.get('chapter'), 'anchor': e.get('anchor'),
                'quote': e.get('quote') or '', 'quote_source': e.get('quote_source') or title,
                'gloss': e.get('gloss') or '', 'gloss_by': e.get('gloss_by') or '',
                'note': e.get('note') or '', 'verdict': '', 'verdict_text': '',
                'source': f'tianzhi-classics · bazi/entries/{name}',
            }
    return {'found': False, 'reason': f'《{title}》里没有「{chapter}」这一篇'}


CITE_RE = re.compile(
    r'(?:穷通宝鉴|窮通寶鑑)\s*[·・.]\s*(?P<gz>[%s]日[%s]月)'
    % (GAN, ZHI)
    + r'|子平真[诠詮]\s*[·・.]\s*(?P<zp>[^\s·，,。；;]+)'
    + r'|神[峰峯]通考\s*[·・.]\s*(?P<sf>[^\s·，,。；;]+)'
    + r'|金不换\s*(?P<jb>[喜忌])\s*[·・.]\s*[%s]' % GAN
)


def lookup(text: str) -> dict:
    """从一段话里找出引用，返回那一条原文。找不到就 found=False。"""
    m = CITE_RE.search(text or '')
    if not m:
        return {'found': False, 'reason': '这段话里没有可查的典籍引用'}

    if m.group('gz'):
        gz = m.group('gz')
        gan, zhi = gz[0], gz[2]
        entry = ((_load('qiongtong.json').get('entries') or {}).get(gan) or {}).get(zhi)
        if not entry:
            return {'found': False, 'reason': f'数据集里没有「{gan}日{zhi}月」这一条'}
        return {
            'found': True, 'cite': f'穷通宝鉴·{gz}',
            'title': (_load('qiongtong.json').get('meta') or {}).get('title', '窮通寶鑑'),
            'loc': entry.get('loc'), 'anchor': entry.get('anchor'),
            'quote': entry.get('quote'), 'quote_source': entry.get('quote_source'),
            'gloss': entry.get('gloss'), 'gloss_by': entry.get('gloss_by'),
            'verdict': entry.get('verdict'), 'verdict_text': VERDICT.get(entry.get('verdict'), ''),
            'note': entry.get('note') or '',
            'source': 'tianzhi-classics · bazi/entries/qiongtong.json',
        }

    if m.group('zp'):
        return _chapter_hit('ziping.json', '子平真詮', m.group(0), m.group('zp'))

    if m.group('sf'):
        return _chapter_hit('shenfeng.json', '神峰通考', m.group(0), m.group('sf'))

    if m.group('jb'):
        return {'found': False,
                'reason': '《金不换》按「日干 × 月支」查表，这句只给了喜忌的字，定位不到是哪一格'}

    return {'found': False, 'reason': '这段话里没有可查的典籍引用'}


def books() -> list[str]:
    return ['窮通寶鑑', '子平真詮', '神峰通考']
