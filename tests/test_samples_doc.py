"""samples.html 必须来自真跑的数据，不能手写。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SAMPLES = ROOT / 'samples.html'


def test_exists():
    assert SAMPLES.exists(), '先跑 tools/samples.py'


def test_has_five_exchanges():
    t = SAMPLES.read_text(encoding='utf-8')
    assert t.count('<section class="qa">') == 5


def test_cites_a_real_run():
    t = SAMPLES.read_text(encoding='utf-8')
    m = re.search(r'来源：(p1-\d{8}-\d{6}\.jsonl)', t)
    assert m, '没写来源'
    src = ROOT / 'eval' / m.group(1)
    assert src.exists(), f'来源文件不在：{src.name}'
    rows = [json.loads(l) for l in src.read_text(encoding='utf-8').splitlines() if l.strip()]
    assert rows and not rows[0].get('mock'), '来源是 mock 跑出来的，不能用'
    # 页面里的问句必须真的出现在那份数据里
    prompts = {r['prompt'] for r in rows}
    for q in re.findall(r'<div class="q">(.*?)</div>', t):
        assert q in prompts, f'页面里的问句不在数据里：{q[:30]}'
