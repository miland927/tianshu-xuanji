"""黄金集：三十个必须算出同样结果的生辰。

它管两件事：
  1. 回归——库或我们的封装改了，输出漂了，这里立刻红。
  2. 覆盖——闰月、早晚子时、真太阳时跨时辰、夏令时、海外、跨年、闰日。

它不管「对不对」。对不对由 `tools/verify_calendar.py`（节气对表，独立实现）与人工核对负责。
快照只保证「没变」，不保证「正确」——这两件事写在这里，免得以后有人拿它当真理。

用法：
  .venv\\Scripts\\python.exe tools\\golden.py --freeze    # 写 eval/golden.jsonl
  .venv\\Scripts\\python.exe tools\\golden.py --check     # 比对，漂了就退出码 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.cal import chart_snapshot  # noqa: E402

GOLDEN = ROOT / 'eval' / 'golden.jsonl'

# id: (生辰, 经度, 性别, 覆盖点)
CASES = {
    'readme':        ('1996-04-18 14:06', 114.93, 0, 120, '上游 README 的例子'),
    'dst_1990':      ('1990-06-01 12:00', 114.93, 0, 120, '中国夏令时区间内'),
    'dst_1988_zi':   ('1988-07-15 03:30', 121.47, 1, 120, '夏令时 + 早子时'),
    'late_zi_2330':  ('1997-08-15 23:50', 113.26, 0, 120, '晚子时（归哪一天看流派）'),
    'late_zi_0005':  ('2000-01-01 00:30', 116.40, 1, 120, '跨年 + 深夜'),
    'lichun_2020':   ('2020-02-04 17:03', 116.40, 0, 120, '立春当刻，年柱换不换就在这一刻'),
    'lichun_2021':   ('2021-02-03 22:58', 116.40, 0, 120, '立春前一小时'),
    'jiazhi_1984':   ('1984-02-02 00:10', 113.26, 0, 120, '甲子年开头'),
    'leap_2016':     ('2016-02-29 12:00', 114.93, 1, 120, '闰日'),
    'leap_2004':     ('2004-02-29 23:59', 120.00, 0, 120, '闰日 + 晚子'),
    'urumqi':        ('2023-03-22 09:00', 87.62, 0, 120, '真太阳时大偏移（西陲，仍用东八区时）'),
    'tokyo':         ('2023-06-21 12:00', 139.69, 1, 135, '海外：东京，标准经线 135'),
    'newyork':       ('2023-06-21 12:00', -74.00, 0, -75, '海外：纽约，标准经线 -75'),
    'tokyo_no_std':  ('2023-06-21 12:00', 139.69, 1, 120, '海外但给了错的标准经线（应出警告）'),
    'year_1900':     ('1900-01-01 12:00', 116.40, 0, 120, '下边界年'),
    'year_2050':     ('2050-12-31 23:59', 116.40, 1, 120, '上边界年'),
    'solstice':      ('2024-06-21 04:50', 116.40, 0, 120, '夏至前后'),
    'winter_sol':    ('2024-12-21 17:20', 116.40, 0, 120, '冬至前后'),
    'qingming':      ('2025-04-04 20:48', 116.40, 0, 120, '清明当刻'),
    'jingzhe':       ('2025-03-05 16:07', 116.40, 0, 120, '惊蛰当刻'),
    'early_zi':      ('1995-11-11 00:20', 121.47, 1, 120, '早子时（23:00–01:00 的另一半）'),
    'noon':          ('1988-08-08 12:00', 120.00, 0, 120, '正午，真太阳时接近上中天'),
    'night_zi':      ('1988-08-08 23:30', 120.00, 0, 120, '夜子时，与 noon 同日'),
    'swing_lon':     ('2001-09-09 08:30', 75.99, 1, 120, '经度极端西，时柱易跨位'),
    'swing_lon_e':   ('2001-09-09 08:30', 134.00, 0, 120, '经度极端东，时柱易跨位'),
    'twin_a':        ('2010-10-10 10:10', 114.93, 0, 120, '双胞胎 A（男）'),
    'twin_b':        ('2010-10-10 10:10', 114.93, 1, 120, '双胞胎 B（女，只影响大运顺逆）'),
    'dst_edge_in':   ('1991-04-14 02:30', 116.40, 0, 120, '夏令时开始当刻'),
    'dst_edge_out':  ('1991-09-15 01:30', 116.40, 0, 120, '夏令时结束当刻'),
    'century':       ('2000-01-01 00:00', 116.40, 0, 120, '整点世纪交界'),
    'dst_1987':      ('1987-06-01 09:00', 121.47, 1, 120, '夏令时另一年'),
    'dst_after_end': ('1991-09-15 02:30', 116.40, 0, 120, '夏令时结束当刻之后'),
    'london':        ('2023-06-21 12:00', -0.13, 0, 0.0, '伦敦，标准经线 0'),
    'los_angeles':   ('2023-06-21 12:00', -118.24, 1, -120.0, '洛杉矶，标准经线 -120'),
    'sydney':        ('2023-06-21 12:00', 151.20, 0, 150.0, '悉尼，标准经线 150'),
    'kathmandu':     ('2023-06-21 12:00', 85.32, 0, 82.5, '加德满都，UTC+5:45 的怪经线'),
    'lichun_2030':   ('2030-02-04 00:00', 116.40, 0, 120, '立春前后另一段'),
    'y2038':         ('2038-01-19 03:14', 116.40, 0, 120, '32 位时间边界'),
    'leap_2000':     ('2000-02-29 12:00', 116.40, 1, 120, '世纪闰日'),
    'late_zi_nye':   ('1999-12-31 23:59', 116.40, 0, 120, '跨年晚子时'),
    'solstice_noon': ('2026-06-21 12:00', 116.40, 0, 120, '夏至正午'),
}


def snapshot(birth: str, lon: float, gender: int, std: float = 120.0) -> dict:
    c = chart_snapshot(birth, lon, gender, standard_longitude=std)
    return {
        'bazi': c['bazi'],
        'true_solar': c['true_solar'],
        'siling': c['siling'],
        'strength': c['strength']['label'],
        'geju': c['geju']['name'],
        'yong': c['yongshen']['yong'],
        'warnings': [w['kind'] for w in c.get('warnings', [])],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--freeze', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    if args.freeze:
        GOLDEN.parent.mkdir(exist_ok=True)
        with GOLDEN.open('w', encoding='utf-8') as f:
            for cid, (birth, lon, gender, std, note) in CASES.items():
                rec = {'id': cid, 'birth': birth, 'longitude': lon, 'gender': gender,
                       'standard_longitude': std, 'note': note,
                       'expect': snapshot(birth, lon, gender, std)}
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print(f'已冻结 {len(CASES)} 例 → {GOLDEN}')
        return 0

    if not GOLDEN.exists():
        print('还没有 golden.jsonl，先跑 --freeze')
        return 1

    drift = 0
    for line in GOLDEN.read_text(encoding='utf-8').splitlines():
        rec = json.loads(line)
        got = snapshot(rec['birth'], rec['longitude'], rec['gender'],
                       rec.get('standard_longitude', 120.0))
        for k, want in rec['expect'].items():
            if got.get(k) != want:
                drift += 1
                print(f"漂移 {rec['id']}.{k}: 期望 {want!r} 实得 {got.get(k)!r}")
    print(f'比对 {len(CASES)} 例：{"全部一致" if not drift else f"{drift} 处漂移"}')
    return 0 if not drift else 1


if __name__ == '__main__':
    raise SystemExit(main())
