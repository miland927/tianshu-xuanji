"""一条命令看这套东西还正不正常。

  .venv\\Scripts\\python.exe tools\\check.py          # 快检（约 10 秒）
  .venv\\Scripts\\python.exe tools\\check.py --slow   # 加上节气对表（约 3 分钟）

不做的事：不修东西。它只回答「现在能不能信」。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(name: str, args: list[str]) -> tuple[str, bool, str]:
    p = subprocess.run([PY, *args], cwd=str(ROOT), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    lines = [l for l in (p.stdout or '').strip().splitlines() if l.strip()]
    note = (lines[-1] if lines else (p.stderr or '')).strip()[:110]
    return name, p.returncode == 0, note


def main() -> int:
    slow = '--slow' in sys.argv
    checks = [
        ('单元测试', ['-m', 'pytest', 'tests', '-q']),
        ('八字黄金集不漂', ['tools/golden.py', '--check']),
        ('三盘快照不漂', ['tools/golden_plates.py', '--check']),
        ('隐私承诺实测', ['tools/verify_privacy.py']),
    ]
    if slow:
        checks.append(('节气对表（624 点）', ['tools/verify_calendar.py', '--from', '2010', '--to', '2035']))

    results = [run(n, a) for n, a in checks]
    width = max(len(r[0]) for r in results)
    for name, ok, note in results:
        print(f'{"PASS" if ok else "FAIL"}  {name:<{width}}  {note}')
    bad = [r for r in results if not r[1]]
    print(f'\n{len(results) - len(bad)}/{len(results)} 通过')
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
