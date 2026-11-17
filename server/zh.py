"""给模型看的读数一律用中文。

排盘库的字段名是英文（support、ten_god……），说明串里也夹着 year/month/day/hour
（「day支未藏丁」「zhi.冲.month|午冲month支子」）。模型会原样抄进回答，古雅口吻里冒出
英文和统计数字，最伤沉浸感（走查 P1-2）。

两道：
    model_view(ctx)   发给模型前，键名和说明串整体换成中文
    scrub(text)       模型输出再过一遍，漏网的字段名就地换掉（兜底，不指望它）
"""
from __future__ import annotations

import re

POS = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}

KEYS = {
    # 此刻
    'now': '此刻', 'clock_bj': '北京时间', 'clock_local': '当地钟表', 'true_solar': '真太阳时',
    'correction_minutes': '校正分钟', 'equation_of_time': '均时差', 'month_zhi': '月建',
    'jie': '所在节', 'next_jie': '下一个节', 'term': '节气', 'days_after_jie': '交节后天数',
    'upcoming_jieqi': '将到节气', 'sidereal': '恒星时', 'lst_deg': '地方恒星时度数', 'lst_hms': '地方恒星时',
    'xiu': '中天宿', 'moon': '月相', 'age_days': '月龄天数', 'age_meaning': '月龄含义', 'illum': '亮面比例',
    'waxing': '渐盈', 'elong_deg': '日月角距', 'sunrise_sunset': '日出日落', 'is_daytime': '是否白天',
    # 盘
    'chart': '盘', 'input': '输入', 'birth': '生辰', 'gender': '性别', 'place': '出生地',
    'longitude': '经度', 'latitude': '纬度', 'standard_longitude': '时区经线',
    'effective_longitude': '折算经度', 'bazi': '四柱', 'hour_known': '时辰已知', 'quad': '四柱分列',
    'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱',
    'siling': '司令', 'siling_shishen': '司令十神',
    'strength': '旺衰', 'label': '结论', 'ratio': '扶抑比', 'support': '生扶', 'drain': '克泄耗',
    'net': '净值', 'has_root': '有根', 'items': '明细', 'pos': '位置', 'side': '方向',
    'source': '来源', 'weight': '权重', 'value': '分值',
    'geju': '格局', 'yongshen': '用神', 'yong': '用神', 'xi': '喜神', 'ji': '忌神',
    'method': '取法', 'evidence': '判据', 'basis': '依据', 'rule': '规则', 'tags': '标签',
    'dayun': '大运', 'pillar': '干支', 'start_age': '起岁', 'end_age': '止岁',
    'start_year': '起年', 'end_year': '止年', 'current': '今年', 'year_gz': '流年',
    'score': '流年分', 'breakdown': '流年分明细', 'ten_god': '十神', 'stance': '定调',
    'qiyun': '起运', 'forward': '顺排', 'anchor': '对照节', 'days': '天数', 'toward': '方向',
    'library_age': '起运岁数', 'note': '说明',
    'warnings': '提示', 'kind': '类别', 'text': '内容', 'offset_minutes': '偏差分钟',
    'name': '名称', 'at': '时刻', 'start': '起', 'end': '止', 'span': '跨度', 'width': '宽度',
    'index': '序号', 'gan': '天干', 'zhi': '地支', 'relation': '关系', 'into': '化为',
    'base': '基数', 'chou': '丑', 'xian': '弦', 'next': '下一个', 'jieqi': '节气',
    # 对话上下文
    'risk': '风险', 'gender_label': '性别', 'gender_note': '性别说明', 'chart_error': '排盘出错',
    'transparent_at': '透出位置',
}

VALUES = {
    'support': '生扶', 'drain': '克泄耗', 'dst': '夏令时', 'hour_unknown': '时辰不详', 'tz': '时区',
    'year': '年', 'month': '月', 'day': '日', 'hour': '时',
}

# 流年分明细的键：「zhi.冲.month|午冲month支子」→「地支冲·午冲月支子」
BREAK = {'dayun_gan': '大运干', 'dayun_zhi': '大运支', 'year_gan': '流年干', 'year_zhi': '流年支',
         'ten_god': '十神', 'group': '合局', 'gan': '天干', 'zhi': '地支'}

_POS_IN_TEXT = re.compile(r'(?<![A-Za-z_])(year|month|day|hour)(?![A-Za-z_])')
_DOTTED = re.compile(r'(?<![A-Za-z_])(gan|zhi|group)\.([一-鿿]+)(?:\.(year|month|day|hour))?(?![A-Za-z_])')
_WORDS = re.compile(r'(?<![A-Za-z_])(' + '|'.join(sorted(
    (k for k in set(KEYS) | set(BREAK) if len(k) >= 3), key=len, reverse=True)) + r')(?![A-Za-z_])')


def text(s: str) -> str:
    """一段中文里夹的英文字段名换成中文。纯日期、纯数字不动。"""
    if not s or not re.search(r'[A-Za-z]', s):
        return s
    s = s.replace('Asia/Shanghai', '东八区')
    s = _DOTTED.sub(lambda m: f"{BREAK[m.group(1)]}{m.group(2)}" + (f"{POS[m.group(3)]}" if m.group(3) else ''), s)
    s = _POS_IN_TEXT.sub(lambda m: POS[m.group(1)], s)
    s = _WORDS.sub(lambda m: BREAK.get(m.group(1)) or KEYS[m.group(1)], s)
    return s


def _key(k: str) -> str:
    if '|' in k:
        head, tail = k.split('|', 1)
        return f'{text(head)}·{text(tail)}'
    return KEYS.get(k) or text(k)


def model_view(x):
    """递归换成中文：键名、枚举值、说明串。数值原样保留。"""
    if isinstance(x, dict):
        return {_key(str(k)): model_view(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [model_view(v) for v in x]
    if isinstance(x, bool):
        return '是' if x else '否'
    if isinstance(x, str):
        return VALUES.get(x) or text(x)
    return x


def scrub(s: str) -> str:
    """模型输出的兜底：漏出来的字段名就地换成中文。只换认得的，不碰别的英文。"""
    return text(s)
