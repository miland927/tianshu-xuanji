"""三块盘的回归快照：六壬、奇门、紫微。

黄金集管的是八字的四柱；这里管另外三门的关键结果——三传、局数、命宫与四化。
它同样只管「没变」，不管「对不对」；对不对由契约测试与人工核对负责。

  .venv\\Scripts\\python.exe tools/golden_plates.py --freeze
  .venv\\Scripts\\python.exe tools/golden_plates.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tianzhi_core import ziwei  # noqa: E402
from tianzhi_core.liuren import pan as liuren_pan  # noqa: E402
from tianzhi_core.qimen import qiju  # noqa: E402

GOLDEN = ROOT / 'eval' / 'plates-golden.jsonl'

# 每类取三个样本：一个常规、一个怪时辰、一个跨节气
LIUREN = [('2026-11-03 01:30', '子时'), ('2026-06-21 12:00', '夏至午时'), ('2025-12-21 23:40', '冬至夜子时')]
QIMEN = [('2026-11-03 15:00', '霜降后'), ('2026-02-04 04:30', '立春交节'), ('2026-07-23 09:00', '大暑')]
ZIWEI = [('1996-04-18 13:46', 0, '男'), ('1990-06-01 12:00', 1, '女'), ('2000-01-01 00:30', 0, '世纪跨年')]


def liuren_snapshot(at: str) -> dict:
    dt = datetime.strptime(at, '%Y-%m-%d %H:%M')
    k = liuren_pan.qike(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    t = k['three_chuan']
    return {
        'yue_jiang': k['yue_jiang'],
        'zhan_shi': k['zhan_shi'],
        'xun_kong': k['xun_kong'],
        'method': t['method'],
        'ge': t['ge'],
        'san_chuan': [t[x]['zhi'] for x in ('chu', 'zhong', 'mo')],
        'tian_di_pan': k['tian_di_pan'],
        'four_up': [c['up'] for c in k['four_classes']],
        'keti': [x['name'] for x in k['keti']],
    }


def qimen_snapshot(at: str) -> dict:
    dt = datetime.strptime(at, '%Y-%m-%d %H:%M')
    r = qiju(dt)
    ju, pan = r['ju'], r['pan']
    pal = pan['palaces']
    palaces = {}
    for g in range(1, 10):
        p = pal.get(g) or pal.get(str(g)) or {}
        palaces[str(g)] = list(p.get('di') or [])
    return {
        'jieqi': ju['jieqi'], 'yuan': ju['yuan'], 'dun': ju['dun'], 'ju': ju['ju'],
        'mode': ju['mode'],
        'zhifu': pan['zhifu'], 'zhishi': pan['zhishi'],
        'zhifu_gong': pan['zhifu_gong'], 'zhishi_gong': pan['zhishi_gong'],
        'kong': r['kong'], 'ma': r['ma'],
        'geju': sorted(x['name'] for x in r['geju']),
        'palaces': palaces,
    }


def ziwei_snapshot(birth: str, gender: int) -> dict:
    dt = datetime.strptime(birth, '%Y-%m-%d %H:%M')
    z = ziwei.build_chart(dt, gender)
    pal = {p['zhi']: p for p in z['palaces']}
    return {
        'ming': z['ming'], 'shen': z['shen'], 'ju_name': z['ju_name'],
        'ming_zhu': z['ming_zhu'], 'shen_zhu': z['shen_zhu'], 'forward': z['forward'],
        'palaces': {zhi: {'name': p['name'],
                          'mains': [s['name'] for s in p['stars'] if s['kind'] == 'main']}
                    for zhi, p in pal.items()},
        'sihua': sorted(f"{s['name']}{s['hua']}" for p in z['palaces'] for s in p['stars'] if s.get('hua')),
    }


def build() -> list[dict]:
    rows = []
    for at, note in LIUREN:
        rows.append({'plate': 'liuren', 'at': at, 'note': note, 'expect': liuren_snapshot(at)})
    for at, note in QIMEN:
        rows.append({'plate': 'qimen', 'at': at, 'note': note, 'expect': qimen_snapshot(at)})
    for birth, gender, note in ZIWEI:
        rows.append({'plate': 'ziwei', 'birth': birth, 'gender': gender, 'note': note,
                     'expect': ziwei_snapshot(birth, gender)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--freeze', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    if args.freeze:
        GOLDEN.parent.mkdir(exist_ok=True)
        rows = build()
        with GOLDEN.open('w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(f'已冻结 {len(rows)} 条 → {GOLDEN}')
        return 0

    if not GOLDEN.exists():
        print('还没有 plates-golden.jsonl，先跑 --freeze')
        return 1

    drift = 0
    for line in GOLDEN.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec['plate'] == 'liuren':
            got = liuren_snapshot(rec['at'])
        elif rec['plate'] == 'qimen':
            got = qimen_snapshot(rec['at'])
        else:
            got = ziwei_snapshot(rec['birth'], rec['gender'])
        for k, want in rec['expect'].items():
            if got.get(k) != want:
                drift += 1
                print(f"漂移 {rec['plate']} {rec.get('at') or rec.get('birth')} . {k}")
                print(f"  期望 {json.dumps(want, ensure_ascii=False)[:120]}")
                print(f"  实得 {json.dumps(got.get(k), ensure_ascii=False)[:120]}")
    total = len([l for l in GOLDEN.read_text(encoding='utf-8').splitlines() if l.strip()])
    print(f'比对 {total} 条（六壬/奇门/紫微）：{"全部一致" if not drift else f"{drift} 处漂移"}')
    return 0 if not drift else 1


if __name__ == '__main__':
    raise SystemExit(main())
