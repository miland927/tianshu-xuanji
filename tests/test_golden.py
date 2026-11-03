"""黄金集不许漂。跑：.venv\\Scripts\\python.exe -m pytest tests -q"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))

import golden  # noqa: E402


def test_golden_file_exists():
    assert golden.GOLDEN.exists(), '先跑 tools/golden.py --freeze'


def test_golden_has_enough_cases():
    rows = [json.loads(l) for l in golden.GOLDEN.read_text(encoding='utf-8').splitlines() if l.strip()]
    assert len(rows) >= 40
    assert len(rows) == len(golden.CASES)
    assert all('expect' in r for r in rows)


def test_no_drift():
    rows = [json.loads(l) for l in golden.GOLDEN.read_text(encoding='utf-8').splitlines() if l.strip()]
    for rec in rows:
        got = golden.snapshot(rec['birth'], rec['longitude'], rec['gender'],
                              rec.get('standard_longitude', 120.0))
        for key, want in rec['expect'].items():
            assert got.get(key) == want, f"{rec['id']}.{key}: 期望 {want!r} 实得 {got.get(key)!r}"


def test_dst_cases_carry_warning():
    rows = [json.loads(l) for l in golden.GOLDEN.read_text(encoding='utf-8').splitlines() if l.strip()]
    in_dst = {'dst_1990', 'dst_1988_zi', 'dst_1987', 'dst_edge_out'}
    found = {r['id'] for r in rows if 'dst' in r['expect']['warnings']}
    assert in_dst <= found, f'缺夏令时警告：{in_dst - found}'
    # 边界：进入当刻（02:00 跳过）与结束之后，都不该报
    assert 'dst' not in next(r for r in rows if r['id'] == 'dst_edge_in')['expect']['warnings']
    assert 'dst' not in next(r for r in rows if r['id'] == 'dst_after_end')['expect']['warnings']
