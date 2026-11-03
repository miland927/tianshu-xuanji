"""勘误命令行。

  .venv\\Scripts\\python.exe tools/corrections.py list
  .venv\\Scripts\\python.exe tools/corrections.py add --kind calc --target /api/year \
      --claim "立春交节时刻差了 2 分钟" --evidence "pymeeus 独立算出 04:04:11" --credit "某网友"
  .venv\\Scripts\\python.exe tools/corrections.py decide c-0001 --status accepted \
      --decision "已复核：改用 TT 转 UT" --credit "@someone"
  .venv\\Scripts\\python.exe tools/corrections.py check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import corrections as corr  # noqa: E402


def cmd_list(args) -> int:
    rows = corr.load()
    if not rows:
        print('台账是空的。')
        print('空不是「没问题」，是「还没有第三方校验过」——这份台账存在的意义就是把它变空为满。')
        return 0
    for r in rows:
        mark = {'open': '○', 'accepted': '✓', 'rejected': '✕', 'unclear': '?'}[r['status']]
        print(f"{mark} {r['id']} {r['at']} [{r['kind']}] {r['target']}")
        print(f"   {r['claim']}")
        print(f"   证据：{r['evidence']}")
        if r.get('decision'):
            print(f"   结论：{r['decision']}")
        if r.get('credit'):
            print(f"   署名：{r['credit']}")
    print(f"\n共 {len(rows)} 条，状态 {corr.counts()}")
    return 0


def cmd_add(args) -> int:
    try:
        rec = corr.add(args.kind, args.target, args.claim, args.evidence, args.credit)
    except ValueError as e:
        print(f'不合法：{e}')
        return 2
    print(f"已记 {rec['id']}：{rec['claim']}")
    return 0


def cmd_decide(args) -> int:
    rows = corr.load()
    hit = next((r for r in rows if r['id'] == args.id), None)
    if not hit:
        print(f'没有 {args.id}')
        return 2
    if args.status not in corr.STATUSES:
        print(f'status 只能是 {corr.STATUSES}')
        return 2
    hit['status'] = args.status
    hit['decision'] = args.decision
    if args.credit:
        hit['credit'] = args.credit
    corr.LEDGER.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n',
                           encoding='utf-8')
    print(f"{args.id} → {args.status}")
    return 0


def cmd_check(args) -> int:
    bad = 0
    for r in corr.load():
        errs = corr.validate(r)
        if errs:
            bad += 1
            print(f"✕ {r.get('id', '?')}: {'；'.join(errs)}")
    print(f'校验 {len(corr.load())} 条，问题 {bad} 条')
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('list')
    a = sub.add_parser('add')
    a.add_argument('--kind', required=True, choices=corr.KINDS)
    a.add_argument('--target', required=True)
    a.add_argument('--claim', required=True)
    a.add_argument('--evidence', required=True)
    a.add_argument('--credit', default='')
    d = sub.add_parser('decide')
    d.add_argument('id')
    d.add_argument('--status', required=True, choices=corr.STATUSES)
    d.add_argument('--decision', required=True)
    d.add_argument('--credit', default='')
    sub.add_parser('check')

    args = ap.parse_args()
    return {'list': cmd_list, 'add': cmd_add, 'decide': cmd_decide, 'check': cmd_check}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
