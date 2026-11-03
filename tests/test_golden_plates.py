"""三盘快照不许漂：六壬、奇门、紫微。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))

import golden_plates as gp  # noqa: E402


def rows():
    assert gp.GOLDEN.exists(), '先跑 tools/golden_plates.py --freeze'
    return [json.loads(l) for l in gp.GOLDEN.read_text(encoding='utf-8').splitlines() if l.strip()]


def test_has_nine_cases():
    rs = rows()
    assert len(rs) == 9
    assert {r['plate'] for r in rs} == {'liuren', 'qimen', 'ziwei'}


def test_no_drift():
    for rec in rows():
        if rec['plate'] == 'liuren':
            got = gp.liuren_snapshot(rec['at'])
        elif rec['plate'] == 'qimen':
            got = gp.qimen_snapshot(rec['at'])
        else:
            got = gp.ziwei_snapshot(rec['birth'], rec['gender'])
        for k, want in rec['expect'].items():
            assert got.get(k) == want, f"{rec['plate']} {rec.get('at') or rec.get('birth')} . {k}"


def test_liuren_san_chuan_is_three():
    for rec in rows():
        if rec['plate'] == 'liuren':
            assert len(rec['expect']['san_chuan']) == 3
            assert len(rec['expect']['tian_di_pan']) == 12


def test_qimen_has_nine_palaces():
    for rec in rows():
        if rec['plate'] == 'qimen':
            assert len(rec['expect']['palaces']) == 9
            assert 1 <= rec['expect']['zhifu_gong'] <= 9


def test_ziwei_sihua_is_four():
    for rec in rows():
        if rec['plate'] == 'ziwei':
            assert len(rec['expect']['sihua']) == 4
            assert len(rec['expect']['palaces']) == 12
