"""夏令时：中国 1986–1991 年实行过，很多排盘软件不处理，时柱会错一位。

这里不硬编码日期，直接用 IANA tzdata（Windows 上靠 tzdata 包）算：
某一天的偏移量、以及某一年里的起止窗口，都从时区库现读。

为什么重要：tianzhi-core 把 naive 时间一律当「东八区法定时」理解。
落在夏令时区间里的出生时间，钟表比标准时快一小时；不换算，时柱可能整位错。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

CN = 'Asia/Shanghai'


def _z(tz: str) -> ZoneInfo:
    return ZoneInfo(tz)


def dst_offset(dt: datetime, tz: str = CN) -> timedelta:
    """这一刻的夏令时偏移。0 或 1 小时（极少数地区 30 分钟）。"""
    return dt.replace(tzinfo=_z(tz)).dst() or timedelta(0)


def in_dst(dt: datetime, tz: str = CN) -> bool:
    return dst_offset(dt, tz) != timedelta(0)


@lru_cache(maxsize=8)
def windows(tz: str = CN, y0: int = 1900, y1: int = 2035) -> tuple[tuple[datetime, datetime], ...]:
    """扫出 tz 在 [y0, y1] 里的夏令时窗口。

    时刻统一折算成该地「标准时」（以当年一月的偏移为准），所以 1986 那一档读作
    1986-05-04 02:00 → 1986-09-14 02:00，跟常见年表一致；不是墙钟上跳变的那一格。
    按天扫、命中的日子再逐小时收窄，几十万天也只要零点几秒，且只算一次。
    """
    z = _z(tz)
    out: list[tuple[datetime, datetime]] = []
    open_at: datetime | None = None
    day = date(y0, 1, 1)
    end = date(y1, 12, 31)
    prev = False
    while day <= end:
        cur = datetime(day.year, day.month, day.day, 12, tzinfo=z).dst() != timedelta(0)
        if cur != prev:
            hour = 0
            while hour < 24:
                at = datetime(day.year, day.month, day.day, hour, tzinfo=z)
                if (at.dst() != timedelta(0)) == cur:
                    break
                hour += 1
            at = datetime(day.year, day.month, day.day, hour, tzinfo=z)
            # 折算成当地标准时：先落到 UTC，再加上当年一月的偏移
            std = datetime(day.year, 1, 15, 12, tzinfo=z).utcoffset() or timedelta(0)
            stamp = at.astimezone(ZoneInfo('UTC')).replace(tzinfo=None) + std
            if cur:
                open_at = stamp
            elif open_at is not None:
                out.append((open_at, stamp))
                open_at = None
            prev = cur
        day += timedelta(days=1)
    return tuple(out)


def warning(dt: datetime, tz: str = CN) -> dict | None:
    """生辰落在夏令时窗口里就给一条警告，否则 None。"""
    off = dst_offset(dt, tz)
    if not off:
        return None
    return {
        'kind': 'dst',
        'offset_minutes': int(off.total_seconds() // 60),
        'text': (f'{dt:%Y-%m-%d %H:%M} 落在 {tz} 的夏令时区间内，钟表比标准时快 '
                 f'{int(off.total_seconds() // 60)} 分钟。如果填的是当时的钟表时间，'
                 f'按法定时应减去这段时间；时柱可能因此差一位。'),
    }
