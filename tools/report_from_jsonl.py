"""用当前规则，把一份 eval jsonl 重新判一遍并重出报告（不花 token）。

  .venv\\Scripts\\python.exe tools/report_from_jsonl.py eval/p1-20261103-093102.jsonl
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))

import eval_p1  # noqa: E402
from server import claims  # noqa: E402
from server.cal import chart_snapshot, now_snapshot  # noqa: E402
from server.guard import check  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print('用法：tools/report_from_jsonl.py eval/p1-xxx.jsonl')
        return 2
    src = Path(sys.argv[1])
    rows = [json.loads(l) for l in src.read_text(encoding='utf-8').splitlines() if l.strip()]
    truth = claims.truth(now_snapshot(114.93), chart_snapshot(eval_p1.BIRTH, 114.93, 0))

    by_cat = defaultdict(Counter)
    per_row, lat = [], []
    for r in rows:
        _, guard_bad = check(r.get('text') or '')
        claim_bad = claims.verify(r.get('text') or '', truth)
        by_cat[r['cat']].update(v['kind'] for v in guard_bad)
        by_cat['_claims'].update(v['kind'] for v in claim_bad)
        lat.append(r['ms'])
        per_row.append({'cat': r['cat'], 'prompt': r['prompt'], 'ms': r['ms'],
                        'guard': len(guard_bad), 'claims': len(claim_bad)})

    claim_total = sum(by_cat['_claims'].values())

    def pct(q: float) -> float:
        s = sorted(lat)
        return round(s[min(len(s) - 1, int(round(q * (len(s) - 1))))], 1) if s else 0.0

    out = src.with_suffix('.md')
    eval_p1.write_report(out, len(rows), False, by_cat, claim_total, per_row, pct, lat, src)
    guard_total = sum(sum(by_cat[c].values()) for c in
                      ['cite', 'medical', 'legal', 'finance', 'predict', 'scare'])
    print(f'{len(rows)} 条：拦截 {guard_total}、对账 {claim_total} → 重写 {out.name}')
    return 0 if guard_total == 0 and claim_total == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
