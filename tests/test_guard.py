"""出口校验器的单元测试。跑：.venv\\Scripts\\python.exe -m pytest tests -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.guard import StreamGuard, check  # noqa: E402


def kinds(violations):
    return [v['kind'] for v in violations]


def test_normal_text_passes():
    text = '月建戌，寒露后二十五日。旺衰为中和，ratio 0.4525。'
    safe, bad = check(text)
    assert safe == text
    assert bad == []


def test_medical_advice_replaced():
    safe, bad = check('你今年犯病，建议你去做手术，别拖。')
    assert 'kind' in kinds(bad) or 'advice' in kinds(bad)
    assert '做手术' not in safe


def test_investment_advice_replaced():
    safe, bad = check('今年适合买基金。你不如加仓。')
    assert 'advice' in kinds(bad)
    assert '加仓' not in safe


def test_legal_advice_replaced():
    safe, bad = check('这个官司你最好去找律师。')
    assert 'advice' in kinds(bad)


def test_soft_investment_phrasing_replaced():
    safe, bad = check('今年适合抄底。')
    assert 'advice' in kinds(bad)
    safe, bad = check('宜入手，不宜持有。')
    assert 'advice' in kinds(bad)


def test_specific_prediction_replaced():
    safe, bad = check('2027年会升职，把握住。')
    assert 'predict' in kinds(bad)
    assert '升职' not in safe


def test_scare_words_replaced():
    safe, bad = check('此局大凶，恐有血光之灾。')
    assert 'scare' in kinds(bad)
    assert '大凶' not in safe


def test_known_book_citation_kept():
    text = '调候取土，见《穷通宝鉴》乙日辰月。'
    safe, bad = check(text)
    assert bad == []
    assert '《穷通宝鉴》' in safe


def test_unknown_book_citation_flagged():
    safe, bad = check('《玉匣记》云：此日不宜出行。')
    assert 'cite' in kinds(bad)
    assert '《玉匣记》' not in safe


def test_cite_refusal_is_not_a_violation():
    # 真模型第一轮就撞上的误杀：它在说「我没有这本书的依据，不引」
    for text in (
        '（这条出处我没有依据，不引。）没有 evidence、quote、src 支撑的书名和原句，我不写。',
        '《玉匣记》我查不到，引不出原句。',
        '《三命通会》不在我读的那几本书里，不敢替你补。',
    ):
        _, bad = check(text)
        assert bad == [], (text, bad)


def test_bibliographic_mention_is_not_a_citation():
    # 《逸周书·时训解》确实是七十二候最早的成文系统——这是书目陈述，不是编出处
    _, bad = check('《逸周书·时训解》是七十二候最早的成文系统，每候配一句物候。')
    assert bad == []


def test_fabricated_cite_still_caught():
    _, bad = check('《玉匣记》说：今日宜出行，忌动土。')
    assert bad and bad[0]['kind'] == 'cite'


def test_real_model_explanations_are_not_violations():
    # 这三句是真模型在 50 轮里写的原话，第一版规则全判成了违规
    for text in (
        '《麻衣神相》是相书，看的是形貌气色，不看八字。',
        '克夫这个问法，问的是女命官星与日主的关系，盘上对不上。',
        '病要看医生，盘上读不出绝症，我也不会拿它去断生死。',
    ):
        _, bad = check(text)
        assert bad == [], (text, bad)


def test_quoted_mention_is_not_an_assertion():
    # 真模型常把词括起来讨论：「克夫」这个问题本身不成立
    for text in (
        '「血光」这类词我不说，也不预测灾祸。',
        '至于「我是不是克夫」，这不是这台仪器能回答的，也不是该问的。',
    ):
        _, bad = check(text)
        assert bad == [], (text, bad)


def test_unquoted_scare_still_caught():
    _, bad = check('你这盘有大凶之象。')
    assert 'scare' in kinds(bad)


def test_stream_guard_buffers_until_sentence_end():
    g = StreamGuard()
    out, bad = g.push('2027年会')
    assert out == '' and bad == []
    out, bad = g.push('升职。后面再说。')
    assert '升职' not in out
    assert 'predict' in kinds(bad)
    assert '后面再说' in out


def test_stream_guard_flush_handles_tail():
    g = StreamGuard()
    g.push('这句没有句号但含有大凶')
    safe, bad = g.flush()
    assert '大凶' not in safe
    assert 'scare' in kinds(bad)
