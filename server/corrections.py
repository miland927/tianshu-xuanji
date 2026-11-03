"""勘误台账。

一条勘误是一行 JSON；这里只做读写与校验，不做判定——判定是人写的，写在 `decision` 里。
台账本身放在 `eval/corrections.jsonl`，进版本库，公开可查。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / 'eval' / 'corrections.jsonl'

KINDS = ('calc', 'cite', 'wording', 'other')
STATUSES = ('open', 'accepted', 'rejected', 'unclear')
REQUIRED = ('id', 'at', 'kind', 'target', 'claim', 'evidence', 'status')


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d')


def load() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding='utf-8').splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def validate(rec: dict) -> list[str]:
    bad = []
    for k in REQUIRED:
        if not rec.get(k):
            bad.append(f'缺 {k}')
    if rec.get('kind') and rec['kind'] not in KINDS:
        bad.append(f'kind 只能是 {KINDS}')
    if rec.get('status') and rec['status'] not in STATUSES:
        bad.append(f'status 只能是 {STATUSES}')
    return bad


def add(kind: str, target: str, claim: str, evidence: str, credit: str = '') -> dict:
    rows = load()
    rec = {
        'id': f'c-{len(rows) + 1:04d}',
        'at': _now(),
        'kind': kind,
        'target': target,
        'claim': claim,
        'evidence': evidence,
        'status': 'open',
        'decision': '',
        'credit': credit,
    }
    bad = validate(rec)
    if bad:
        raise ValueError('；'.join(bad))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return rec


def counts() -> dict:
    out = {s: 0 for s in STATUSES}
    for r in load():
        out[r.get('status', 'open')] = out.get(r.get('status', 'open'), 0) + 1
    return out
