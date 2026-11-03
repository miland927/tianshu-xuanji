"""接 key 之后的第一件事：验 key，不打印 key。

  $env:DEEPSEEK_API_KEY = 'sk-...'
  .venv\\Scripts\\python.exe tools\\preflight.py

做三件事：
1. 看环境变量在不在（只显示掩码）
2. 真发一次最小的请求（max_tokens=1），确认 key 与网络都通
3. 看返回里有没有 usage（成本账要靠它）
"""
from __future__ import annotations

import json
import os
import sys

import httpx

BASE = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
MODEL = os.environ.get('TIANZHI_MODEL', 'deepseek-chat')


def mask(key: str | None) -> str:
    if not key:
        return '（未设置）'
    if len(key) <= 8:
        return key[0] + '***'
    return f'{key[:4]}…{key[-4:]}（{len(key)} 字符）'


def main() -> int:
    key = os.environ.get('DEEPSEEK_API_KEY', '')
    print(f'key      : {mask(key)}')
    print(f'base_url : {BASE}')
    print(f'model    : {MODEL}')

    if not key:
        print('\n没有 key。先设置，再重跑：')
        print("  $env:DEEPSEEK_API_KEY = 'sk-...'")
        return 2

    body = {'model': MODEL, 'stream': False, 'max_tokens': 1, 'temperature': 0,
            'messages': [{'role': 'user', 'content': 'ping'}]}
    try:
        r = httpx.post(f'{BASE}/chat/completions', json=body, timeout=30,
                       headers={'Authorization': f'Bearer {key}'})
    except Exception as e:
        print(f'\n连不上：{type(e).__name__}: {e}')
        return 3

    if r.status_code != 200:
        print(f'\n被拒：HTTP {r.status_code}')
        print(r.text[:300])
        return 4

    d = r.json()
    usage = d.get('usage') or {}
    print('\nOK：key 可用。')
    print(f"  usage: prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')}")
    if not usage:
        print('  ⚠ 返回里没有 usage——成本账会记 0（这不影响对话，但账会不准）')
    print('\n下一步：重启服务让 key 生效，再跑')
    print('  .venv\\Scripts\\python.exe tools\\eval_p1.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
