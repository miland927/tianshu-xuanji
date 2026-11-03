"""看审计日志。

  .venv\\Scripts\\python.exe tools\\audit.py --tail 5
  .venv\\Scripts\\python.exe tools\\audit.py --id 004512-a1b2c3
  .venv\\Scripts\\python.exe tools\\audit.py --verify      # 结构自检 + 统计
  .venv\\Scripts\\python.exe tools\\audit.py --purge --days 30
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import audit  # noqa: E402

REQUIRED = ('ts', 'id', 'ms', 'status', 'in', 'out', 'req', 'ctx', 'versions', 'mock')


def records() -> list[dict]:
    if not audit.AUDIT_DIR.exists():
        return []
    out = []
    for p in sorted(audit.AUDIT_DIR.glob('*.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tail', type=int, default=0)
    ap.add_argument('--id', default='')
    ap.add_argument('--replay', action='store_true', help='按 --id 还原一条回答的完整上下文')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--purge', action='store_true')
    ap.add_argument('--days', type=int, default=audit.KEEP_DAYS)
    ap.add_argument('--full', action='store_true')
    args = ap.parse_args()

    if args.purge:
        gone = audit.purge(args.days)
        print(f'删了 {len(gone)} 个文件：{gone or "（没有超期的）"}')
        return 0

    recs = records()
    if not recs:
        print(f'{audit.AUDIT_DIR} 下没有记录')
        return 0

    if args.id:
        hit = [r for r in recs if r.get('id') == args.id]
        if not hit:
            print('没找到这条')
            return 1
        r = hit[0]
        if args.replay:
            d = (r.get('ctx') or {}).get('derived') or {}
            print(f"时间   {r['ts']}   记录 {r['id']}   耗时 {r['ms']} ms   状态 {r['status']}")
            print(f"问题   {r.get('in', '')}")
            print(f"版本   {r['versions']}")
            print(f"读数   {r['ctx'].get('jie')} 后 · 月建 {r['ctx'].get('month_zhi')} · 四柱 {r['ctx'].get('bazi') or '未报生辰'}")
            if d:
                print(f"真太阳 {d.get('true_solar')} · 司令 {d.get('siling')}")
                print(f"旺衰   {d['strength']['label']} {d['strength']['ratio']} · 格 {d.get('geju')} · 用 {d.get('yong')}（{d.get('method')}）")
                print(f"岁运   {d['current'].get('year')} · 大运 {d['current'].get('dayun')} · {d['current'].get('score')} 分")
                print('判据   ' + ' / '.join(d.get('evidence') or []))
            print(f"拦截   {r.get('violations') or '无'}")
            print('回答   ' + (r.get('out') or '').replace('\n', '\n       '))
            print(f"生辰   {r['req'].get('birth_day')} (hash {r['req'].get('birth_hash')}) · 经度 {r['req']['place'].get('longitude')}")
            return 0
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    if args.verify:
        bad = 0
        for r in recs:
            miss = [k for k in REQUIRED if k not in r]
            if miss:
                bad += 1
                print(f"缺字段 {r.get('id')}: {miss}")
            if not r.get('out'):
                bad += 1
                print(f"空回答 {r.get('id')}")
        st = Counter(r.get('status') for r in recs)
        hit = Counter(v['kind'] for r in recs for v in r.get('violations') or [])
        avg = sum(r.get('ms', 0) for r in recs) / len(recs)
        print(f'记录 {len(recs)} 条 · 结构问题 {bad} 处')
        print(f'  状态：{dict(st)}')
        print(f'  拦截：{dict(hit) or "无"}')
        print(f'  平均耗时：{avg:.0f} ms')
        print(f'  版本：{set(json.dumps(r["versions"], sort_keys=True) for r in recs[:1])}')
        return 0 if not bad else 1

    rows = recs[-args.tail:] if args.tail else recs
    for r in rows:
        warn = ','.join(r['ctx'].get('warnings') or [])
        print(f"{r['ts'][:19]} {r['id']} {r['ms']:>5}ms {r['status']:6s} "
              f"{'mock' if r['mock'] else 'live':4s} {r['ctx'].get('bazi') or '-':32s} "
              f"{'拦' + str(len(r['violations'])) if r.get('violations') else '  '} {warn}")
        if args.full:
            print('  问：', r['in'])
            print('  答：', (r['out'] or '')[:400].replace('\n', ' '))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
