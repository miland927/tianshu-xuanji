"""隐私删除的实测：把隐私政策上的承诺逐条验一遍。

不是「代码里有这个函数所以它应该成立」，而是起一个真服务、发真请求、
读真文件，再把文件删掉看还能不能翻出来。

跑：.venv\\Scripts\\python.exe tools\\verify_privacy.py
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from tempfile import mkdtemp

ROOT = Path(__file__).resolve().parent.parent
VENV = Path(r'D:\Dev\tianzhi\.venv\Scripts\python.exe')
BIRTH = '1996-04-18 14:06'
QUESTION = '我 1996-04-18 14:06 出生，帮我看看这个盘'


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_health(base: str, timeout: float = 30.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f'{base}/api/health', timeout=2).read()
            return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError('服务没起来')


def chat(base: str) -> str:
    body = json.dumps({'messages': [{'role': 'user', 'content': QUESTION}],
                       'birth': BIRTH, 'place': {'longitude': 114.93}}).encode()
    req = urllib.request.Request(f'{base}/api/chat', data=body,
                                 headers={'content-type': 'application/json'})
    return urllib.request.urlopen(req, timeout=60).read().decode('utf-8')


def main() -> int:
    tmp = Path(mkdtemp(prefix='cw-privacy-'))
    port = free_port()
    base = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'AUDIT_DIR': str(tmp), 'PYTHONIOENCODING': 'utf-8'}
    env.pop('DEEPSEEK_API_KEY', None)

    proc = subprocess.Popen(
        [str(VENV), '-m', 'uvicorn', 'server.app:app', '--host', '127.0.0.1', '--port', str(port)],
        cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    checks: list[tuple[str, bool, str]] = []
    try:
        wait_health(base)
        chat(base)
        files = sorted(tmp.glob('*.jsonl'))
        raw = files[0].read_text(encoding='utf-8') if files else ''

        checks.append(('写了审计文件', bool(files), str(files[0].name if files else '无')))
        checks.append(('不含出生时刻 14:06', '14:06' not in raw, raw.count('14:06')))
        checks.append(('不含完整生辰', BIRTH not in raw, ''))
        checks.append(('问题里的时间被抹掉', '〔已隐去〕' in raw, ''))
        checks.append(('保留到日（政策明说）', '1996-04-18' in raw, ''))
        rec = json.loads(raw.splitlines()[0]) if raw else {}
        checks.append(('只存 8 位哈希', len(rec.get('req', {}).get('birth_hash', '')) == 8,
                       rec.get('req', {}).get('birth_hash', '')))
        checks.append(('无 birth 原文键', 'birth' not in rec.get('req', {}), ''))
        checks.append(('派生量可解释结论', bool(rec.get('ctx', {}).get('derived', {}).get('evidence')), ''))

        # 删除：整个目录清空
        subprocess.run([str(VENV), str(ROOT / 'tools' / 'audit.py'), '--purge', '--days', '0'],
                       cwd=str(ROOT), env=env, check=True, capture_output=True)
        left = sorted(tmp.glob('*.jsonl'))
        checks.append(('purge 之后无残留', not left, f'{len(left)} 个文件'))

        # 删完之后还能正常写新记录（说明不是把日志功能整个关掉）
        chat(base)
        after = sorted(tmp.glob('*.jsonl'))
        checks.append(('删除后新记录照常写', len(after) == 1, f'{len(after)} 个文件'))
        checks.append(('新记录也不含生辰', all('14:06' not in p.read_text(encoding='utf-8') for p in after), ''))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    width = max(len(c[0]) for c in checks)
    for name, ok, note in checks:
        print(f'{"PASS" if ok else "FAIL"}  {name:<{width}}  {note}')
    bad = [c for c in checks if not c[1]]
    if bad:
        print('临时目录留着供排查：', tmp)   # 有失败就别删，方便看现场
    else:
        shutil.rmtree(tmp, ignore_errors=True)
        print('临时目录已清理')
    print(f'\n{len(checks) - len(bad)}/{len(checks)} 通过')
    return 0 if not bad else 1


if __name__ == '__main__':
    raise SystemExit(main())
