"""对账：一段话里的事实断言，与库的输出比。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import claims  # noqa: E402
from server.cal import chart_snapshot, now_snapshot  # noqa: E402


def T():
    return claims.truth(now_snapshot(114.93), chart_snapshot('1996-04-18 14:06', 114.93, 0))


def kinds(bad):
    return [b['kind'] for b in bad]


def test_correct_answer_passes():
    text = ('月建戌，寒露后二十五日。盘：丙子 壬辰 乙酉 癸未；'
            '旺衰 中和（0.4525）；格 偏印格；用 土。')
    assert claims.verify(text, T()) == []


def test_now_pillars_are_also_truth():
    t = T()
    text = f"此刻四柱 {t['bazi_now']}，旺衰 中和。"
    assert claims.verify(text, t) == []


def test_wrong_strength_flagged():
    bad = claims.verify('旺衰 偏旺。', T())
    assert '旺衰' in kinds(bad)


def test_wrong_yong_flagged():
    bad = claims.verify('用 火。', T())
    assert '用神' in kinds(bad)


def test_wrong_pillars_flagged():
    bad = claims.verify('四柱 甲子 乙丑 丙寅 丁卯。', T())
    assert '四柱' in kinds(bad)


def test_bogus_jieqi_flagged():
    bad = claims.verify('现在是立春。', T())
    assert '节气' in kinds(bad)


def test_jie_and_term_both_acceptable():
    t = T()
    assert t['jie'] and t['term'] and t['jie'] != t['term']
    assert claims.verify(f"{t['jie']} 是本月之节，此刻 {t['term']}。", t) == []


def test_nothing_to_check_is_clean():
    assert claims.verify('今天天气不错。', T()) == []


def test_pillars_must_be_consecutive():
    # 真模型会逐项讲「乙酉日、壬辰月」——那不是报四柱，不能判错
    t = T()
    prose = '你报的生辰排得乙酉日、壬辰月，真太阳时13:46，落在未时。'
    assert claims.verify(prose, t) == []


def test_strength_prose_is_not_a_misquote():
    # 「旺衰·中和」后面又写「印重而身弱」——真值说了就不挑刺
    t = T()
    assert claims.verify('旺衰判为中和，印重而身弱，无根。', t) == []


def test_birth_month_jie_is_allowed():
    # 「月建辰，清明后」是对的：清明是辰月之节
    t = T()
    assert t['birth_jie'] == '清明'
    assert claims.verify('月建辰，清明后十二日。', t) == []
