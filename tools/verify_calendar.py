"""历法对表：用另一套独立实现（pymeeus 的太阳视黄经）核 tianzhi-core 的节气时刻。

为什么这么核：tianzhi-core 底下的 lunar-python 与 pymeeus 是两套互不相干的实现。
两边对得上，才叫「对过表」；只跟自己对，叫自洽。

（试过 pyephem，但它的 ra/dec 是 astrometric，用作视黄经会差十几分钟——踩过这个坑，
留在这里免得下次再踩。pymeeus 在 2020 夏至那一刻给出 89.9993°，可以作参考。）

跑：
  .venv\\Scripts\\python.exe tools\\verify_calendar.py --from 2010 --to 2035
产出：
  eval/calendar-check.md（误差表）
"""
from __future__ import annotations

import argparse
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymeeus.Epoch import Epoch
from pymeeus.Sun import Sun

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tianzhi_core.calendar.jieqi import jieqi_table  # noqa: E402

# 太阳视黄经 → 节气（每 15° 一个）
TERMS = {
    315: '立春', 330: '雨水', 345: '惊蛰', 0: '春分', 15: '清明', 30: '谷雨',
    45: '立夏', 60: '小满', 75: '芒种', 90: '夏至', 105: '小暑', 120: '大暑',
    135: '立秋', 150: '处暑', 165: '白露', 180: '秋分', 195: '寒露', 210: '霜降',
    225: '立冬', 240: '小雪', 255: '大雪', 270: '冬至', 285: '小寒', 300: '大寒',
}


def sun_lon(dt_utc: datetime) -> float:
    """太阳视黄经（度），地心视位置，瞬时黄道。"""
    frac = (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
            + dt_utc.microsecond / 3.6e9) / 24
    e = Epoch(dt_utc.year, dt_utc.month, dt_utc.day + frac)
    lon, _lat, _r = Sun.apparent_geocentric_position(e)
    return float(lon) % 360.0


def solve(dt_a: datetime, dt_b: datetime, target: float) -> datetime:
    """二分：g(t) = ((target - lon) + 180) % 360 - 180 由正变负处即交点。"""
    def g(t):
        return ((target - sun_lon(t) + 180.0) % 360.0) - 180.0

    lo, hi = dt_a, dt_b
    for _ in range(30):
        mid = lo + (hi - lo) / 2
        if g(mid) > 0:
            lo = mid
        else:
            hi = mid
        if (hi - lo).total_seconds() < 0.5:
            break
    return lo + (hi - lo) / 2


def ref_terms(year: int) -> dict[str, datetime]:
    """某年 24 个节气的时刻（东八区 naive），与 tianzhi 的口径一致。

    注意 ΔT：pymeeus 的历表吃的是 TT，而这里要的是 UT（钟表时间）。
    不扣 ΔT 会整年偏六十多秒——踩过一次，记在此处。
    """
    out: dict[str, datetime] = {}
    t = datetime(year, 1, 1)
    end = datetime(year, 12, 31, 23)
    prev_l = sun_lon(t)
    while t < end:
        t2 = t + timedelta(days=1)
        l2 = sun_lon(t2)
        for target, name in TERMS.items():
            a = ((target - prev_l + 180) % 360) - 180
            b = ((target - l2 + 180) % 360) - 180
            if a > 0 >= b:  # 由正变负 = 跨过该黄经
                at = solve(t, t2, target)
                at -= timedelta(seconds=Epoch.tt2ut(at.year, at.month))
                bj = (at.replace(tzinfo=timezone.utc) + timedelta(hours=8)).replace(tzinfo=None)
                if bj.year == year:
                    out[name] = bj
        prev_l, t = l2, t2
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='y0', type=int, default=2010)
    ap.add_argument('--to', dest='y1', type=int, default=2035)
    args = ap.parse_args()

    diffs: list[tuple[int, str, float, datetime, datetime]] = []
    for year in range(args.y0, args.y1 + 1):
        mine = jieqi_table(year)
        ref = ref_terms(year)
        for name, at in mine.items():
            if name not in ref:
                continue
            diffs.append((year, name, (at - ref[name]).total_seconds(), at, ref[name]))
        print(f'  {year} ok', flush=True)

    if not diffs:
        print('没有可比的数据')
        return 1

    secs = [abs(d[2]) for d in diffs]
    worst = sorted(diffs, key=lambda x: -abs(x[2]))[:10]
    over1m = [d for d in diffs if abs(d[2]) > 60]
    over30s = [d for d in diffs if abs(d[2]) > 30]

    print(f'\n比对 {len(diffs)} 个节气时刻（{args.y0}–{args.y1}）')
    print(f'  平均 |差| {statistics.mean(secs):.2f} 秒 · 中位 {statistics.median(secs):.2f} 秒 · 最大 {max(secs):.1f} 秒')
    print(f'  >30 秒：{len(over30s)} 个    >60 秒：{len(over1m)} 个')
    for year, name, d, at, ref in worst:
        print(f'    {year} {name:3s} {d:+7.2f}s  库={at:%Y-%m-%d %H:%M:%S}  参考={ref:%Y-%m-%d %H:%M:%S}')

    out = ROOT / 'eval' / 'calendar-check.md'
    out.parent.mkdir(exist_ok=True)
    with out.open('w', encoding='utf-8') as f:
        f.write(f'# 节气对表（{args.y0}–{args.y1}）\n\n')
        f.write('参考实现：pymeeus 太阳视黄经（Meeus，与 lunar-python 无共同代码）。\n')
        f.write('口径：东八区钟表时间，与 `/api/now` 一致。\n\n')
        f.write(f'- 比对样本：{len(diffs)}\n')
        f.write(f'- 平均绝对误差：{statistics.mean(secs):.2f} 秒\n')
        f.write(f'- 最大绝对误差：{max(secs):.1f} 秒\n')
        f.write(f'- 超过 30 秒：{len(over30s)} 个；超过 60 秒：{len(over1m)} 个\n\n')
        f.write('| 年 | 节气 | 差（秒） | 库 | 参考 |\n|---:|---|---:|---|---|\n')
        for year, name, d, at, ref in worst:
            f.write(f'| {year} | {name} | {d:+.2f} | {at:%m-%d %H:%M:%S} | {ref:%m-%d %H:%M:%S} |\n')
    print(f'\n落盘：{out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
