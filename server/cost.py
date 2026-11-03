"""成本核算：只用上游真给的 usage，不拿字符数假装 token 数。

流式请求带 `stream_options.include_usage`，上游会在最后一块里回 usage；
没有 usage（没接模型、上游不认这个参数）就**记 0 并标明**，不估。

价格是估算，默认值按 DeepSeek 公开价的量级取，可用环境变量改：
  XJI_PRICE_IN  / XJI_PRICE_OUT   每百万 token 的人民币价
  XJI_DAILY_BUDGET                当日预算（元），超了就不再打上游
"""
from __future__ import annotations

import os
import threading
import time
from datetime import date

DEFAULT_IN = 2.0     # 元 / 百万 token（输入，缓存未命中量级）
DEFAULT_OUT = 8.0    # 元 / 百万 token（输出）

_LOCK = threading.Lock()


def _price(env: str, default: float) -> float:
    try:
        return float(os.environ.get(env, default))
    except ValueError:
        return default


class Ledger:
    def __init__(self, clock=time.monotonic, today=date.today):
        self._clock = clock
        self._today = today
        self.reset()

    def reset(self) -> None:
        with _LOCK:
            self.day = self._today().isoformat()
            self.requests = 0
            self.requests_without_usage = 0
            self.prompt_tokens = 0
            self.completion_tokens = 0

    def _roll(self) -> None:
        d = self._today().isoformat()
        if d != self.day:
            self.day = d
            self.requests = self.requests_without_usage = 0
            self.prompt_tokens = self.completion_tokens = 0

    def record(self, usage: dict | None) -> None:
        """usage 形如 {'prompt_tokens': 120, 'completion_tokens': 30}；None 表示上游没给。"""
        with _LOCK:
            self._roll()
            self.requests += 1
            if not usage:
                self.requests_without_usage += 1
                return
            self.prompt_tokens += int(usage.get('prompt_tokens') or 0)
            self.completion_tokens += int(usage.get('completion_tokens') or 0)

    def snapshot(self) -> dict:
        with _LOCK:
            self._roll()
            pin, pout = _price('XJI_PRICE_IN', DEFAULT_IN), _price('XJI_PRICE_OUT', DEFAULT_OUT)
            yuan = (self.prompt_tokens * pin + self.completion_tokens * pout) / 1_000_000
            cap = os.environ.get('XJI_DAILY_BUDGET')
            cap = float(cap) if cap else None
            return {
                'day': self.day,
                'requests': self.requests,
                'requests_without_usage': self.requests_without_usage,
                'prompt_tokens': self.prompt_tokens,
                'completion_tokens': self.completion_tokens,
                'estimated_cny': round(yuan, 4),
                'price_per_m_in': pin, 'price_per_m_out': pout,
                'daily_budget_cny': cap,
                'over_budget': bool(cap is not None and yuan >= cap),
                'note': '估算；只用上游返回的 usage，未返回的记为 0 并计入 requests_without_usage',
            }


LEDGER = Ledger()


def over_budget() -> bool:
    return LEDGER.snapshot()['over_budget']
