"""月相：日月黄经差。

只为读数条上一格，不需要精确星历——差 0.1° 换算成时间不到 15 分钟，
而月相是按 45° 一档命名的，这个精度足够。

公式取 Meeus《Astronomical Algorithms》的截断式（太阳第 25 章、月亮第 47 章主项）。
不是全天候精密星历：真要做精密月相时刻，得上 ELP2000 或 JPL DE。
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

D2R = math.pi / 180.0

PHASES = [
    (0.0, '新月'), (22.5, '蛾眉月'), (67.5, '上弦'), (112.5, '盈凸'),
    (157.5, '满月'), (202.5, '亏凸'), (247.5, '下弦'), (292.5, '残月'), (337.5, '新月'),
]

SYNODIC = 29.530588853   # 朔望月，天


def _julian_centuries(dt_utc: datetime) -> float:
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_utc = dt_utc.astimezone(timezone.utc)
    jd = 2451545.0 + (dt_utc - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400.0
    return (jd - 2451545.0) / 36525.0


def sun_longitude(t: float) -> float:
    """太阳视黄经（度）。Meeus 25.x 简化式，精度约 0.01°。"""
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m * D2R)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m * D2R)
         + 0.000289 * math.sin(3 * m * D2R))
    omega = 125.04 - 1934.136 * t
    return (l0 + c - 0.00569 - 0.00478 * math.sin(omega * D2R)) % 360.0


def moon_longitude(t: float) -> float:
    """月亮视黄经（度）。Meeus 47 主项，精度约 0.05°。"""
    lp = 218.3164477 + 481267.88123421 * t - 0.0015786 * t * t
    d = 297.8501921 + 445267.1114034 * t - 0.0018819 * t * t
    m = 357.5291092 + 35999.0502909 * t - 0.0001536 * t * t
    mp = 134.9633964 + 477198.8675055 * t + 0.0087414 * t * t
    f = 93.2720950 + 483202.0175233 * t - 0.0036539 * t * t

    s = (6.288774 * math.sin(mp * D2R)
         + 1.274027 * math.sin((2 * d - mp) * D2R)
         + 0.658314 * math.sin(2 * d * D2R)
         + 0.213618 * math.sin(2 * mp * D2R)
         - 0.185116 * math.sin(m * D2R)
         - 0.114332 * math.sin(2 * f * D2R)
         + 0.058793 * math.sin((2 * d - 2 * mp) * D2R)
         + 0.057066 * math.sin((2 * d - m - mp) * D2R)
         + 0.053322 * math.sin((2 * d + mp) * D2R)
         + 0.045758 * math.sin((2 * d - m) * D2R)
         - 0.040923 * math.sin((m - mp) * D2R))
    return (lp + s) % 360.0


def elongation(dt_utc: datetime) -> float:
    """日月黄经差（0–360）。0 新月、180 满月、90 上弦。"""
    t = _julian_centuries(dt_utc)
    return (moon_longitude(t) - sun_longitude(t)) % 360.0


def phase_name(elong: float) -> str:
    e = elong % 360.0
    for start, name in reversed(PHASES):
        if e >= start:
            return name
    return PHASES[0][1]


def snapshot(dt_utc: datetime) -> dict:
    e = elongation(dt_utc)
    illum = (1 - math.cos(e * D2R)) / 2
    name = phase_name(e)
    return {
        'elong_deg': round(e, 2),
        'name': name,
        'illum': round(illum, 4),
        'waxing': e < 180.0,
        'age_days': round(e / 360.0 * SYNODIC, 2),
    }


def _g(dt: datetime, target: float) -> float:
    """(target - 黄经差) 折到 (-180, 180]；黄经差递增，所以它单调递减，交点即目标时刻。"""
    return ((target - elongation(dt) + 180.0) % 360.0) - 180.0


def _solve(a: datetime, b: datetime, target: float) -> datetime:
    for _ in range(32):
        mid = a + (b - a) / 2
        if _g(mid, target) > 0:
            a = mid
        else:
            b = mid
        if (b - a).total_seconds() < 1:
            break
    return a + (b - a) / 2


def year_events(year: int) -> list[dict]:
    """某公历年的朔（新月）与望（满月）时刻，东八区 naive。

    内部按 UTC 扫（黄经公式吃 UTC），出结果再 +8 小时；扫描窗口前后各放宽，
    免得年界附近的朔望被切掉，最后按东八区的年份筛。
    """
    t0 = datetime(year - 1, 12, 31)
    t1 = datetime(year + 1, 1, 2)
    out: list[dict] = []
    for kind, target in (('朔', 0.0), ('望', 180.0)):
        t = t0
        prev = _g(t, target)
        while t < t1:
            nxt = t + timedelta(hours=6)
            cur = _g(nxt, target)
            if prev > 0 >= cur:
                bj = _solve(t, nxt, target) + timedelta(hours=8)
                if bj.year == year:
                    out.append({'kind': kind, 'at': bj})
            prev, t = cur, nxt
    out.sort(key=lambda e: e['at'])
    return out
