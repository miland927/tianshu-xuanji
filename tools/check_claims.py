"""对账命令行：拿一段话（或一个 eval jsonl），核对里面的事实断言。

  .venv\\Scripts\\python.exe tools/check_claims.py --text "此刻霜降，四柱 丙午 戊戌 辛巳 戊子"
  .venv\\Scripts\\python.exe tools/check_claims.py --jsonl eval/p1-xxxx.jsonl
  .venv\\Scripts\\python.exe tools/check_claims.py --self      # 用几条假话自检
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import claims  # noqa: E402
from server.cal import chart_snapshot, now_snapshot  # noqa: E402

FALLBACK = ('月建戌，寒露后二十五日。盘：丙子 壬辰 乙酉 癸未；旺衰 中和（0.4525）；用 土。',
            '盘：丙子 壬辰 乙酉 癸未；旺衰 偏旺；用 火。')


def build_truth(birth: str | None):
    chart = chart_snapshot(birth, 114.93, 0) if birth else None
    return claims.truth(now_snapshot(114.93), chart)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--text')
    ap.add_argument('--jsonl')
    ap.add_argument('--birth', default='1996-04-18 14:06')
    ap.add_argument('--self', action='store_true')
    args = ap.parse_args()

    t = build_truth(None if args.text and not args.jsonl and '四柱' not in args.text else args.birth)

    if args.self:
        for text, expect in ((FALLBACK[0], 0), (FALLBACK[1], 2)):
            bad = claims.verify(text, t)
            ok = len(bad) == expect
            print(f'{"PASS" if ok else "FAIL"}  期望 {expect} 处不一致，实得 {len(bad)}：{text[:28]}…')
            for b in bad:
                print('       ', b)
        return 0

    if args.text:
        bad = claims.verify(args.text, t)
        print(json.dumps(bad, ensure_ascii=False, indent=1) if bad else '对账通过：这段话里能查的都查了')
        return 0 if not bad else 1

    if args.jsonl:
        rows = [json.loads(l) for l in Path(args.jsonl).read_text(encoding='utf-8').splitlines() if l.strip()]
        total = 0
        for r in rows:
            bad = claims.verify(r.get('text', ''), t)
            if bad:
                total += len(bad)
                print(f"{r.get('cat', '?'):8s} {r.get('prompt', '')[:24]:24s} {bad}")
        print(f'\n{len(rows)} 条回答，共 {total} 处与库不符')
        return 0 if total == 0 else 1

    ap.print_help()
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
