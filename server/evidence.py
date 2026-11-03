"""把一次回答背后的判据整理成界面能直接摆出来的样子。

原则：界面上看到的每一行，都必须来自这个函数，不能由前端自己拼、更不能由模型编。
所以这里只做「取字段 + 分组 + 截断」，不做任何判断。
"""
from __future__ import annotations


def _short(x: str, n: int = 48) -> str:
    x = str(x)
    return x if len(x) <= n else x[:n] + '…'


def groups(ctx: dict) -> list[dict]:
    out: list[dict] = []

    now = ctx.get('now') or {}
    if now:
        term = now.get('term') or {}
        items = [
            (f"{term.get('name')} 交节 {term.get('at')}" if term
             else f"{now.get('jie', {}).get('name')} 交节 {now.get('jie', {}).get('at')}"),
            f"月建 {now.get('month_zhi')} · 距节 {now.get('days_after_jie')} 天",
            f"真太阳时 {now.get('true_solar')}（校正 {now.get('correction_minutes')} 分）",
        ]
        sid = now.get('sidereal') or {}
        if sid.get('xiu'):
            items.append(f"恒星时 {sid.get('lst_hms')} · 子午线在 {sid['xiu'].get('name')}宿")
        m = now.get('moon') or {}
        if m:
            items.append(f"月相 {m.get('name')} · 日月黄经差 {m.get('elong_deg')}° · 照度 {round((m.get('illum') or 0) * 100)}%")
        out.append({'layer': '历法', 'items': items})

    c = ctx.get('chart')
    if not c:
        return out

    out.append({'layer': '四柱', 'items': [
        c.get('bazi', ''),
        f"人元司令 {c.get('siling')}",
        f"真太阳时 {c.get('true_solar')}",
    ]})

    st = c.get('strength', {})
    items = [f"{st.get('label')} · ratio {st.get('ratio')}（扶 {st.get('support')} / 抑 {st.get('drain')}）"]
    for it in (st.get('items') or [])[:5]:
        tag = '、'.join(it.get('tags') or [])
        items.append(f"{it.get('source')} {it.get('score')}" + (f'（{tag}）' if tag else ''))
    out.append({'layer': '旺衰', 'items': items})

    g = c.get('geju', {})
    out.append({'layer': '格局', 'items': [f"{g.get('name')} · {g.get('basis')}"] + list(g.get('evidence') or [])})

    y = c.get('yongshen', {})
    out.append({'layer': '用神', 'items': [
        f"用 {y.get('yong')} / 喜 {y.get('xi')} / 忌 {y.get('ji')} / 仇 {y.get('chou')} · 方法 {y.get('method')}"
    ] + list(y.get('evidence') or [])})

    cur = c.get('current') or {}
    if cur:
        rows = [f"{cur.get('year_gz')} 年 · 大运 {cur.get('dayun')} · {cur.get('score')} 分（50 为不偏）"]
        for k, v in (cur.get('breakdown') or {}).items():
            try:
                rows.append(f"{k} {float(v):+.1f}")
            except (TypeError, ValueError):
                rows.append(f'{k} {v}')
        out.append({'layer': '岁运', 'items': rows})

    for w in c.get('warnings') or []:
        out.append({'layer': '提示', 'items': [_short(w.get('text', ''), 60)]})

    return out
