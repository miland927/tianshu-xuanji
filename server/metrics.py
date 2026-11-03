"""运行指标：进程内的计数与耗时，不依赖外部服务。

为什么自己写而不是接 Prometheus：这东西现在只有一个人跑、一台机器，
一个 `/api/metrics` 就够看出「哪条路由慢、拦了多少次、降级过几次」。
真要上生产再换 exporter，接口形状不变。
"""
from __future__ import annotations

import threading
import time
from collections import Counter, deque

START = time.time()
_LOCK = threading.Lock()

REQUESTS: Counter = Counter()      # "GET /api/now 200" → n
ROUTE_LAT: Counter = Counter()     # "GET /api/now" → 累计秒
ROUTE_N: Counter = Counter()
ROUTE_MAX: dict[str, float] = {}
RECENT: dict[str, deque] = {}      # 每路由最近 256 次耗时，用来算 p50/p95
EVENTS: Counter = Counter()        # guard_hit / degraded / rate_limited / mock_reply …
SLOW: deque = deque(maxlen=50)     # 最近 50 条慢请求

SLOW_MS = 1500.0
WINDOW = 256


def normalize(path: str) -> str:
    if path.startswith('/api/'):
        return path.rstrip('/')
    if path in ('/', '/index.html'):
        return '/'
    return 'static'


def record(method: str, path: str, status: int, ms: float) -> None:
    key = f'{method} {normalize(path)}'
    with _LOCK:
        REQUESTS[f'{key} {status}'] += 1
        ROUTE_N[key] += 1
        ROUTE_LAT[key] += ms
        ROUTE_MAX[key] = max(ROUTE_MAX.get(key, 0.0), ms)
        RECENT.setdefault(key, deque(maxlen=WINDOW)).append(ms)
        if ms >= SLOW_MS:
            SLOW.append({'at': round(time.time() - START, 1), 'route': key, 'ms': round(ms, 1)})


def bump(name: str, n: int = 1) -> None:
    with _LOCK:
        EVENTS[name] += n


def _pct(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return round(s[i], 1)


def snapshot() -> dict:
    with _LOCK:
        routes = {}
        for key in sorted(ROUTE_N):
            n = ROUTE_N[key]
            routes[key] = {
                'count': n,
                'avg_ms': round(ROUTE_LAT[key] / n, 1) if n else 0.0,
                'max_ms': round(ROUTE_MAX.get(key, 0.0), 1),
                'p50_ms': _pct(list(RECENT.get(key, [])), 0.50),
                'p95_ms': _pct(list(RECENT.get(key, [])), 0.95),
            }
        return {
            'uptime_s': round(time.time() - START, 1),
            'routes': routes,
            'status': dict(sorted(REQUESTS.items())),
            'events': dict(sorted(EVENTS.items())),
            'slow': list(SLOW),
        }


def reset() -> None:
    """测试用。"""
    with _LOCK:
        REQUESTS.clear(); ROUTE_LAT.clear(); ROUTE_N.clear()
        ROUTE_MAX.clear(); RECENT.clear(); EVENTS.clear(); SLOW.clear()
