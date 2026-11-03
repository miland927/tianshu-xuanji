"""换一派：同一张盘，换一组口径重算，把差异摊在一张表上。

不做「哪个对」的判断——只把分歧点、两边取值、以及为什么分歧列出来。
流派是参数，不是真理；这里的作用是让人看见参数在哪。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from tianzhi_core.bazi import chart, geju, strength, yongshen

from .cal import BEIJING, effective_longitude

# 三个真实存在的分歧点，各自都有典籍依据
VARIANTS: list[dict[str, Any]] = [
    {
        'key': 'baseline',
        'label': '默认口径',
        'note': '晚子时归次日（与多数排盘软件一致）、按真太阳时、用神取法按「格局→扶抑→通关→病药→调候」',
        'params': {'late_zi': 'next_day', 'use_true_solar': True,
                   'priority': ('格局', '扶抑', '通关', '病药', '调候')},
    },
    {
        'key': 'late_zi_same_day',
        'label': '夜子时归当日',
        'note': '23:00 之后仍算当日的日柱，只把时柱记作夜子时——古法一派',
        'params': {'late_zi': 'same_day', 'use_true_solar': True,
                   'priority': ('格局', '扶抑', '通关', '病药', '调候')},
    },
    {
        'key': 'no_true_solar',
        'label': '不校正真太阳时',
        'note': '按钟表时间直接排，不扣经度与均时差——有些软件与流派如此',
        'params': {'late_zi': 'next_day', 'use_true_solar': False,
                   'priority': ('格局', '扶抑', '通关', '病药', '调候')},
    },
    {
        'key': 'fuyi_first',
        'label': '用神先扶抑',
        'note': '取用次序改为「扶抑→格局→通关→病药→调候」，强弱优先于格局',
        'params': {'late_zi': 'next_day', 'use_true_solar': True,
                   'priority': ('扶抑', '格局', '通关', '病药', '调候')},
    },
]

FIELDS = [('四柱', 'bazi'), ('旺衰', 'strength'), ('格局', 'geju'), ('用神', 'yong'),
          ('喜', 'xi'), ('忌', 'ji'), ('取用方法', 'method')]


def _one(birth: str, longitude: float, gender: int, std: float, params: dict) -> dict:
    dt = datetime.strptime(birth.strip().replace('T', ' '), '%Y-%m-%d %H:%M')
    lam = effective_longitude(longitude, std)
    c = chart.build_chart(dt, longitude=lam, gender=gender,
                          late_zi=params['late_zi'], use_true_solar=params['use_true_solar'])
    s = strength.day_master_strength(c.quad, month_siling=c.siling)
    g = geju.month_pattern(c.quad, month_siling=c.siling)
    y = yongshen.select(c.quad, month_siling=c.siling, priority=params['priority'])
    return {
        'bazi': c.bazi,
        'strength': f"{s.label} {s.ratio:.3f}",
        'geju': g.name,
        'yong': y.yong, 'xi': y.xi, 'ji': y.ji,
        'method': y.method,
        'evidence': list(y.evidence),
    }


def compare(birth: str, longitude: float = 114.93, gender: int = 0,
            standard_longitude: float = BEIJING) -> dict:
    variants = []
    for v in VARIANTS:
        row = {'key': v['key'], 'label': v['label'], 'note': v['note'],
               'params': {k: (list(p) if isinstance(p, tuple) else p) for k, p in v['params'].items()}}
        row.update(_one(birth, longitude, gender, standard_longitude, v['params']))
        variants.append(row)

    base = variants[0]
    diff = []
    for field, key in FIELDS:
        values = {v['key']: v[key] for v in variants}
        if len(set(map(str, values.values()))) > 1:
            diff.append({'field': field, 'key': key, 'values': values,
                         'changed_by': [v['label'] for v in variants[1:] if str(v[key]) != str(base[key])]})

    return {'input': {'birth': birth, 'longitude': longitude, 'gender': gender,
                      'standard_longitude': standard_longitude},
            'variants': variants, 'diff': diff}
