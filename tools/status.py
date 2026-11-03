"""生成 STATUS.md：把「声称」和「怎么验的」绑在一起。

这里不做判断，只跑、只数、只写。凡是跑不起来的，就写「没跑」——不写成「通过」。

  .venv\\Scripts\\python.exe tools/status.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(args: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        p = subprocess.run([PY, *args], cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, '超时'


def first_match(pattern: str, text: str, default: str = '?') -> str:
    m = re.search(pattern, text)
    return m.group(1) if m else default


def main() -> int:
    checks: list[dict] = []

    rc, out = run(['-m', 'pytest', 'tests', '-q'])
    n = first_match(r'(\d+) passed', out)
    checks.append({'claim': '单元测试全过', 'how': '`pytest tests -q`',
                   'result': f'{n} passed' if rc == 0 else f'失败（rc={rc}）', 'ok': rc == 0})

    rc, out = run(['tools/golden.py', '--check'])
    m = first_match(r'比对 (\d+) 例', out)
    checks.append({'claim': '八字黄金集不漂', 'how': '`tools/golden.py --check`',
                   'result': f'{m} 例一致' if rc == 0 else f'漂移（rc={rc}）', 'ok': rc == 0})

    rc, out = run(['tools/golden_plates.py', '--check'])
    m = first_match(r'比对 (\d+) 条', out)
    checks.append({'claim': '六壬/奇门/紫微快照不漂', 'how': '`tools/golden_plates.py --check`',
                   'result': f'{m} 条一致' if rc == 0 else f'漂移（rc={rc}）', 'ok': rc == 0})

    rc, out = run(['tools/verify_privacy.py'])
    m = first_match(r'(\d+/\d+)', out)
    checks.append({'claim': '隐私承诺实测', 'how': '`tools/verify_privacy.py`（起真服务、读真文件）',
                   'result': f'{m} 通过' if rc == 0 else f'失败（rc={rc}）', 'ok': rc == 0})

    rc, out = run(['tools/api_smoke.py'])
    m = first_match(r'(\d+) 个例子，失败 (\d+)', out, '0')
    m2 = re.search(r'(\d+) 个例子，失败 (\d+)', out)
    ok = rc == 0 and m2 is not None
    checks.append({'claim': '文档里的接口例子能跑通',
                   'how': '`tools/api_smoke.py`（需要服务在跑）',
                   'result': f'{m2.group(1)} 个例子，失败 {m2.group(2)}' if ok else '没跑（服务未起或失败）',
                   'ok': ok})

    # 真模型跑过没有：看最新的 eval/p1-*.jsonl 是不是 mock
    real = None
    for f in sorted((ROOT / 'eval').glob('p1-*.jsonl')):
        rows = [json.loads(l) for l in f.read_text(encoding='utf-8').splitlines() if l.strip()]
        if rows and not rows[0].get('mock'):
            real = (f, rows)
    if real:
        f, rows = real
        rc3, out3 = run(['tools/recheck.py', str(f)])
        lat = sorted(r['ms'] for r in rows)
        p50 = lat[len(lat) // 2] if lat else 0
        checks.append({
            'claim': f'真模型 {len(rows)} 轮（守则 + 对账）',
            'how': f'`tools/eval_p1.py` → `tools/recheck.py {f.name}`',
            'result': ('通过：拦截 0、对账 0' if rc3 == 0 else '有拦截或对账不符')
                      + f'；p50 {p50:.0f}ms',
            'ok': rc3 == 0,
        })
    else:
        checks.append({'claim': '真模型对话', 'how': '`tools/eval_p1.py`（需 key）',
                       'result': '没跑（没有 key）', 'ok': False})

    # 盘面与接口的清单直接从代码里数，不靠记忆
    sys.path.insert(0, str(ROOT))
    from server.app import ROUTE_META  # noqa: E402

    pages = sorted(p.name for p in ROOT.glob('*.html'))
    data = sorted(p.name for p in (ROOT / 'data' / 'classics').glob('*.json'))

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    ok_all = all(c['ok'] for c in checks)

    lines = [
        '# STATUS：现在到底验了什么',
        '',
        f'自动生成于 {now}（`tools/status.py`）。**这张表不靠记忆，靠跑**——重跑一次就对得上。',
        '',
        f'一句话：离线可验的部分{"全过" if ok_all else "有失败"}；'
        f'{"真模型也跑过了（见下表）" if real else "**模型相关的部分一次都没真跑过**（没有 key）"}。',
        '',
        '## 已验证',
        '',
        '| 声称 | 怎么验的 | 结果 |',
        '|---|---|---|',
    ]
    for c in checks:
        mark = '✅' if c['ok'] else '⚠️'
        lines.append(f"| {c['claim']} | {c['how']} | {mark} {c['result']} |")

    unverified = [
        '| 备案与内容标识 | 这是行政流程 | 人来办 |',
        '| 法务复核 | 三份草案没请人看过 | 人来看 |',
        '| 真实流量下的限流/熔断/告警 | 只有本机几个请求 | 真实用户 |',
        '| 「算得对」的第三方校验 | 目前是与库、与 pymeeus/ephem 互相印证 | 有人来提勘误 |',
        '| 回答的「有用程度」 | 守则和对账只能查越界与说错，查不了好不好 | 人读，或者更大规模的对照 |',
    ]
    if not real:
        unverified.insert(0, '| 接真模型后的话风与守则 | 所有回答都是 mock 路径 | `DEEPSEEK_API_KEY` |')
        unverified.insert(1, '| 真实 token 成本 | 没有 usage 就没有账 | 同上 |')

    lines += [
        '',
        '## 未验证（不是忘了，是没法自己验）',
        '',
        '| 声称 | 为什么没验 | 需要什么 |',
        '|---|---|---|',
        *unverified,
        '',
        '## 现在有什么',
        '',
        f'- 页面 {len(pages)} 个：' + '、'.join(f'`{p}`' for p in pages),
        f'- 接口 {len(ROUTE_META)} 条（`/api/docs` 可试）',
        f'- 典籍数据 {len(data)} 份：' + '、'.join(f'`{d}`' for d in data),
        '',
        '## 怎么重跑',
        '',
        '```powershell',
        '.venv\\Scripts\\python.exe tools\\check.py        # 单元测试 + 两个黄金集 + 隐私',
        '.venv\\Scripts\\python.exe tools\\api_smoke.py    # 文档里的接口例子（需服务在跑）',
        '.venv\\Scripts\\python.exe tools\\status.py       # 重新生成本页',
        '```',
        '',
        '边界（写在接口文档与人设里，也写在这里）：这是传统文化研究与学习工具，'
        '不预测具体事件、不判定吉凶、不提供医疗/法律/投资建议。',
        '',
    ]

    (ROOT / 'STATUS.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'已写 STATUS.md（{sum(1 for c in checks if c["ok"])}/{len(checks)} 项通过）')
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main())
