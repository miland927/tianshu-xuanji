"""周天 · 璇玑 —— 本地接口层。

一个进程同时做三件事：
  /api/now     此刻的历法与天文读数（tianzhi-core 算）
  /api/chart   一张盘的排盘结果（tianzhi-core 算）
  /api/chat    把问题 + 读数交给模型，流式吐回来（模型只负责讲人话）
其余路径当静态站。

跑：  .venv\\Scripts\\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8788
      （工作目录：D:\\Dev\\celestial-wheel）
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import audit, breaker, cal, compare, cost, evidence, metrics
from .guard import StreamGuard
from .persona import detect_risk, system_prompt

ROOT = Path(__file__).resolve().parent.parent
API_KEY = os.environ.get('DEEPSEEK_API_KEY', '').strip()
BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').strip()
MODEL = os.environ.get('TIANZHI_MODEL', 'deepseek-chat')

#: 网页上临时填的 key。只放内存，重启就没——不落盘，免得把别人的 key 写进文件。
_runtime_key: str = ''


def current_key() -> str:
    """运行时填的优先，其次是环境变量。"""
    return _runtime_key or API_KEY


def key_mask(key: str) -> str:
    if not key:
        return ''
    return f'{key[:4]}…{key[-4:]}' if len(key) > 10 else '***'


def key_source() -> str:
    if _runtime_key:
        return 'ui'
    return 'env' if API_KEY else 'none'

# 限流：默认每 IP 五分钟 30 次。本地一个人用根本碰不到，公开之后是底线。
RATE_LIMIT = int(os.environ.get('XJI_RATE_LIMIT', '30'))
RATE_WINDOW = float(os.environ.get('XJI_RATE_WINDOW', '300'))
_hits: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get('x-forwarded-for', '')
    return (fwd.split(',')[0].strip() if fwd else '') or (request.client.host if request.client else 'unknown')


def _rate_ok(ip: str) -> tuple[bool, float]:
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return False, max(0.0, RATE_WINDOW - (now - q[0]))
    q.append(now)
    return True, 0.0


# ---- 开放 API 的元信息 ----
# /api/docs 是 Swagger；schema 在 /api/openapi.json。分组与一句话说明在 ROUTE_META 里补，
# 免得为了加注释去改十七个装饰器。
API_DESC = """周天 · 读数 API。把 tianzhi-core 的确定性计算包成 HTTP 接口：此刻的历法读数、
一张盘的旺衰格局用神、四门盘（六壬/奇门/紫微）、年度报告，以及四门典籍的原文段落。

**边界**：这是传统文化研究与学习工具，不做预测、不判定吉凶、不提供医疗/法律/投资建议。
分数是「与用神顺逆」的折算，不是概率，也不能折算成任何现实事件的可能性。

