"""恒星时与二十八宿：让星宿环对得上此刻的天。

两件事：
1. 当地恒星时（LST）——此刻哪一段赤经正落在子午线上。
2. 二十八宿的赤经分界——把 LST 落到某一宿。

口径（写在前面，免得当成精算）：
- 恒星时用 Meeus 12.4 的平恒星时，未加章动（差 < 1.3 秒 ≈ 0.005°，对分宿无影响）。
- 二十八宿用古籍的「距度」（周天 365¼ 古度），折算成现代度 = 距度 × 360/365.25。
- 起点取角宿距星「角宿一」（Spica）的 J2000 赤经 201.30°，**未做岁差改正**——
  古表距度本身也是某个历元的，两者混用只保证「大致对」，不保证逐度精确。
  要做精，得先定历元、再逐宿改正岁差，那是另一个工程量。
"""
from __future__ import annotations

from datetime import datetime, timezone

J2000 = 2451545.0

# 二十八宿距度（古度，周天 365.25）。数值取通行本，各界略有出入。
XIU = [
    ('角', 12.00), ('亢', 9.00), ('氐', 15.00), ('房', 5.00), ('心', 5.00), ('尾', 18.00),
    ('箕', 11.25), ('斗', 26.25), ('牛', 8.00), ('女', 12.00), ('虚', 10.00), ('危', 17.00),
    ('室', 16.00), ('壁', 9.00), ('奎', 16.00), ('娄', 12.00), ('胃', 14.00), ('昴', 11.00),
    ('毕', 16.00), ('觜', 2.00), ('参', 9.00), ('井', 33.00), ('鬼', 4.00), ('柳', 15.00),
    ('星', 7.00), ('张', 18.00), ('翼', 18.00), ('轸', 17.00),
]

XI_START_DEG = 201.2983          # 角宿一（Spica）J2000 赤经
ANCIENT_FULL = 365.25            # 古度周天
TO_MODERN = 360.0 / ANCIENT_FULL

# 通行本距度合计 365.5 古度，比周天多 0.25——各家传本本就有出入。
# 处理办法：按合计归一，保证二十八段首尾相接、不重叠（不假装那是精确的古度）。
_TOTAL = sum(w for _, w in XIU)


def widths() -> list[float]:
    return [w * 360.0 / _TOTAL for _, w in XIU]


def julian_date(dt_utc: datetime) -> float:
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_utc = dt_utc.astimezone(timezone.utc)
    epoch = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    return J2000 + (dt_utc - epoch).total_seconds() / 86400.0


def gmst_deg(jd: float) -> float:
    """格林尼治平恒星时（度）。Meeus, Astronomical Algorithms, 12.4。"""
    t = (jd - J2000) / 36525.0
    theta = (280.46061837 + 360.98564736629 * (jd - J2000)
             + 0.000387933 * t * t - t * t * t / 38710000.0)
    return theta % 360.0


def lst_deg(dt_utc: datetime, longitude: float) -> float:
    """当地恒星时（度）。东经为正。"""
    return (gmst_deg(julian_date(dt_utc)) + longitude) % 360.0


def spans() -> list[dict]:
    """各宿的赤经区间（现代度），从角宿起点开始顺次排。"""
    out, start = [], XI_START_DEG
    for (name, _ancient), width in zip(XIU, widths()):
        out.append({'name': name, 'start': round(start % 360, 3), 'end': round((start + width) % 360, 3),
                    'width': round(width, 3)})
        start += width
    return out


def xiu_at(lst: float) -> dict:
    """这一刻子午线落在哪一宿。"""
    offset = (lst - XI_START_DEG) % 360.0
    acc = 0.0
    for i, ((name, _ancient), width) in enumerate(zip(XIU, widths())):
        if acc <= offset < acc + width:
            return {'index': i, 'name': name, 'start': round((XI_START_DEG + acc) % 360, 3),
                    'end': round((XI_START_DEG + acc + width) % 360, 3),
                    'into': round(offset - acc, 3), 'width': round(width, 3)}
        acc += width
    return {'index': len(XIU) - 1, 'name': XIU[-1][0], 'start': 0.0, 'end': 0.0, 'into': 0.0, 'width': 0.0}


def hms(deg: float) -> str:
    hours = deg / 15.0
    h = int(hours)
    m = int((hours - h) * 60)
    s = ((hours - h) * 60 - m) * 60
    return f'{h:02d}h{m:02d}m{s:04.1f}s'
