"""年度报告：一张盘在某一年（立春 → 立春）的十二个月。

月份排列按节气走，不按公历：寅月自立春起，丑月至次年小寒止。
月干用五虎遁（甲己之年丙作首…）推，不从流月表抄——两处能互相对上才是对的。
"""
from __future__ import annotations

from datetime import datetime

from tianzhi_core.bazi import chart, luck_cycle, score, ten_god, yongshen

from . import cal

GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'

# 五虎遁：年干 → 寅月的月干
YIN_GAN = {'甲': '丙', '己': '丙', '乙': '戊', '庚': '戊', '丙': '庚', '辛': '庚',
           '丁': '壬', '壬': '壬', '戊': '甲', '癸': '甲'}

JIE_TO_ZHI = {'立春': '寅', '惊蛰': '卯', '清明': '辰', '立夏': '巳', '芒种': '午', '小暑': '未',
              '立秋': '申', '白露': '酉', '寒露': '戌', '立冬': '亥', '大雪': '子', '小寒': '丑'}


def month_ganzhi(year_gan: str, offset: int) -> str:
    """寅月为 0。五虎遁推月干，支从寅顺行。"""
    start = GAN.index(YIN_GAN[year_gan])
    return GAN[(start + offset) % 10] + ZHI[(2 + offset) % 12]


def _terms_for_flow_year(year: int) -> list[dict]:
    """取「立春→次年小寒」这十二个节。"""
    this = [x for x in cal.calendar_year(year)['terms'] if x['name'] in JIE_TO_ZHI]
    nxt = [x for x in cal.calendar_year(year + 1)['terms'] if x['name'] == '小寒']
    picked = [x for x in this if x['name'] != '小寒'] + nxt[:1]
    picked.sort(key=lambda x: x['at'])
    return picked


def year_report(birth: str, year: int, gender: int = 0,
                longitude: float = 114.93, standard_longitude: float = 120.0) -> dict:
    snap = cal.chart_snapshot(birth, longitude, gender, standard_longitude)
    dt = datetime.strptime(birth.strip().replace('T', ' '), '%Y-%m-%d %H:%M')
    lam = cal.effective_longitude(longitude, standard_longitude)
    c = chart.build_chart(dt, longitude=lam, gender=gender)
    day_gan = c.bazi.split()[2][0]

    # 该年的流年干支：以立春后的年份为准，用当年年中取一次盘
    probe = chart.build_chart(datetime(year, 6, 1, 12), longitude=lam, gender=gender)
    year_gz = ''.join(probe.quad['year'])
    year_gan = year_gz[0]

    dayun = luck_cycle.dayun_list(c)
    dy = next((d for d in dayun if d.start_year <= year <= d.end_year), None)
    y = yongshen.select(c.quad, month_siling=c.siling)
    sc = score.score_year(c.quad, year_gz,
                          dayun_gz=f'{dy.pillar.gan}{dy.pillar.zhi}' if dy else None,
                          favorable=y.favorable, unfavorable=y.unfavorable)

    months = []
    for i, t in enumerate(_terms_for_flow_year(year)):
        gz = month_ganzhi(year_gan, i)
        months.append({
            'index': i + 1,
            'zhi': gz[1],
            'gz': gz,
            'jie': t['name'],
            'at': t['at'],
            'ten_god': ten_god(day_gan, gz[0]),
            'dayun': f'{dy.pillar.gan}{dy.pillar.zhi}' if dy else None,
        })

    # 紫微那边也算一份「今年」：大限宫、流年宫、小限、流年四化。
    # 两份都在这一页给出，省得用户在两页之间对年份。
    ziwei_part = None
    try:
        from . import ziwei_year

        ziwei_part = ziwei_year.year_view(birth, gender, year)
    except Exception as e:  # 紫微排不出来不该拖垮年度报告
        ziwei_part = {'error': f'{type(e).__name__}: {e}'}

    return {
        'input': {'birth': birth, 'gender': gender, 'year': year},
        'year': year,
        'year_gz': year_gz,
        'bazi': c.bazi,
        'day_master': day_gan,
        'dayun': {'pillar': f'{dy.pillar.gan}{dy.pillar.zhi}', 'start_age': dy.start_age,
                  'end_age': dy.end_age, 'start_year': dy.start_year, 'end_year': dy.end_year}
        if dy else None,
        'score': {'value': sc.score, 'stance': sc.stance, 'ten_god': sc.ten_god,
                  'breakdown': dict(sc.breakdown or {})},
        'months': months,
        'ziwei': ziwei_part,
        'source': '立春起算；月干以五虎遁推；月建按节气；紫微流年取 build_chart 的 daxian/xiaoxian',
    }


def yongshen_fav(snap: dict) -> list[str]:
    y = (snap.get('yongshen') or {})
    return list(y.get('favorable') or [])


def yongshen_unfav(snap: dict) -> list[str]:
    y = (snap.get('yongshen') or {})
    return list(y.get('unfavorable') or [])