**口径**：时间一律按**东八区钟表时间**解释（海外用 `standard_longitude` 与 `effective_longitude` 代换）；
节气按天文算法计算，与 pymeeus 对过表；月相与 ephem 对过表。
"""

TAGS = [
    {'name': '读数', 'description': '此刻的时间读数：节气、干支、真太阳时、恒星时、月相'},
    {'name': '盘', 'description': '按生辰排盘：四柱、旺衰、格局、用神、大运、六壬、奇门、紫微'},
    {'name': '报告', 'description': '跨时间的汇总：一年的十二个月、紫微的流年'},
    {'name': '原文', 'description': '四门典籍的段落级引用：查得到就给原文，查不到就直说'},
    {'name': '璇玑', 'description': '接 DeepSeek 的对话（SSE 流式）；输出经守则校验'},
    {'name': '运维', 'description': '健康检查、指标、告警'},
]

ROUTE_META = {
    '/api/now': ('读数', '此刻：节气/月建/真太阳/宿/月相'),
    '/api/calendar': ('读数', '某年的二十四节气与七十二候'),
    '/api/moon-calendar': ('读数', '某年的朔望时刻'),
    '/api/chart': ('盘', '一张八字盘：四柱→旺衰→格局→用神→大运'),
    '/api/compare': ('盘', '换一派：四组口径重算同一张盘并给差异'),
    '/api/liuren': ('盘', '大六壬：天地盘、四课、三传、课体、毕法'),
    '/api/qimen': ('盘', '时家奇门：局、九宫、直符直使、成格'),
    '/api/ziwei': ('盘', '紫微斗数命盘：十二宫、星曜、四化、大限'),
    '/api/ziwei/year': ('报告', '紫微流年：大限宫、流年宫、小限、流年四化'),
    '/api/year': ('报告', '年度报告：立春起十二个月'),
    '/api/passage': ('原文', '八字典籍引用 → 原句与今译'),
    '/api/liuren/bifa': ('原文', '《六壬大全》毕法赋某条的注'),
    '/api/ziwei/passage': ('原文', '《紫微斗数全书》宫×星论断'),
    '/api/qimen/passage': ('原文', '《遁甲演义》某一格的原节'),
    '/api/chat': ('璇玑', '问一句（SSE）：meta → delta → [violation] → done'),
    '/api/health': ('运维', '存活与是否 mock'),
    '/api/metrics': ('运维', '按路由的调用量/耗时/事件'),
    '/api/alerts': ('运维', '指标翻成告警'),
    '/api/corrections': ('运维', '勘误台账（只读）'),
    '/api/config': ('运维', '当前配置：key 有没有、从哪来、掩码（不回显全文）'),
    '/api/config/key': ('运维', '在网页上设置 / 清除 API key（只存内存）'),
    '/api/config/key/test': ('运维', '用当前 key 打一次最小请求，确认可用并返回 usage'),
    '/api': ('运维', '接口目录：版本、文档位置、分组'),
}

app = FastAPI(title='周天 · 读数 API', description=API_DESC, version='0.1.0',
              openapi_tags=TAGS, docs_url='/api/docs', redoc_url=None,
              openapi_url='/api/openapi.json',
              license_info={'name': 'MIT（上游 celestial-wheel）'})

_orig_openapi = app.openapi


def _openapi():
    schema = _orig_openapi()
    for path, (tag, summary) in ROUTE_META.items():
        for item in (schema.get('paths', {}).get(path) or {}).values():
            # FastAPI 会拿函数名生成 summary（now_view → "Now View"），所以这里要覆盖，不能 setdefault
            item['tags'] = [tag]
            item['summary'] = summary
    return schema


app.openapi = _openapi



class Place(BaseModel):
    longitude: float = 114.93
    latitude: float = 22.54
    standard_longitude: float = 120.0


class Msg(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    messages: list[Msg]
    place: Place = Place()
    birth: str | None = None
    gender: int = 0


@app.middleware('http')
async def _timing(request: Request, call_next):
    t0 = time.perf_counter()
    try:
        resp = await call_next(request)
        status = resp.status_code
    except Exception:
        metrics.record(request.method, request.url.path, 500, (time.perf_counter() - t0) * 1000)
        raise
    metrics.record(request.method, request.url.path, status, (time.perf_counter() - t0) * 1000)
    return resp


@app.get('/api')
def api_index():
    """这一层接口的目录：版本、文档位置、分组，以及一句边界说明。"""
    return {
        'name': '周天 · 读数 API',
        'version': app.version,
        'docs': '/api/docs',
        'schema': '/api/openapi.json',
        'examples': '/API.md',
        'tags': [{'name': t['name'],
                  'count': sum(1 for v in ROUTE_META.values() if v[0] == t['name'])}
                 for t in TAGS],
        'endpoints': [{'path': k, 'tag': v[0], 'summary': v[1]} for k, v in ROUTE_META.items()],
        'boundary': '传统文化研究与学习工具；不预测、不判定吉凶、不提供医疗法律投资建议。',
    }


@app.get('/api/corrections')
def corrections_view():
    """勘误台账：谁提了什么、现在是什么状态。只读——判定由人写进文件。"""
    from . import corrections as corr
    rows = corr.load()
    return {'count': len(rows), 'counts': corr.counts(), 'items': rows,
            'kinds': list(corr.KINDS), 'statuses': list(corr.STATUSES),
            'doc': '/CORRECTIONS.md'}


@app.get('/api/metrics')
def metrics_view(token: str = ''):
    """进程内指标：按路由的调用量/耗时、状态码分布、守则与降级次数、慢请求。

    设了 XJI_METRICS_TOKEN 就得带 `?token=`——上线时别把流量画像裸奔在公网。
    """
    want = os.environ.get('XJI_METRICS_TOKEN')
    if want and token != want:
        return JSONResponse(status_code=403, content={'error': 'forbidden'})
    snap = metrics.snapshot()
    snap['breaker'] = breaker.BREAKER.snapshot()
    snap['cost'] = cost.LEDGER.snapshot()
    return snap


@app.get('/api/alerts')
def alerts_view(token: str = ''):
    """指标翻成告警：有没有出错、有没有变慢、守则有没有在干活。"""
    want = os.environ.get('XJI_METRICS_TOKEN')
    if want and token != want:
        return JSONResponse(status_code=403, content={'error': 'forbidden'})
    from . import alerts as alerts_mod
    return alerts_mod.evaluate(metrics.snapshot())


@app.get('/api/config')
def config_view():
    """当前配置：key 有没有、从哪来、掩码长什么样。绝不回显完整 key。"""
    k = current_key()
    return {
        'key_present': bool(k),
        'key_source': key_source(),
        'key_mask': key_mask(k),
        'model': MODEL,
        'base_url': BASE_URL,
        'note': '网页上填的 key 只存在内存里，重启就没了；也可以用环境变量 DEEPSEEK_API_KEY',
    }


class KeyIn(BaseModel):
    key: str


@app.post('/api/config/key')
def config_set_key(inp: KeyIn):
    """网页上填 key。只放内存，不落盘。"""
    global _runtime_key
    k = (inp.key or '').strip()
    if len(k) < 20:
        raise HTTPException(status_code=400, detail='key 太短，看着不像')
    if ' ' in k:
        raise HTTPException(status_code=400, detail='key 里不该有空格')
    _runtime_key = k
    return {'ok': True, 'key_present': True, 'key_source': key_source(), 'key_mask': key_mask(k)}


@app.delete('/api/config/key')
def config_clear_key():
    global _runtime_key
    _runtime_key = ''
    return {'ok': True, 'key_present': bool(current_key()), 'key_source': key_source()}


@app.post('/api/config/key/test')
def config_test_key():
    """拿当前的 key 打一次最小请求，确认它可用、并且能拿到 usage。"""
    k = current_key()
    if not k:
        raise HTTPException(status_code=400, detail='还没有 key')
    body = {'model': MODEL, 'stream': False, 'max_tokens': 1, 'temperature': 0,
            'messages': [{'role': 'user', 'content': 'ping'}]}
    try:
        r = httpx.post(f'{BASE_URL}/chat/completions', json=body, timeout=30,
                       headers={'Authorization': f'Bearer {k}'})
    except Exception as e:
        return {'ok': False, 'reason': f'{type(e).__name__}: {e}'}
    if r.status_code != 200:
        return {'ok': False, 'reason': f'HTTP {r.status_code}', 'detail': r.text[:200]}
    usage = (r.json() or {}).get('usage') or {}
    return {'ok': True, 'usage': usage}


@app.get('/api/health')
def health():
    return {'ok': True, 'mock': not bool(current_key()), 'model': MODEL,
            'utc': datetime.now(timezone.utc).isoformat()}


@app.get('/api/now')
def now(longitude: float = 114.93, latitude: float = 22.54, standard_longitude: float = 120.0):
    return cal.now_snapshot(longitude, latitude, standard_longitude)


@app.get('/api/chart')
def chart_view(birth: str, longitude: float = 114.93, gender: int = 0, ziwei: bool = False,
               standard_longitude: float = 120.0):
    try:
        return cal.chart_snapshot(birth, longitude, gender, with_ziwei=ziwei,
                                  standard_longitude=standard_longitude)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f'birth 格式应为 YYYY-MM-DD HH:MM（{e}）')


def _parse_at(s: str, field: str = 'at') -> datetime:
    """用户给的时间串：格式不对是 400，不是 500。"""
    try:
        return datetime.strptime((s or '').strip().replace('T', ' '), '%Y-%m-%d %H:%M')
    except ValueError:
        raise HTTPException(status_code=400, detail=f'{field} 格式应为 YYYY-MM-DD HH:MM')


def _sse(event: str, data) -> str:
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


def _derived(chart: dict | None) -> dict:
    """审计里只留派生量：不存生辰，也能把当时的结论解释清楚。"""
    if not chart:
        return {}
    st = chart.get('strength') or {}
    g = chart.get('geju') or {}
    y = chart.get('yongshen') or {}
    cur = chart.get('current') or {}
    ts = chart.get('true_solar') or ''
    return {
        # 只留时刻，不留日期：日期本身就是生辰的一部分
        'true_solar': ts.split(' ')[-1] if ts else None,
        'siling': chart.get('siling'),
        'strength': {'label': st.get('label'), 'ratio': st.get('ratio')},
        'geju': g.get('name'),
        'yong': y.get('yong'),
        'method': y.get('method'),
        'evidence': list(y.get('evidence') or [])[:12],
        'current': {'year': cur.get('year_gz'), 'dayun': cur.get('dayun'), 'score': cur.get('score')},
    }


def _mock_reply(ctx: dict) -> str:
    n = ctx.get('now', {})
    lines = [
        '接口还没接上：这台机器上没有 DEEPSEEK_API_KEY，所以现在是我在念读数。',
        '',
        f"此刻 {n.get('clock_bj')}，月建 {n.get('month_zhi')}，{n.get('jie', {}).get('name')} 后 "
        f"{n.get('days_after_jie')} 天；真太阳时 {n.get('true_solar')}。",
    ]
    if ctx.get('chart'):
        c = ctx['chart']
        lines += [
            f"盘：{c['bazi']}；旺衰 {c['strength']['label']}（{c['strength']['ratio']}）；"
            f"格 {c['geju']['name']}；用 {c['yongshen']['yong']}。",
        ]
    lines += [
        '',
        '接上模型后，这里会是璇玑按读数讲的话。它的约束是：只读不算、不编出处、不断具体事件、',
        '不涉医疗法律投资。读数以上面这些字段为准。',
    ]
    return '\n'.join(lines)


def _fallback_text(ctx: dict) -> str:
    """模型不可用时说的话：不解释，只念读数，且明说是降级。"""
    n = ctx.get('now') or {}
    c = ctx.get('chart')
    lines = [
        '模型暂时不可用，我不解释，只念读数：',
        '',
        f"{n.get('clock_bj')} · 月建 {n.get('month_zhi')} · "
        f"{n.get('jie', {}).get('name')} 后 {n.get('days_after_jie')} 天",
        f"真太阳时 {n.get('true_solar')} · 四柱 {n.get('bazi')}",
    ]
    sid = n.get('sidereal') or {}
    if sid.get('xiu'):
        lines.append(f"恒星时 {sid.get('lst_hms')} · 子午线在 {sid['xiu'].get('name')}宿")
    if c:
        lines += ['', f"盘：{c.get('bazi')}；旺衰 {c['strength']['label']} {c['strength']['ratio']}；"
                      f"格 {c.get('geju', {}).get('name')}；用 {c.get('yongshen', {}).get('yong')}。"]
    lines += ['', '下面的「依据」照样能点开；模型回来之前，不给判断。']
    return '\n'.join(lines)


@app.post('/api/chat')
async def chat(inp: ChatIn, request: Request):
    ok, retry = _rate_ok(_client_ip(request))
    if not ok:
        metrics.bump('rate_limited')
        return JSONResponse(status_code=429,
                            content={'error': 'rate_limited', 'retry_after': round(retry, 1),
                                     'hint': f'每 {int(RATE_WINDOW)} 秒最多 {RATE_LIMIT} 次'})

    ctx: dict = {'now': cal.now_snapshot(inp.place.longitude, inp.place.latitude,
                                         inp.place.standard_longitude)}
    if inp.birth:
        try:
            ctx['chart'] = cal.chart_snapshot(inp.birth, inp.place.longitude, inp.gender,
                                              standard_longitude=inp.place.standard_longitude)
        except Exception as e:  # 生辰格式不对就如实说，不猜
            ctx['chart_error'] = f'{type(e).__name__}: {e}'

    last = next((m.content for m in reversed(inp.messages) if m.role == 'user'), '')
    risk = detect_risk(last)
    ctx['risk'] = risk
    # 把性别的字面写进上下文：只给 0/1，模型会自己映射反（真跑时它把 0 当成女，还据此说盘排错了）
    ctx['gender_label'] = '男' if inp.gender == 0 else '女'
    ctx['gender_note'] = '0 = 男，1 = 女（tianzhi-core 的约定）'

    async def gen():
        rid = audit.new_id()
        t0 = time.perf_counter()
        out: list[str] = []
        violations: list[dict] = []
        status = 'ok'
        sys_digest = audit._digest(system_prompt(json.dumps(ctx, ensure_ascii=False, default=str), risk))

        def _degraded(reason: str) -> list[str]:
            """上游坏了也不留白：降级成「只念读数」。"""
            nonlocal status
            status = reason
            metrics.bump('degraded')
            text = _fallback_text(ctx)
            out.append(text)
            events = [_sse('degraded', {'reason': reason})]
            events += [_sse('delta', {'text': text[i:i + 18]}) for i in range(0, len(text), 18)]
            events.append(_sse('done', {'mock': False, 'id': rid, 'degraded': True}))
            return events

        yield _sse('meta', {'id': rid,
                            'now': {k: ctx['now'][k] for k in
                                    ('clock_bj', 'month_zhi', 'true_solar', 'jie', 'next_jie')},
                            'chart': ctx.get('chart', {}).get('bazi') if ctx.get('chart') else None,
                            'warnings': ctx.get('chart', {}).get('warnings', []) if ctx.get('chart') else [],
                            'evidence': evidence.groups(ctx),
                            'focus': _focus(ctx, last),
                            'risk': risk, 'mock': not bool(current_key())})
        try:
            if not current_key():
                metrics.bump('mock_reply')
                text = _mock_reply(ctx)
                for i in range(0, len(text), 12):
                    yield _sse('delta', {'text': text[i:i + 12]})
                out.append(text)
                yield _sse('done', {'mock': True, 'id': rid})
                return

            payload = {
                'model': MODEL,
                'stream': True,
                'stream_options': {'include_usage': True},
                'temperature': 0.6,
                'max_tokens': 1200,
                'messages': [{'role': 'system', 'content': system_prompt(json.dumps(ctx, ensure_ascii=False, default=str), risk)}]
                            + [{'role': m.role, 'content': m.content} for m in inp.messages[-12:]],
            }
            guard = StreamGuard()

            if cost.over_budget():
                metrics.bump('budget_exhausted')
                for ev in _degraded('budget_exhausted: 当日预算已用完'):
                    yield ev
                return

            if not breaker.BREAKER.allow():
                metrics.bump('circuit_open')
                snap = breaker.BREAKER.snapshot()
                for ev in _degraded(f'circuit_open: 上游连续失败，{snap["retry_in_s"]}s 后再试'):
                    yield ev
                return

            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream('POST', f'{BASE_URL}/chat/completions', json=payload,
                                         headers={'Authorization': f'Bearer {current_key()}'}) as r:
                    if r.status_code != 200:
                        breaker.BREAKER.failure()
                        body = (await r.aread()).decode('utf-8', 'replace')[:300]
                        for ev in _degraded(f'upstream_{r.status_code}: {body[:120]}'):
                            yield ev
                        return
                    breaker.BREAKER.success()
                    usage = None
                    async for line in r.aiter_lines():
                        if not line.startswith('data: '):
                            continue
                        chunk = line[6:].strip()
                        if chunk == '[DONE]':
                            break
                        try:
                            payload_chunk = json.loads(chunk)
                        except Exception:
                            continue
                        if isinstance(payload_chunk, dict) and payload_chunk.get('usage'):
                            usage = payload_chunk['usage']     # include_usage 的最后一块
                            continue
                        try:
                            delta = payload_chunk['choices'][0]['delta'].get('content')
                        except Exception:
                            continue
                        if not delta:
                            continue
                        safe, bad = guard.push(delta)
                        if bad:
                            violations.extend(bad)
                            metrics.bump('guard_hit', len(bad))
                            yield _sse('violation', bad)
                        if safe:
                            out.append(safe)
                            yield _sse('delta', {'text': safe})
                    cost.LEDGER.record(usage)
            safe, bad = guard.flush()
            if bad:
                violations.extend(bad)
                yield _sse('violation', bad)
            if safe:
                out.append(safe)
                yield _sse('delta', {'text': safe})
            yield _sse('done', {'mock': False, 'id': rid, 'violations': len(guard.violations)})
        except Exception as e:
            breaker.BREAKER.failure()
            reason = f'error:{type(e).__name__}'
            for ev in _degraded(reason):
                yield ev
            yield _sse('note', {'message': f'{type(e).__name__}: {e}'})
        finally:
            audit.write({
                'id': rid,
                'ms': round((time.perf_counter() - t0) * 1000, 1),
                'status': status,
                'in': audit.scrub(last),
                'out': audit.scrub(''.join(out), secrets=[inp.birth], generic=False),
                'chars': len(''.join(out)),
                'req': {'place': inp.place.model_dump(), 'gender': inp.gender,
                        **audit.mask_birth(inp.birth)},
                'ctx': {'bazi': (ctx.get('chart') or {}).get('bazi'),
                        'month_zhi': ctx['now'].get('month_zhi'),
                        'jie': (ctx['now'].get('jie') or {}).get('name'),
                        'warnings': [w.get('kind') for w in (ctx.get('chart') or {}).get('warnings', [])],
                        'risk': risk,
                        'system': sys_digest,
                        # 派生量：不存生辰也能解释当时的结论（还原上下文用）
                        'derived': _derived(ctx.get('chart'))},
                'violations': violations,
                'mock': not bool(current_key()),
            })

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'cache-control': 'no-cache', 'x-accel-buffering': 'no'})


@app.get('/api/calendar')
def calendar_view(year: int | None = None):
    """某年的二十四节气表；不给年份就取东八区当下这一年。"""
    y = year or cal.now_snapshot().get('clock_bj', '')[:4]
    return cal.calendar_year(int(y))


@app.get('/api/moon-calendar')
def moon_calendar_view(year: int | None = None):
    """某年的朔望表；不给年份就取当下这一年。"""
    from . import moon as moon_mod
    y = year or int(cal.now_snapshot().get('clock_bj', '')[:4])
    return {'year': y, 'events': [{'kind': e['kind'], 'at': e['at'].strftime('%Y-%m-%d %H:%M')}
                                  for e in moon_mod.year_events(int(y))]}


@app.get('/api/liuren')
def liuren_view(at: str | None = None):
    """起一课大六壬。at 形如 '2026-11-03 01:30'（东八区钟表时间），不给就用此刻。"""
    from tianzhi_core.liuren import pan as liuren_pan

    if at:
        dt = _parse_at(at)
    else:
        dt = datetime.strptime(cal.now_snapshot().get('clock_bj', ''), '%Y-%m-%d %H:%M:%S')
    ke = liuren_pan.qike(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    return cal.plain(ke)


@app.get('/api/qimen')
def qimen_view(at: str | None = None):
    """起一局时家奇门。at 形如 '2026-11-03 15:00'（东八区钟表时间），不给就用此刻。"""
    from tianzhi_core.qimen import qiju

    if at:
        dt = _parse_at(at)
    else:
        dt = datetime.strptime(cal.now_snapshot().get('clock_bj', ''), '%Y-%m-%d %H:%M:%S')
    r = cal.plain(qiju(dt))
    ju = r.get('ju') or {}
    if hasattr(ju.get('jieqi_time'), 'isoformat'):
        ju['jieqi_time'] = ju['jieqi_time'].strftime('%Y-%m-%d %H:%M')
    return r


@app.get('/api/ziwei')
def ziwei_view(birth: str = '1996-04-18 13:46', gender: int = 0):
    """排一张紫微斗数命盘。birth 是出生地钟表时间。"""
    from tianzhi_core import ziwei as ziwei_mod

    dt = _parse_at(birth, 'birth')
    return cal.plain(ziwei_mod.build_chart(dt, gender))


@app.get('/api/passage')
def passage_view(cite: str = ''):
    """把「穷通宝鉴·乙日辰月」这种引用落到典籍数据集里的那一条原文。"""
    from . import passages as passages_mod
    return passages_mod.lookup(cite)


@app.get('/api/liuren/bifa')
def bifa_view(no: int = 1):
    """《毕法赋》某一条的原文注。"""
    from . import bifa as bifa_mod
    return bifa_mod.get(no)


@app.get('/api/ziwei/passage')
def ziwei_passage(palace: str, stars: str = ''):
    """某宫某星的《紫微斗数全书》原文；stars 可给多个（逗号分隔），取第一个查得到的。"""
    from . import ziwei_src
    return ziwei_src.lookup_any(palace, [s for s in stars.split(',') if s])


@app.get('/api/qimen/passage')
def qimen_passage(cite: str = ''):
    """奇门某一格在《遁甲演义》里的原文；cite 用格自带的引用，如「遁甲演義·卷二|青龍回首」。"""
    from . import qimen_src
    return qimen_src.lookup_cite(cite)


@app.get('/api/year')
def year_view(birth: str = '1996-04-18 14:06', year: int | None = None, gender: int = 0,
              longitude: float = 114.93, standard_longitude: float = cal.BEIJING):
    """一张盘某一年的十二个月（立春起算）。"""
    from . import year as year_mod
    y = year or int(cal.now_snapshot().get('clock_bj', '')[:4])
    try:
        return year_mod.year_report(birth, int(y), gender, longitude, standard_longitude)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f'birth 格式应为 YYYY-MM-DD HH:MM（{e}）')


@app.get('/api/ziwei/year')
def ziwei_year_view(birth: str = '1996-04-18 13:46', gender: int = 0, year: int | None = None):
    """紫微的「今年」：大限宫、流年宫、小限、流年四化。"""
    from . import ziwei_year
    y = year or int(cal.now_snapshot().get('clock_bj', '')[:4])
    try:
        return ziwei_year.year_view(birth, gender, int(y))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f'birth 格式应为 YYYY-MM-DD HH:MM（{e}）')


@app.get('/api/compare')
def compare_view(birth: str, longitude: float = 114.93, gender: int = 0,
                 standard_longitude: float = 120.0):
    """同一张盘，换三组口径重算，返回差异表。"""
    return compare.compare(birth, longitude, gender, standard_longitude)


def _focus(ctx: dict, question: str) -> dict | None:
    """决定让哪一环转到哪一格。

    索引不由模型给，也不由前端算：这里只给「环 + 字」，前端用 wheel.indexOf 去找格子。
    模型如果想指，也只能指这几个现成的候选。
    """
    now = ctx.get('now') or {}
    chart = ctx.get('chart') or {}
    jie = (now.get('jie') or {}).get('name')
    term = (now.get('term') or {}).get('name') or jie
    chart_parts = (chart.get('bazi') or '').split()
    now_parts = (now.get('bazi') or '').split()
    # 没报生辰时，「今天」「此刻」用当刻四柱
    day_gz = chart_parts[2] if len(chart_parts) >= 4 else (now_parts[2] if len(now_parts) >= 4 else None)
    hour_zhi = ((chart.get('quad') or {}).get('hour') or [None, None])[1] if chart else None
    if not hour_zhi and len(now_parts) >= 4:
        hour_zhi = now_parts[3][1]

    q = question or ''
    if any(k in q for k in ('星宿', '二十八宿', '恒星时', '子午线')):
        xiu = ((now.get('sidereal') or {}).get('xiu') or {}).get('name')
        if xiu:
            return {'ring': '二十八宿', 'label': xiu}
    if any(k in q for k in ('时辰', '时柱', '几点', '地支')):
        if hour_zhi:
            return {'ring': '十二地支', 'label': hour_zhi}
    if any(k in q for k in ('日柱', '今天', '甲子', '干支', '日子')):
        if day_gz:
            return {'ring': '六十甲子', 'label': day_gz}
    if term:
        return {'ring': '二十四节气', 'label': term}
    return None


app.mount('/', StaticFiles(directory=str(ROOT), html=True), name='static')
