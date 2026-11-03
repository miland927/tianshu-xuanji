"""把指标翻成「要不要管」。

阈值写死在这里，是为了让告警可读、可改、可测——不是藏进某个仪表盘里。
它只回答三件事：有没有出错、有没有变慢、守则有没有在干活。
"""
from __future__ import annotations

ERR_RATE = 0.05          # 5xx 占比
MIN_SAMPLES = 20         # 样本太少不算率
SLOW_P95_MS = 1500.0     # 单路由 p95 上限
SLOW_MIN_CALLS = 5
DEGRADED_WARN = 1        # 降级过一次就值得看一眼
RATE_LIMIT_WARN = 20


def _code(key: str) -> int:
    try:
        return int(key.rsplit(' ', 1)[-1])
    except ValueError:
        return 0


def evaluate(snap: dict) -> dict:
    status = snap.get('status') or {}
    routes = snap.get('routes') or {}
    events = snap.get('events') or {}
    total = sum(status.values())
    errs = sum(v for k, v in status.items() if _code(k) >= 500)
    alerts: list[dict] = []

    if total == 0:
        alerts.append({'level': 'info', 'code': 'no_traffic', 'detail': '还没有请求'})
        return {'ok': True, 'alerts': alerts, 'total': 0, 'errors': 0, 'error_rate': 0.0}

    rate = errs / total
    if total >= MIN_SAMPLES and rate > ERR_RATE:
        alerts.append({'level': 'error', 'code': 'error_rate',
                       'detail': f'5xx {errs}/{total} = {rate:.1%}，超过 {ERR_RATE:.0%}'})

    for route, r in routes.items():
        p95 = r.get('p95_ms') or 0
        if p95 >= SLOW_P95_MS and (r.get('count') or 0) >= SLOW_MIN_CALLS:
            alerts.append({'level': 'warn', 'code': 'slow_route',
                           'detail': f'{route} p95 {p95}ms（{r.get("count")} 次）'})

    if events.get('degraded', 0) >= DEGRADED_WARN:
        alerts.append({'level': 'warn', 'code': 'degraded',
                       'detail': f'降级 {events["degraded"]} 次：上游或网络出过问题'})
    if events.get('rate_limited', 0) > RATE_LIMIT_WARN:
        alerts.append({'level': 'warn', 'code': 'rate_limited',
                       'detail': f'限流 {events["rate_limited"]} 次：可能被刷，或自己压测忘了调'})
    if events.get('guard_hit', 0) > 0:
        alerts.append({'level': 'info', 'code': 'guard_hit',
                       'detail': f'守则改写 {events["guard_hit"]} 处：它在干活'})

    br = snap.get('breaker') or {}
    if br.get('state') == 'open':
        alerts.append({'level': 'warn', 'code': 'circuit_open',
                       'detail': f'上游熔断中，{br.get("retry_in_s")}s 后放探针'})

    co = snap.get('cost') or {}
    if co.get('over_budget'):
        alerts.append({'level': 'warn', 'code': 'over_budget',
                       'detail': f"当日已花 ¥{co.get('estimated_cny')}，预算 ¥{co.get('daily_budget_cny')}"})
    elif (co.get('requests_without_usage') or 0) > 0:
        alerts.append({'level': 'info', 'code': 'no_usage',
                       'detail': f"{co['requests_without_usage']} 次调用上游没回 usage，成本未计入"})

    slow = snap.get('slow') or []
    if slow:
        worst = max(slow, key=lambda x: x.get('ms', 0))
        alerts.append({'level': 'info', 'code': 'slow_samples',
                       'detail': f'最慢一次 {worst.get("ms")}ms @ {worst.get("route")}'})

    order = {'error': 0, 'warn': 1, 'info': 2}
    alerts.sort(key=lambda a: order.get(a['level'], 3))

    return {
        'ok': not any(a['level'] == 'error' for a in alerts),
        'alerts': alerts,
        'total': total,
        'errors': errs,
        'error_rate': round(rate, 4),
    }
