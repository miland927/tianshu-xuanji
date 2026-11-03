"""出口校验器：模型说的话，在送到用户眼前之前过一遍。

三层拦截的第三层。前两层（入口识别、系统约束）靠关键词与 prompt，都可能被绕过；
这一层不看模型怎么想，只看它说出了什么。

两种用法：
    check(text, context)            # 整段，事后校验
    g = StreamGuard(context)        # 逐段，流式校验
    safe, bad = g.push(chunk)
    safe, bad = g.flush()
"""
from __future__ import annotations

import re

# 数据集里真实存在的典籍（tianzhi-classics 的目录）。引用超出这个集合，视为编造。
ALLOWED_BOOKS = {
    '穷通宝鉴', '穷通寶鑑', '栏江网', '造化元钥', '金不换', '子平真诠', '滴天髓',
    '神峰通考', '三命通会', '渊海子平', '协纪辨方书', '钦定协纪辨方书',
    '六壬大全', '紫微斗数全书', '遁甲演义', '古今图书集成',
    '尚书', '史记', '汉书', '淮南子', '周易', '道德经',
}

BOOK_RE = re.compile(r'《([^》\n]{1,24})》')
# 解释语境需要两个条件同时成立：既是否认（不是/没有/推不出…），又在谈「读数的边界」
# （字段、判据、盘上、编、范围…）。只有否认不算——「这句没有句号但含有大凶」不能被放过。
DENIAL = re.compile(r'没有|没这|不是|不算|不看|不说|不预测|不提|谈不上|推不出|对不上|读不出|不能|'
                    r'不该|不敢|不引|不写|不编|不做|无法|查不到|无据|未见|不知道|不在|就是编|而是|只读|只能读|'
                    r'旧说|古书|照录|背书|不替它')
META = re.compile(r'读数|字段|判据|盘上|盘里|evidence|quote|src|编|判断|范围|依据|相书|结构|术语|象|'
                  r'关系|位置|问法|仪器|词')

#: 引号里的词是「提及」，不是「断言」：「克夫」这种问题我不答 ≠ 你有克夫之相
QUOTED = re.compile(r'「[^」]*」|『[^』]*』|“[^”]*”|"[^"]*"')

FIX = {
    'advice': '这一条我不答。不是我能给建议的范围——盘上的象可以说，决定要你自己做。',
    'predict': '具体事件我不预测。能说的是这一层的结构与节奏，说不准的是吉凶。',
    'scare': '这类词我不用。它除了吓人，什么也说明不了。',
    'cite': '（这条出处我没有依据，不引。）',
}

# 顺序即优先级：越界最重，其次预测，其次恐吓，最后引用。
RULES = [
    ('advice', re.compile(
        r'(建议|劝)你(去|做|买|卖|投|找|吃|停|签|加仓|减仓|抄底|梭哈|贷款|离婚|分手)|'
        r'你(应该|最好|不如|赶紧|马上)(去|买|卖|投|吃|停|签|做|加仓|减仓)|'
        r'(可以|不如|赶紧)(买|卖|投|加仓|减仓|抄底|梭哈|贷款)|'
        r'(适合|宜|不宜)(买|卖|投|加仓|减仓|抄底|梭哈|贷款|入手|上车|持有)|'
        r'(去|到)(医院|法院|律师|诊所)看|'
        r'(吃|停)药|做手术|签合同|离婚吧|分手吧')),
    ('predict', re.compile(
        r'(今年|明年|后年|这年|那一年|下个月|这个月|\d{4}年).{0,12}(会|将|必然|一定)(升职|结婚|离婚|发财|破财|生病|去世|失业|考上|中奖|生子|搬家)|'
        r'(必|一定|肯定|注定)(会|要|能)(升|结|离|发|破|生|死|成|败|中)|'
        r'(会|将)在.{0,8}(结婚|离婚|去世|发病|出事)|'
        r'活到.{0,6}岁|寿元.{0,6}岁')),
    ('scare', re.compile(
        r'大凶|必死|血光之灾|灾祸|绝症|回天乏术|克夫|克妻|克子|断子绝孙|横死|凶死')),
]


def _split(text: str) -> list[str]:
    """按句切，保留标点。句末标点与换行都算边界。"""
    out, buf = [], ''
    for ch in text:
        buf += ch
        if ch in '。！？!?\n':
            out.append(buf)
            buf = ''
    if buf:
        out.append(buf)
    return out


#: 只有「在引」的语境才校验书名：带引号，或跟着云/曰/原文/载/说。
#: 光提一句「《逸周书·时训解》是七十二候最早的成文系统」是书目陈述，不是编出处。
QUOTING = re.compile(r'「[^」]*」|『[^』]*』|“[^”]*”|"[^"]*"|云|曰|原文|载|说|称')


def _cite_bad(sentence: str) -> str | None:
    # 先看是不是「否认语境」：模型说「这本书我没有依据，不引」时，
    # 提书名恰恰是对的。不认这一条，就会把守规矩的回答当成违规改掉。
    if DENIAL.search(sentence):
        return None
    if not QUOTING.search(sentence):
        return None
    for m in BOOK_RE.finditer(sentence):
        name = m.group(1).strip()
        # 「《全书》卷三」这种简称也放过：只校验书名主体
        base = name.split('·')[0].split('卷')[0].strip()
        if base and base not in ALLOWED_BOOKS:
            return base
    return None


def check(text: str) -> tuple[str, list[dict]]:
    """整段校验，返回（清洗后的文本, 违规清单）。"""
    violations: list[dict] = []
    kept: list[str] = []
    for sentence in _split(text):
        if not sentence.strip():
            kept.append(sentence)
            continue
        # 解释语境的句子整句放过：模型在说「这不是绝症」「推不出寿数」「查不到出处」，
        # 恰恰是守则希望它做的。误杀这类句子，会把好回答改成一句干巴巴的模板。
        if DENIAL.search(sentence) and META.search(sentence):
            kept.append(sentence)
            continue
        kind = None
        probe = QUOTED.sub('', sentence)   # 引号内的词只算「提及」
        for k, rx in RULES:
            if rx.search(probe):
                kind = k
                break
        if kind is None:
            bad = _cite_bad(sentence)
            if bad:
                violations.append({'kind': 'cite', 'hit': bad, 'sentence': sentence.strip()[:120]})
                kept.append(FIX['cite'])
                continue
            kept.append(sentence)
        else:
            violations.append({'kind': kind, 'hit': _hit(sentence), 'sentence': sentence.strip()[:120]})
            kept.append(FIX[kind])
    return ''.join(kept), violations


def _hit(sentence: str) -> str:
    for k, rx in RULES:
        m = rx.search(sentence)
        if m:
            return m.group(0)[:40]
    return ''


class StreamGuard:
    """流式版：攒到一句才判，判完再往前送。句子没说完就不送，避免半句被截断误判。"""

    def __init__(self) -> None:
        self.buf = ''
        self.violations: list[dict] = []

    def push(self, chunk: str) -> tuple[str, list[dict]]:
        self.buf += chunk
        cut = max(self.buf.rfind(c) for c in '。！？!?\n')
        if cut < 0:
            return '', []
        ready, self.buf = self.buf[:cut + 1], self.buf[cut + 1:]
        safe, bad = check(ready)
        self.violations.extend(bad)
        return safe, bad

    def flush(self) -> tuple[str, list[dict]]:
        safe, bad = check(self.buf)
        self.violations.extend(bad)
        self.buf = ''
        return safe, bad
