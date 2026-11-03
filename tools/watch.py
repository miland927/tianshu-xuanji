"""盯一眼：轮询 /api/alerts，有新告警就打印。

  .venv\\Scripts\\python.exe tools/watch.py --base http://127.0.0.1:8788 --interval 5
  .venv\\Scripts\\python.exe tools/watch.py --once        # 看一次就退，有 error 则退出码 1

不做常驻守护进程——它不该替人做决定，只负责把该看的推到你眼前。
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import httpx


def fmt(a: dict) -> str:
    icon = {'error': '✕', 'warn': '!', 'info': '·'}.get(a.get('level'), '?')
    return f"{icon} [{a.get('level')}] {a.get('code')}: {a.get('detail')}"


def poll(base: str, token: str | None) -> dict:
    q = f'?token={token}' if token else ''
    with httpx.Client(timeout=10) as c:
        r = c.get(f'{base}/api/alerts{q}')
        r.raise_for_status()
        return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8788')
    ap.add_argument('--interval', type=float, default=15)
    ap.add_argument('--token', default=None)
    ap.add_argument('--once', action='store_true')
    args = ap.parse_args()

    seen: set[str] = set()
    while True:
        try:
            d = poll(args.base, args.token)
        except Exception as e:
            print(f'✕ 取不到告警：{type(e).__name__}: {e}')
            if args.once:
                return 2
            time.sleep(args.interval)
            continue

        fresh = [a for a in d['alerts'] if a.get('code') not in seen]
        for a in fresh:
            print(fmt(a))
        if args.once:
            print(f"\n请求 {d['total']} 次，5xx {d['errors']} 次（{d['error_rate']:.1%}）；"
                  f"{'有 error 级告警' if not d['ok'] else '没有 error 级告警'}")
            return 0 if d['ok'] else 1
        if not fresh:
            print(f'… {time.strftime("%H:%M:%S")} 无新告警（{len(d["alerts"])} 条旧的）')
        seen.update(a.get('code') for a in d['alerts'])
        time.sleep(args.interval)


if __name__ == '__main__':
    raise SystemExit(main())
