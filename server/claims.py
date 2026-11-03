"""核对一段话里的事实性断言：四柱、节气、旺衰、用神、比例数值。

用途：模型说的话里，凡是能算的部分都该与库的输出一致。这里只做「对账」，
不判断话说得好不好——那是人的事。

单位是「条断言」：抽出模型写了什么，逐条与真值比，返回不一致的地方。
"""
from __future__ import annotations

import re

GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI = '子丑寅卯辰巳午未申酉戌亥'
JIEQI = ['立春', '雨水', '惊蛰', '春分', '清明', '谷雨', '立夏', '小满', '芒种', '夏至',
         '小暑', '大暑', '立秋', '处暑', '白露', '秋分', '寒露', '霜降', '立冬', '小雪',
         '大雪', '冬至', '小寒', '大寒']
WANG_SHUAI = ['身旺', '偏旺', '中和', '偏弱', '身弱']
WUXING = '木火土金水'

GZ = re.compile(f'[{GAN}][{ZHI}]')
NUM = re.compile(r'0\.\d{3,4}')


def truth(now: dict, chart: dict | None = None) -> dict:
    """从 /api/now 与 /api/chart 的返回里取真值。

    节气的「可接受集合」有四个来源：当月的**节**（月建用）、此刻的**节气**（含中气）、
    下一个节气、以及**本命月建的节**（说「月建辰，清明后」是对的）。
    因为一段话里说「寒露后二十五日」「此刻霜降」「你生在辰月清明后」都对。
    """
    term = now.get('term') or {}
    t = {'term': term.get('name'),
         'next': (term.get('next') or {}).get('name'),
         'jie': (now.get('jie') or {}).get('name'),
         'month_zhi': now.get('month_zhi'),
         'bazi_now': now.get('bazi')}
    if chart:
        t['bazi'] = chart.get('bazi')
        t['strength'] = (chart.get('strength') or {}).get('label')
        t['ratio'] = (chart.get('strength') or {}).get('ratio')
        t['geju'] = (chart.get('geju') or {}).get('name')
        t['yong'] = (chart.get('yongshen') or {}).get('yong')
        t['birth_jie'] = month_jie(chart.get('bazi'))
        t['birth_next_jie'] = next_jie(chart.get('bazi'))
    return t


#: 十二节与月支的对应（节气→月建）
JIE_OF_ZHI = {'寅': '立春', '卯': '惊蛰', '辰': '清明', '巳': '立夏', '午': '芒种', '未': '小暑',
              '申': '立秋', '酉': '白露', '戌': '寒露', '亥': '立冬', '子': '大雪', '丑': '小寒'}


def month_jie(bazi: str | None) -> str | None:
    """本命月柱的地支 → 管它的那个「节」。用来避免把「月建辰，清明后」判成错。"""
    if not bazi:
        return None
    parts = bazi.split()
    if len(parts) < 2 or len(parts[1]) < 2:
        return None
    return JIE_OF_ZHI.get(parts[1][1])


def next_jie(bazi: str | None) -> str | None:
    """本命月建之后的下一个节（辰月 → 立夏）。说「下一节是立夏」是对的。"""
    if not bazi:
        return None
    parts = bazi.split()
    if len(parts) < 2 or len(parts[1]) < 2:
        return None
    zhi = parts[1][1]
    order = list(JIE_OF_ZHI)
    if zhi not in order:
        return None
    return JIE_OF_ZHI[order[(order.index(zhi) + 1) % len(order)]]


def extract(text: str) -> dict:
    """把一段话里的事实断言抽出来。抽到什么算什么，抽不到就不查。"""
    out: dict = {}
    # 四柱必须是「连续四个干支」且**前面紧挨着四柱标记**才算断言。
    # 散文里说「乙酉日、壬辰月」，或讲大运序列「辛卯、庚寅、己丑、戊子」，都不算。
    for run in re.finditer('(?:[' + GAN + '][' + ZHI + '])(?:[ \\t、,，]{1,2}[' + GAN + '][' + ZHI + ']){3}',
                           text or ''):
        lead = (text or '')[max(0, run.start() - 10):run.start()]
        if not re.search(r'四柱|八字|生辰|排得|排出来|排为|盘[:：]', lead):
            continue
        out['bazi'] = ' '.join(GZ.findall(run.group(0))[:4])
        break
    # 节气只有跟在「此刻/现在/月建/本月/下一节」后面才算断言。
    # 散文里举例说「一个节到一个节」「立夏小雪」不是在报节气，不能被判错。
    sentences = re.split(r'[。！？!?\n]', text or '')
    terms = []
    for s in sentences:
        if re.search(r'此刻|现在|今天|今日|当下|月建|本月|下一节|这个节|该节', s):
            terms += [x for x in JIEQI if x in s]
    if terms:
        out['terms'] = sorted(set(terms))
    # 旺衰标签要带上下文才算断言：「水偏旺」是在说五行偏旺，不是给日主定性。
    for m in re.finditer(r'(?:旺衰|判为|标为|定为|评为)\s*[·:：为]?\s*(身旺|偏旺|中和|偏弱|身弱)',
                         text or ''):
        out.setdefault('strength', []).append(m.group(1))
    m = re.search(r'用\s*[神]?\s*[取为是:：]?\s*([' + WUXING + '])', text or '')
    if m:
        out['yong'] = m.group(1)
    # 比例只在「ratio/比例/比值」附近才算断言：别把宿度（入10.847度）当成分数
    for m in re.finditer(r'(?:ratio|比例|比值)\s*[:：为=]?\s*(\d\.\d{2,4})', text or '', re.I):
        out.setdefault('nums', []).append(m.group(1))
    return out


def verify(text: str, t: dict) -> list[dict]:
    """返回不一致清单；空列表表示这段话里能查的都查过了、都对。"""
    got = extract(text)
    bad: list[dict] = []

    if 'bazi' in got:
        # 一段话里的四柱可能指「这张盘」，也可能指「此刻」——对上任何一个都算对
        pool = [x for x in (t.get('bazi'), t.get('bazi_now')) if x]
        if pool and got['bazi'].replace(' ', '') not in [x.replace(' ', '') for x in pool]:
            bad.append({'kind': '四柱', 'claim': got['bazi'], 'expected': ' / '.join(pool)})

    if 'terms' in got:
        allowed = {x for x in (t.get('term'), t.get('jie'), t.get('next'),
                               t.get('birth_jie'), t.get('birth_next_jie')) if x}
        extra = [x for x in got['terms'] if x not in allowed]
        if extra:
            bad.append({'kind': '节气', 'claim': '、'.join(extra), 'expected': '、'.join(sorted(allowed))})

    if 'strength' in got and t.get('strength'):
        # 真值已经说出来了就不再挑刺：散文里写「身弱」并不等于把标签报错
        if t['strength'] not in got['strength']:
            bad.append({'kind': '旺衰', 'claim': '、'.join(got['strength']), 'expected': t['strength']})

    if 'yong' in got and t.get('yong'):
        if got['yong'] != t['yong']:
            bad.append({'kind': '用神', 'claim': got['yong'], 'expected': t['yong']})

    if 'nums' in got and t.get('ratio') is not None:
        want = f"{t['ratio']:.4f}".rstrip('0').rstrip('.')
        if not any(n == want or n.startswith(want[:6]) for n in got['nums']):
            bad.append({'kind': '比例', 'claim': '、'.join(got['nums']), 'expected': want})

    return bad
