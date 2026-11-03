"""把一份 eval jsonl 用当前的规则重新判一遍，不花 token。

改了守则或对账规则之后，用它看「旧回答在新规则下是什么结果」。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import claims  # noqa: E402
from server.cal import chart_snapshot, now_snapshot  # noqa: E402
from server.guard import check  # noqa: E402

BIRTH = '1996-04-18 14:06'


def main() -> int:
    if len(sys.argv) < 2:
        print('用法：tools/recheck.py eval/p1-xxx.jsonl')
        return 2
    path = Path(sys.argv[1])
    truth = claims.truth(now_snapshot(114.93), chart_snapshot(BIRTH, 114.93, 0))

    guard_hits: Counter = Counter()
    claim_hits: Counter = Counter()
    rows = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows += 1
        _, bad = check(r.get('text') or '')
        for v in bad:
            guard_hits[v['kind']] += 1
        for v in claims.verify(r.get('text') or '', truth):
            claim_hits[v['kind']] += 1

    print(f'{rows} 条回答（{path.name}）')
    print('  守则拦截：', dict(guard_hits) or '无')
    print('  对账不符：', dict(claim_hits) or '无')
    return 0 if not guard_hits and not claim_hits else 1


if __name__ == '__main__':
    raise SystemExit(main())
