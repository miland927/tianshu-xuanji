"""从最近一次真模型评估里，原样摘几段对话，生成 samples.html。

不做编辑：只取、只排、只标注它用了多久、有没有被拦。
模型说得对不对，由读者自己看——这是一页「它长什么样」，不是一页宣传。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'samples.html'

PICK = [('cite', '逼它编出处'), ('medical', '医疗边界'), ('finance', '投资边界'),
        ('predict', '逼它预测'), ('normal', '正常提问')]


def load_latest() -> tuple[Path, list[dict]]:
    best = None
    for f in sorted((ROOT / 'eval').glob('p1-*.jsonl')):
        rows = [json.loads(l) for l in f.read_text(encoding='utf-8').splitlines() if l.strip()]
        if rows and not rows[0].get('mock'):
            best = (f, rows)
    if not best:
        raise SystemExit('没有真模型跑出来的 eval/p1-*.jsonl，先跑 tools/eval_p1.py')
    return best


def esc(s: str) -> str:
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def main() -> int:
    src, rows = load_latest()
    picked = []
    for cat, label in PICK:
        hit = next((r for r in rows if r['cat'] == cat), None)
        if hit:
            picked.append((label, hit))

    blocks = []
    for label, r in picked:
        text = (r.get('text') or '').strip()
        blocks.append(f'''
  <section class="qa">
    <div class="meta"><span class="chip">{label}</span>
      <span>{r['ms'] / 1000:.1f}s</span>
      <span>{len(text)} 字</span>
      <span>{'被守则改写 ' + str(len(r['server_violations'])) + ' 处' if r.get('server_violations') else '未被守则改写'}</span>
    </div>
    <div class="q">{esc(r['prompt'])}</div>
    <pre class="a">{esc(text)}</pre>
  </section>''')

    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>它长什么样 · 周天</title>
<style>
  :root {{ --ink:#e7e1d3; --dim:#6f6a60; --zhu:#d9483f; --gold:#f0d9b5; --hair:rgba(242,237,224,.14); }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#050505; color:var(--ink);
         font:13px/1.95 "PingFang SC","Noto Sans SC",system-ui,sans-serif; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:52px 24px 96px; }}
  header {{ display:flex; align-items:baseline; gap:14px; }}
  h1 {{ font:500 21px/1.4 "Songti SC","STSong",serif; letter-spacing:.2em; margin:0; }}
  header a {{ margin-left:auto; font-size:11px; color:var(--dim); text-decoration:none;
             border-bottom:1px solid var(--hair); }}
  header a:hover {{ color:var(--ink); }}
  .lede {{ color:rgba(231,225,211,.72); font:14px/2 "Songti SC","STSong",serif; margin:16px 0 4px; }}
  .lede b {{ color:var(--gold); font-weight:500; }}
  .src {{ font:10.5px/1.8 ui-monospace,monospace; color:var(--dim); margin-bottom:26px; }}
  .qa {{ border-top:1px solid var(--hair); padding:20px 0 6px; }}
  .meta {{ display:flex; gap:14px; font:10px/1.6 ui-monospace,monospace; color:var(--dim);
           letter-spacing:.08em; margin-bottom:8px; }}
  .chip {{ color:var(--zhu); border:1px solid rgba(217,72,63,.4); padding:1px 6px; }}
  .q {{ font:500 15px/1.8 "Songti SC","STSong",serif; color:var(--ink); margin-bottom:10px; }}
  .q::before {{ content:"问 "; color:var(--dim); font-size:11px; letter-spacing:.2em; }}
  .a {{ margin:0; white-space:pre-wrap; word-break:break-word;
        font:12.5px/2 "Songti SC","STSong",serif; color:rgba(231,225,211,.8);
        border-left:2px solid rgba(240,217,181,.28); padding:2px 0 2px 14px; }}
  footer {{ margin-top:44px; padding-top:16px; border-top:1px solid var(--hair);
            font-size:11px; line-height:2; color:var(--dim); }}
  footer a {{ color:rgba(231,225,211,.55); text-decoration:none; border-bottom:1px solid var(--hair); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>它长什么样</h1>
    <a href="/">← 回到周天</a>
  </header>
  <p class="lede">
    下面是从一次真模型评估里<b>原样抽出来</b>的问答。没有润色，没有挑最好的一段——
    按类别各取第一条：逼它编出处、医疗、投资、预测、正常提问。
  </p>
  <div class="src">来源：{src.name} · {len(rows)} 轮 · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
{''.join(blocks)}
  <footer>
    这些是模型的原话。它说错的、说对的，都在这儿——
    这台东西的边界是「只读不算」，所以它多数时候在说「这不是我能答的」。<br>
    完整数据：<a href="/eval/{src.name}">{src.name}</a> ·
    <a href="/guide.html">使用说明</a> ·
    <a href="/corrections.html">勘误台账</a>
  </footer>
</div>
</body>
</html>
'''
    OUT.write_text(html, encoding='utf-8')
    print(f'已写 {OUT.name}（{len(picked)} 段，来源 {src.name}）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
