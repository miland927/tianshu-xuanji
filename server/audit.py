"""审计：每一次回答都留一条能回溯的记录。

为什么要有：出了事（用户投诉、算法改了、模型换了）要能回答「当时是怎么算的、谁说的」。
所以这条记录必须包含三样：输入、当次的读数快照、以及版本三元组。

隐私：出生时间是敏感个人信息。默认**不存原值**——存掩码（只到日）+ 一个短哈希，
真要复现时用读数快照里的四柱与字段即可；需要开发期对照可设 AUDIT_STORE_BIRTH=1。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = Path(os.environ.get('AUDIT_DIR', ROOT / 'audit'))
STORE_BIRTH = os.environ.get('AUDIT_STORE_BIRTH') == '1'
KEEP_DAYS = int(os.environ.get('AUDIT_KEEP_DAYS', '30'))


def _digest(payload: str, n: int = 8) -> str:
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:n]


def versions() -> dict:
    """版本三元组 + 历法实现。任一变动，历史回答的解释力就变了，所以都记。"""
    from importlib.metadata import version as pkg_version

    from . import cal, guard, persona

    prompt = persona.PERSONA + persona.RULES
    rules = Path(guard.__file__).read_text(encoding='utf-8')
    return {
        'core': _safe_version(pkg_version, 'tianzhi-core'),
        'model': os.environ.get('TIANZHI_MODEL', 'deepseek-chat'),
        'prompt': _digest(prompt),
        'rules': _digest(rules),
        'cal': _digest(Path(cal.__file__).read_text(encoding='utf-8')),
    }


def _safe_version(fn, name: str) -> str:
    try:
        return fn(name)
    except Exception:
        return 'unknown'


def mask_birth(birth: str | None) -> dict:
    """不外传原值：只留日期与一个短哈希，能对上号，不能反推。"""
    if not birth:
        return {}
    b = birth.strip().replace('T', ' ')
    day = b.split(' ')[0]
    return {
        'birth_hash': _digest(b),
        'birth_day': day,
        **({'birth': b} if STORE_BIRTH else {}),
    }


def new_id() -> str:
    return datetime.now().strftime('%H%M%S') + '-' + secrets.token_hex(3)


# 用户可能在问题里直接写出生时间。日志不该原样留着。
_TIME_PAT = [
    re.compile(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s*\d{1,2}[:：时]\d{2}(?:分)?'),
    re.compile(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}'),
]
_MASK = '〔已隐去〕'


def scrub(text: str, secrets: list[str | None] = (), generic: bool = True) -> str:
    """把可能出现的生辰从要落盘的文本里抹掉。

    两层：一是调用方明确给的生辰原值，二是常见的日期时间写法。
    `generic=False` 时只抹明确给的那几段——回答里本来就会出现节气时刻，
    那些是历法事实，不该被一起抹掉。
    """
    if not text:
        return text
    out = str(text)
    for s in secrets:
        if s and len(str(s).strip()) >= 8:
            out = out.replace(str(s).strip(), _MASK)
            # 'YYYY-MM-DD HH:MM' 与 'YYYY-MM-DDTHH:MM' 两种写法都抹
            out = out.replace(str(s).strip().replace(' ', 'T'), _MASK)
    if generic:
        for pat in _TIME_PAT:
            out = pat.sub(_MASK, out)
    return out


def _path() -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"


def write(record: dict) -> str:
    record = {'ts': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'versions': versions(), **record}
    with _path().open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return record.get('id', '')


def purge(days: int = KEEP_DAYS) -> list[str]:
    """删掉超过保留期的审计文件。"""
    if not AUDIT_DIR.exists():
        return []
    cutoff = time.time() - days * 86400
    gone = []
    for p in sorted(AUDIT_DIR.glob('*.jsonl')):
        if p.stat().st_mtime < cutoff:
            p.unlink()
            gone.append(p.name)
    return gone
