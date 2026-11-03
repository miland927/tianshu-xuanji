"""用当前规则，把一份 eval jsonl 重新判一遍（不花 token）。

  .venv\\Scripts\\python.exe tools\\recheck.py eval/p1-xxx.jsonl

注意：**「此刻」类断言（比如当刻四柱）要用那次运行时的读数来判**，不能用现在的。
所以 eval_p1 会把每轮的 `now` 一起写进 jsonl；老文件没有这一段，四柱一项会被跳过并标注。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import claims  # noqa: E402
from server.cal import chart_snapshot  # noqa: E402
from server.guard import check  # noqa: E402

BIRTH = '1996-04-18 14:06'


def main() -> int:
    if len(sys.argv) < 2:
        print('用法：tools/recheck.py eval/p1-xxx.jsonl')
        return 2
    path = Path(sys.argv[1])
    chart = chart_snapshot(BIRTH, 114.93, 0)

    guard_hits: Counter = Counter()
    claim_hits: Counter = Counter()
    rows = 0
    legacy = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows += 1
        _, bad = check(r.get('text') or '')
        for v in bad:
            guard_hits[v['kind']] += 1

        now = r.get('now') or {}
        if now:
            truth = claims.truth(now, chart)
            skip: set[str] = set()
        else:
            legacy += 1
            truth = claims.truth({}, chart)
            # 没有当时的读数，「此刻」类的两项就无从判——跳过，并在上面标注
            skip = {'四柱', '节气'}

        for v in claims.verify(r.get('text') or '', truth):
            if v['kind'] in skip:
                continue
            claim_hits[v['kind']] += 1

    print(f'{rows} 条回答（{path.name}）')
    if legacy:
        print(f'  ⚠ {legacy} 条是旧格式（没记当时的读数），四柱一项已跳过——别把它当成「全查过」')
    print('  守则拦截：', dict(guard_hits) or '无')
    print('  对账不符：', dict(claim_hits) or '无')
    return 0 if not guard_hits and not claim_hits else 1


if __name__ == '__main__':
    raise SystemExit(main())
