"""照着文档接一遍：把 API.md 里的例子真跑一次。

  .venv\\Scripts\\python.exe tools/api_smoke.py                 # 打一份结果表
  .venv\\Scripts\\python.exe tools/api_smoke.py --json out.json # 顺便落盘摘要

每个例子都断言状态码与关键字段；SSE 单独读一轮事件。
它跑的是「文档里写的东西」，所以文档一旦说谎，这里会红。
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

BASE = 'http://127.0.0.1:8788'
BIRTH = '1996-04-18 14:06'


def get(c: httpx.Client, path: str, **params):
    r = c.get(BASE + path, params=params)
    r.raise_for_status()
    return r.json()


def chat_once(c: httpx.Client) -> dict:
    body = {'messages': [{'role': 'user', 'content': '此刻什么节气？'}], 'birth': BIRTH, 'gender': 0,
            'place': {'longitude': 114.93, 'latitude': 30.59, 'standard_longitude': 120.0}}
    events: list[tuple[str, dict]] = []
    with c.stream('POST', BASE + '/api/chat', json=body, timeout=60) as r:
        r.raise_for_status()
        ev = None
        for line in r.iter_lines():
            if line.startswith('event: '):
                ev = line[7:].strip()
            elif line.startswith('data: '):
                events.append((ev, json.loads(line[6:])))
    kinds = [e for e, _ in events]
    text = ''.join(d.get('text', '') for e, d in events if e == 'delta')
    return {'events': kinds, 'chars': len(text), 'first': text[:24],
            'meta_keys': sorted((events[0][1] if events else {}).keys())}


CASES = [
    ('读数', '/api/now', {'longitude': 114.93}, ('term', 'bazi', 'moon', 'sidereal')),
    ('读数', '/api/calendar', {'year': 2026}, ('year', 'terms')),
    ('读数', '/api/moon-calendar', {'year': 2026}, ('year', 'events')),
    ('盘', '/api/chart', {'birth': BIRTH, 'longitude': 114.93, 'gender': 0}, ('bazi', 'strength', 'yongshen', 'dayun')),
    ('盘', '/api/liuren', {'at': '2026-11-03 01:30'}, ('yue_jiang', 'three_chuan', 'four_classes')),
    ('盘', '/api/qimen', {'at': '2026-11-03 15:00'}, ('ju', 'pan', 'geju')),
    ('盘', '/api/ziwei', {'birth': BIRTH, 'gender': 0}, ('ming', 'palaces', 'ju_name')),
    ('报告', '/api/year', {'birth': BIRTH, 'year': 2026}, ('year_gz', 'months', 'score')),
    ('报告', '/api/ziwei/year', {'birth': BIRTH, 'year': 2026}, ('age', 'daxian', 'sihua')),
    ('原文', '/api/passage', {'cite': '穷通宝鉴·乙日辰月'}, ('found', 'quote', 'gloss')),
    ('原文', '/api/liuren/bifa', {'no': 52}, ('verse', 'commentary')),
    ('原文', '/api/ziwei/passage', {'palace': '命宫', 'stars': '紫微'}, ('text', 'stars')),
    ('原文', '/api/qimen/passage', {'cite': '遁甲演義·卷二|青龍回首'}, ('chapter', 'text')),
    ('运维', '/api/health', {}, ('ok', 'mock')),
    ('运维', '/api/metrics', {}, ('routes', 'events')),
    ('运维', '/api/alerts', {}, ('ok', 'alerts')),
    ('目录', '/api', {}, ('version', 'endpoints')),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    rows, failed = [], 0
    t_all = time.perf_counter()
    with httpx.Client(timeout=30) as c:
        for group, path, params, want in CASES:
            t0 = time.perf_counter()
            try:
                d = get(c, path, **params)
                missing = [k for k in want if k not in d]
                ms = (time.perf_counter() - t0) * 1000
                ok = not missing
                rows.append({'group': group, 'path': path, 'params': params, 'ok': ok,
                             'ms': round(ms, 1), 'missing': missing})
                if not ok:
                    failed += 1
                print(f"{'PASS' if ok else 'FAIL'}  {group:4s} {path:22s} {ms:6.0f}ms"
                      + ('' if ok else f"  缺 {missing}"))
            except Exception as e:
                failed += 1
                rows.append({'group': group, 'path': path, 'params': params, 'ok': False,
                             'error': f'{type(e).__name__}: {e}'})
                print(f'FAIL  {group:4s} {path:22s} {type(e).__name__}: {e}')

        try:
            ch = chat_once(c)
            ok = 'meta' in ch['events'] and 'delta' in ch['events'] and ch['chars'] > 0
            rows.append({'group': '璇玑', 'path': '/api/chat', 'ok': ok, 'events': ch['events'][:4],
                         'chars': ch['chars']})
            print(f"{'PASS' if ok else 'FAIL'}  璇玑 /api/chat            事件 {ch['events'][:3]}… {ch['chars']} 字")
            failed += 0 if ok else 1
        except Exception as e:
            failed += 1
            print(f'FAIL  璇玑 /api/chat            {type(e).__name__}: {e}')

    total_ms = (time.perf_counter() - t_all) * 1000
    print(f'\n{len(rows)} 个例子，失败 {failed}，合计 {total_ms:.0f}ms')
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump({'rows': rows, 'failed': failed, 'total_ms': round(total_ms, 1)},
                      f, ensure_ascii=False, indent=1)
        print(f'落盘：{args.json}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
