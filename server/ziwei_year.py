"""紫微的「今年」：大限在哪个宫、流年落哪个宫、小限、流年四化。

不新算东西——大限与小限本来就写在 `build_chart` 的每个宫里（虚岁区间），
这里只是按年份去查表。流年四化用同一张生年四化表（丙年：天同禄、天机权、文昌科、廉贞忌）。
"""
from __future__ import annotations

from datetime import datetime

from tianzhi_core import ziwei
from tianzhi_core.ziwei.chart import SIHUA

HUA = ('禄', '权', '科', '忌')


def _age(birth_year: int, year: int) -> int:
    """虚岁：出生算一岁。跨立春的细节按公历年算，年报里已注明口径。"""
    return year - birth_year + 1


def year_view(birth: str, gender: int, year: int) -> dict:
    dt = datetime.strptime(birth.strip().replace('T', ' '), '%Y-%m-%d %H:%M')
    z = ziwei.build_chart(dt, gender)
    age = _age(dt.year, year)

    # 流年干支：用当年年中排一次盘取年柱（紫微本身按农历年，这里只借干支）
    from tianzhi_core.bazi import chart as bchart
    probe = bchart.build_chart(datetime(year, 6, 1, 12), gender=gender)
    year_gz = ''.join(probe.quad['year'])
    year_zhi = year_gz[1]

    pal = {p['zhi']: p for p in z['palaces']}

    daxian = next((p for p in z['palaces']
                   if p.get('daxian') and p['daxian'][0] <= age <= p['daxian'][1]), None)
    xiaoxian = next((p for p in z['palaces'] if age in (p.get('xiaoxian') or [])), None)
    liunian = pal.get(year_zhi)

    # 流年四化：星 → 所在宫
    stars_at = {}
    for p in z['palaces']:
        for s in p.get('stars') or []:
            stars_at.setdefault(s['name'], p)
    sihua = []
    for i, name in enumerate(SIHUA.get(year_gz[0], ())):
        p = stars_at.get(name)
        sihua.append({'hua': HUA[i], 'star': name,
                      'palace': p['name'] if p else '（此盘不见）',
                      'zhi': p['zhi'] if p else None})

    return {
        'input': {'birth': birth, 'gender': gender, 'year': year},
        'year': year,
        'year_gz': year_gz,
        'age': age,
        'ming': {'zhi': z['ming'], 'name': pal[z['ming']]['name']},
        'shen': {'zhi': z['shen'], 'name': pal[z['shen']]['name']},
        'ju_name': z['ju_name'],
        'forward': z['forward'],
        'daxian': {'zhi': daxian['zhi'], 'name': daxian['name'],
                   'range': list(daxian['daxian']), 'stars': _mains(daxian)} if daxian else None,
        'liunian': {'zhi': year_zhi, 'name': liunian['name'],
                    'stars': _mains(liunian)} if liunian else None,
        'xiaoxian': {'zhi': xiaoxian['zhi'], 'name': xiaoxian['name']} if xiaoxian else None,
        'sihua': sihua,
        'source': '大限/小限取 build_chart 各宫的 daxian/xiaoxian；流年四化按年干查 SIHUA',
    }


def _mains(p: dict) -> list[str]:
    return [s['name'] for s in (p.get('stars') or []) if s.get('kind') == 'main']
