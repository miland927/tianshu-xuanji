"""把 tianzhi-core 包成「此刻」与「一张盘」两件事。

这个文件是唯一允许出现排盘逻辑的地方：模型永远不许自己算，它只拿这里的 JSON。
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone

from tianzhi_core import ziwei
from tianzhi_core.bazi import chart, geju, luck_cycle, score, strength, yongshen
from tianzhi_core.calendar import jieqi, solar_time
from tianzhi_core.calendar.jieqi import as_naive

from . import dst, moon, sidereal

BEIJING = 120.0


def plain(x):
    if is_dataclass(x):
        return asdict(x)
    if isinstance(x, (list, tuple)):
        return [plain(i) for i in x]
    if isinstance(x, dict):
        return {k: plain(v) for k, v in x.items()}
    return x


def _fmt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S') if isinstance(dt, datetime) else dt


def effective_longitude(longitude: float, standard_longitude: float = BEIJING) -> float:
    """把「出生地标准时」折成库能吃的经度。

    tianzhi-core 内部一律按东八区理解钟表时间，再用 (λ-120)/15h 修正到真太阳时。
    要在东八区口径下得到当地的真太阳时 L+(lon-M)/15h，只需令
        λ_eff = lon + (120 - M)
    这是一行等价代换，不是近似：修正量 (λ_eff-120)/15 正好等于 (lon-M)/15。

    例：东京 lon=139.69, M=135 → λ_eff=124.69，修正 +18.8 分钟；
        而直接按 λ=139.69 会多修整整一小时（+78.8 分钟），时柱可能错一位。
    """
    return longitude + (BEIJING - standard_longitude)


def now_snapshot(longitude: float = 114.93, latitude: float = 22.54,
                 standard_longitude: float = BEIJING) -> dict:
    """此刻的天文与历法事实。全部由库算，前端只负责显示。"""
    now_utc = datetime.now(timezone.utc)
    clock = as_naive(now_utc)                      # 东八区钟表时间
    local = (now_utc + timedelta(hours=standard_longitude / 15)).replace(tzinfo=None)
    c = chart.build_chart(now_utc, longitude=longitude, gender=0)

    jie_name, jie_at = jieqi.month_jieqi(now_utc)
    next_name, next_at = jieqi.next_jie(now_utc)
    table = jieqi.jieqi_table(clock.year)
    upcoming = [(k, v) for k, v in table.items() if v >= clock][:4]

    # 「此刻是哪个节气」要算上中气，不能只看节——月建用的节（寒露）与节气（霜降）不是一回事。
    # 注意用列表：三年同名节气会互相覆盖，dict 合并会只剩最后一年。
    all_terms: list[tuple[str, datetime]] = []
    for y in (clock.year - 1, clock.year, clock.year + 1):
        all_terms.extend(jieqi.jieqi_table(y).items())
    past = sorted((kv for kv in all_terms if kv[1] <= clock), key=lambda kv: kv[1])
    future = sorted((kv for kv in all_terms if kv[1] > clock), key=lambda kv: kv[1])
    term = ({'name': past[-1][0], 'at': _fmt(past[-1][1]),
             'index': RING_ORDER.index(past[-1][0]) if past[-1][0] in RING_ORDER else None,
             'next': {'name': future[0][0], 'at': _fmt(future[0][1])} if future else None}
            if past else None)

    true_solar = solar_time.true_solar_time(local, longitude, standard_longitude=standard_longitude)
    sun = solar_time.sunrise_sunset(local, latitude, longitude, standard_longitude=standard_longitude)
    lst = sidereal.lst_deg(now_utc, longitude)
    xiu = sidereal.xiu_at(lst)

    return {
        'clock_bj': _fmt(clock),
        'clock_local': _fmt(local),
        'place': {'longitude': longitude, 'latitude': latitude, 'standard_longitude': standard_longitude},
        'true_solar': _fmt(true_solar),
        'correction_minutes': round(solar_time.correction_minutes(local, longitude,
                                                                 standard_longitude=standard_longitude), 1),
        'equation_of_time': round(solar_time.equation_of_time(local), 2),
        'month_zhi': jieqi.month_zhi(now_utc),
        'jie': {'name': jie_name, 'at': _fmt(jie_at)},
        'term': term,
        'next_jie': {'name': next_name, 'at': _fmt(next_at)},
        'days_after_jie': round(jieqi.days_after_jieqi(now_utc), 2),
        'upcoming_jieqi': [{'name': k, 'at': _fmt(v)} for k, v in upcoming],
        'bazi': c.bazi,
        'quad': plain(c.quad),
        'siling': c.siling,
        'siling_shishen': c.siling_shishen,
        'sunrise_sunset': [_fmt(sun[0]), _fmt(sun[1])] if sun else None,
        'is_daytime': solar_time.is_daytime(local, latitude, longitude, standard_longitude=standard_longitude),
        'sidereal': {'lst_deg': round(lst, 3), 'lst_hms': sidereal.hms(lst), 'xiu': xiu},
        'moon': moon.snapshot(now_utc),
    }


# 二十四节气按「立春为 0」排，与铜环、七十二候的次序一致
RING_ORDER = ['立春', '雨水', '惊蛰', '春分', '清明', '谷雨', '立夏', '小满', '芒种', '夏至',
              '小暑', '大暑', '立秋', '处暑', '白露', '秋分', '寒露', '霜降', '立冬', '小雪',
              '大雪', '冬至', '小寒', '大寒']


def calendar_year(year: int) -> dict:
    """某公历年的二十四节气表。

    两套顺序都给：`terms` 按公历年内的时间先后排（小寒在前），
    每项带 `ring_index`（立春为 0 的那套），前端用它去七十二候里切三候。
    """
    table = jieqi.jieqi_table(year)
    rows = []
    for i, name in enumerate(RING_ORDER):
        at = table.get(name)
        if at is None or at.year != year:
            continue
        rows.append({'name': name, 'at': _fmt(at), 'ring_index': i})
    rows.sort(key=lambda r: r['at'])
    return {'year': year, 'terms': rows}


def chart_snapshot(birth: str, longitude: float, gender: int = 0,
                   latitude: float = 22.54, with_ziwei: bool = False,
                   standard_longitude: float = BEIJING) -> dict:
    """一张盘：四柱 → 旺衰 → 格局 → 用神 → 大运 → 今年。

    birth 是**出生地钟表时间**（不是北京时间的换算值）。出生地所在时区的标准经线
    由 standard_longitude 给：中国 120，东京 135，纽约 -75。
    """
    dt = datetime.strptime(birth.strip().replace('T', ' '), '%Y-%m-%d %H:%M')
    lam = effective_longitude(longitude, standard_longitude)
    c = chart.build_chart(dt, longitude=lam, gender=gender)
    s = strength.day_master_strength(c.quad, month_siling=c.siling)
    g = geju.month_pattern(c.quad, month_siling=c.siling)
    y = yongshen.select(c.quad, month_siling=c.siling)
    dayun = luck_cycle.dayun_list(c)

    now = datetime.now(timezone.utc)
    nowc = chart.build_chart(now, longitude=lam, gender=gender)
    year_gz = ''.join(nowc.quad['year'])
    dy = next((d for d in dayun if d.start_year <= as_naive(now).year <= d.end_year), None)
    sc = score.score_year(c.quad, year_gz, dayun_gz=f'{dy.pillar.gan}{dy.pillar.zhi}' if dy else None,
                          favorable=y.favorable, unfavorable=y.unfavorable)

    out = {
        'input': {'birth': birth, 'longitude': longitude, 'gender': gender,
                  'standard_longitude': standard_longitude},
        'place': {'longitude': longitude, 'standard_longitude': standard_longitude,
                  'effective_longitude': round(lam, 4)},
        'bazi': c.bazi,
        'quad': plain(c.quad),
        'siling': c.siling,
        'true_solar': _fmt(c.solar),
        'strength': {'label': s.label, 'ratio': round(s.ratio, 4), 'support': s.support,
                     'drain': s.drain, 'net': s.net, 'has_root': s.has_root, 'items': plain(s.items)},
        'geju': plain(g),
        'yongshen': plain(y),
        'dayun': [{'pillar': f"{d.pillar.gan}{d.pillar.zhi}", 'start_age': d.start_age,
                   'end_age': d.end_age, 'start_year': d.start_year, 'end_year': d.end_year}
                  for d in dayun[:8]],
        'current': {'year_gz': year_gz, 'dayun': f'{dy.pillar.gan}{dy.pillar.zhi}' if dy else None,
                    'score': sc.score, 'breakdown': sc.breakdown, 'ten_god': sc.ten_god,
                    'stance': sc.stance},
        # 起运的验算材料：出生月的节、下一个节、天数，以及按「三日折一年」算出来的岁数。
        # 真跑时模型说过「读数没给立夏时刻，起运 6 岁我只照抄、不验算」——这一段就是给它验算的料。
        'qiyun': qiyun_note(c, dt, gender, dayun[0].start_age if dayun else None),
    }
    if with_ziwei:
        zw = ziwei.build_chart(dt, gender)
        out['ziwei'] = {'ming': zw['ming'], 'ju_name': zw['ju_name'], 'ming_zhu': zw['ming_zhu'],
                        'shen_zhu': zw['shen_zhu']}

    out['warnings'] = [w for w in (dst.warning(dt), _tz_warning(longitude, standard_longitude)) if w]
    return out


def qiyun_note(c, birth_dt, gender: int, library_age: float | None) -> dict:
    """起运的验算材料：出生月的节、下一个节、相隔天数，以及库给出的起运虚岁。

    这里**不给第二个起运岁数**。我先按连续天数折了一版，四个样本里两个与库差一岁——
    原因是库按「整日数 + 时辰数」折算（古法口径），我按连续小时数折算。
    两份实现不一致时，正确的做法不是把两个数都摆出来让人猜，而是给材料、给库的数、
    把差异的由来写清楚。
    """
    from tianzhi_core.calendar import jieqi

    yang_year = str(c.quad['year'][0]) in '甲丙戊庚壬'
    forward = (yang_year and gender == 0) or (not yang_year and gender == 1)
    prev_name, prev_at = jieqi.month_jieqi(birth_dt)
    next_name, next_at = jieqi.next_jie(birth_dt)

    if forward:
        days = (next_at - birth_dt).total_seconds() / 86400
        anchor = {'name': next_name, 'at': next_at.strftime('%Y-%m-%d %H:%M')}
        toward = '生日 → 下一个节'
    else:
        days = (birth_dt - prev_at).total_seconds() / 86400
        anchor = {'name': prev_name, 'at': prev_at.strftime('%Y-%m-%d %H:%M')}
        toward = '上一个节 → 生日'

    return {
        'forward': forward,
        'basis': '阳年男/阴年女顺排，阴年男/阳年女逆排',
        'anchor': anchor,
        'span': toward,
        'days': round(days, 2),
        'rule': '三日折一年，一日折四月，一时辰折十天',
        'library_age': library_age,
        'age_meaning': '虚岁：交运那年记作 交运年 − 出生年 + 1',
        'note': 'days 是连续天数；库按整日数加时辰数折算，边界上可能与连续折算差一岁，以 library_age 为准',
    }


def _tz_warning(longitude: float, standard_longitude: float) -> dict | None:
    """没给时区标准经线、经度又明显不在东八区时提醒一句。给了就不提醒。"""
    if standard_longitude != BEIJING:
        return None
    if 73.0 <= longitude <= 135.0:
        return None
    return {
        'kind': 'tz',
        'text': (f'经度 {longitude} 不在东八区（120°E 附近）。如果你填的是当地钟表时间，'
                 f'请把 standard_longitude 设成出生地的标准经线（东京 135、纽约 -75），'
                 f'否则时柱可能整位偏移。'),
    }
