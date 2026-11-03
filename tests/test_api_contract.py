"""API 契约：前端依赖的字段，不许悄悄消失或换类型。

这些断言不为「算得对」负责（那是 golden 与对表的事），只为「说好的形状不变」。
"""
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server.app as app_module  # noqa: E402
import server.audit as audit_module  # noqa: E402

BIRTH = '1996-04-18 14:06'


@pytest.fixture()
def _local_client_placeholder():
    """客户端夹具已移到 tests/conftest.py，这里保留占位以免误改。"""
    return None


def test_health(client):
    d = client.get('/api/health').json()
    assert set(d) == {'ok', 'mock', 'model', 'utc'}
    assert d['ok'] is True


def test_now_schema(client):
    d = client.get('/api/now?longitude=114.93').json()
    for k in ('clock_bj', 'clock_local', 'true_solar', 'month_zhi', 'bazi',
              'siling', 'correction_minutes', 'days_after_jie', 'upcoming_jieqi'):
        assert k in d, k
    assert set(d['place']) >= {'longitude', 'latitude', 'standard_longitude'}
    assert set(d['jie']) == {'name', 'at'}
    assert set(d['next_jie']) == {'name', 'at'}
    assert set(d['term']) == {'name', 'at', 'index', 'next'}
    assert 0 <= d['term']['index'] < 24
    assert d['term']['name'] in ('立春', '雨水', '惊蛰', '春分', '清明', '谷雨', '立夏', '小满',
                                 '芒种', '夏至', '小暑', '大暑', '立秋', '处暑', '白露', '秋分',
                                 '寒露', '霜降', '立冬', '小雪', '大雪', '冬至', '小寒', '大寒')
    assert len(d['bazi'].split()) == 4
    assert set(d['sidereal']) >= {'lst_deg', 'lst_hms', 'xiu'}
    assert set(d['sidereal']['xiu']) >= {'index', 'name', 'start', 'end', 'width'}
    assert set(d['moon']) == {'elong_deg', 'name', 'illum', 'waxing', 'age_days'}


def test_chart_schema(client):
    d = client.get(f'/api/chart?birth={BIRTH}&longitude=114.93').json()
    for k in ('input', 'place', 'bazi', 'quad', 'siling', 'true_solar', 'strength',
              'geju', 'yongshen', 'dayun', 'current', 'warnings'):
        assert k in d, k
    assert d['bazi'] == '丙子 壬辰 乙酉 癸未'
    assert set(d['strength']) >= {'label', 'ratio', 'support', 'drain', 'net', 'items'}
    assert d['strength']['items'] and {'source', 'gan', 'relation', 'side', 'score'} <= set(d['strength']['items'][0])
    assert set(d['geju']) >= {'name', 'basis', 'evidence'}
    assert set(d['yongshen']) >= {'yong', 'xi', 'ji', 'chou', 'method', 'evidence'}
    assert set(d['current']) >= {'year_gz', 'dayun', 'score', 'breakdown'}
    assert set(d['dayun'][0]) >= {'pillar', 'start_age', 'start_year', 'end_year'}
    assert isinstance(d['warnings'], list)


def test_chart_overseas_shifts_effective_longitude(client):
    d = client.get(f'/api/chart?birth={BIRTH}&longitude=139.69&standard_longitude=135').json()
    assert d['place']['standard_longitude'] == 135
    assert d['place']['effective_longitude'] == pytest.approx(124.69, abs=0.01)


def test_compare_schema(client):
    d = client.get(f'/api/compare?birth=1996-04-18 15:05&longitude=114.93').json()
    assert set(d) == {'input', 'variants', 'diff'}
    assert len(d['variants']) == 4
    keys = [v['key'] for v in d['variants']]
    assert keys[0] == 'baseline'
    for v in d['variants']:
        assert {'key', 'label', 'note', 'params', 'bazi', 'strength', 'geju',
                'yong', 'xi', 'ji', 'method', 'evidence'} <= set(v)
    for row in d['diff']:
        assert set(row) == {'field', 'key', 'values', 'changed_by'}
        assert set(row['values']) == set(keys)


def _sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for frame in text.split('\n\n'):
        ev = None
        data = None
        for line in frame.splitlines():
            if line.startswith('event: '):
                ev = line[7:].strip()
            elif line.startswith('data: '):
                data = line[6:]
        if ev and data:
            out.append((ev, json.loads(data)))
    return out


def test_chat_meta_contract(client):
    r = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': '现在什么节气'}],
                                       'birth': BIRTH, 'place': {'longitude': 114.93}})
    assert r.status_code == 200
    events = _sse(r.text)
    kinds = [e for e, _ in events]
    assert kinds[0] == 'meta'
    meta = events[0][1]
    for k in ('id', 'now', 'chart', 'warnings', 'evidence', 'focus', 'risk', 'mock'):
        assert k in meta, k
    assert meta['chart'] == '丙子 壬辰 乙酉 癸未'
    assert meta['focus']['ring'] == '二十四节气'
    assert any(g['layer'] == '用神' for g in meta['evidence'])
    assert 'done' in kinds


def test_chat_bad_birth_does_not_500(client):
    r = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': '看看'}],
                                       'birth': '不是时间'})
    assert r.status_code == 200
    meta = _sse(r.text)[0][1]
    assert meta['chart'] is None


def test_calendar_schema(client):
    d = client.get('/api/calendar?year=2026').json()
    assert d['year'] == 2026
    assert len(d['terms']) == 24
    names = [t['name'] for t in d['terms']]
    assert names[0] == '小寒' and names[-1] == '冬至'
    assert names[2] == '立春'
    for t in d['terms']:
        assert set(t) == {'name', 'at', 'ring_index'}
        assert 0 <= t['ring_index'] < 24
        assert len(t['at']) == 19
    # 按时间先后排
    stamps = [t['at'] for t in d['terms']]
    assert stamps == sorted(stamps)
    # ring_index 用的是「立春为 0」那套
    assert next(t for t in d['terms'] if t['name'] == '立春')['ring_index'] == 0
    assert next(t for t in d['terms'] if t['name'] == '大寒')['ring_index'] == 23


def test_liuren_schema(client):
    d = client.get('/api/liuren?at=2026-11-03 01:30').json()
    for k in ('ganzhi', 'yue_jiang', 'zhan_shi', 'tian_di_pan', 'tian_jiang_map',
              'four_classes', 'three_chuan', 'keti', 'bifa'):
        assert k in d, k
    assert len(d['tian_di_pan']) == 12
    assert d['yue_jiang'] == '卯' and d['zhan_shi'] == '丑'
    # 卯将加丑时：丑宫坐卯，子宫坐寅
    assert d['tian_di_pan']['丑'] == '卯'
    assert d['tian_di_pan']['子'] == '寅'
    assert [d['three_chuan'][k]['zhi'] for k in ('chu', 'zhong', 'mo')] == ['寅', '辰', '午']
    assert len(d['four_classes']) == 4


def test_qimen_schema(client):
    d = client.get('/api/qimen?at=2026-11-03 15:00').json()
    for k in ('sizhu', 'ju', 'pan', 'geju', 'kong', 'ma'):
        assert k in d, k
    assert set(d['sizhu']) == {'year', 'month', 'day', 'hour'}
    assert {'jieqi', 'yuan', 'dun', 'ju', 'mode'} <= set(d['ju'])
    assert len(d['pan']['palaces']) == 9
    assert set(d['pan']) >= {'zhifu', 'zhishi', 'zhifu_gong', 'zhishi_gong', 'palaces'}
    for g, p in d['pan']['palaces'].items():
        assert set(p) >= {'di', 'tian', 'star', 'door', 'shen'}
    assert isinstance(d['geju'], list)
    if d['geju']:
        assert {'name', 'verdict', 'gong'} <= set(d['geju'][0])


def test_ziwei_schema(client):
    d = client.get('/api/ziwei?birth=1996-04-18 13:46&gender=0').json()
    for k in ('ming', 'shen', 'ju', 'ju_name', 'ming_zhu', 'shen_zhu', 'palaces'):
        assert k in d, k
    assert len(d['palaces']) == 12
    assert {p['zhi'] for p in d['palaces']} == set('子丑寅卯辰巳午未申酉戌亥')
    assert d['ming'] in set('子丑寅卯辰巳午未申酉戌亥')
    # 生年四化挂在星上，正好四颗，禄权科忌各一
    hua = [s['hua'] for p in d['palaces'] for s in p['stars'] if s.get('hua')]
    assert sorted(hua) == sorted(['禄', '权', '科', '忌'])
    for p in d['palaces']:
        assert {'zhi', 'gan', 'name', 'stars', 'is_shen'} <= set(p)


def test_passage_schema(client):
    d = client.get('/api/passage?cite=穷通宝鉴·乙日辰月').json()
    assert d['found'] is True
    for k in ('cite', 'title', 'loc', 'quote', 'gloss', 'verdict', 'source'):
        assert k in d, k
    miss = client.get('/api/passage?cite=不存在的东西').json()
    assert miss['found'] is False and 'reason' in miss


def test_bifa_schema(client):
    d = client.get('/api/liuren/bifa?no=1').json()
    assert d['found'] is True
    assert d['verse'] == '前後引從陞遷吉'
    assert set(d) >= {'no', 'verse', 'vol', 'commentary', 'edition', 'source'}
    miss = client.get('/api/liuren/bifa?no=999').json()
    assert miss['found'] is False


def test_ziwei_passage_schema(client):
    d = client.get('/api/ziwei/passage?palace=命宫&stars=紫微').json()
    assert d['found'] is True
    assert d['palace'] == '命宫' and d['star'] == '紫微'
    assert d['text'] and d['source']
    miss = client.get('/api/ziwei/passage?palace=命宫&stars=不存在').json()
    assert miss['found'] is False


def test_qimen_passage_schema(client):
    d = client.get('/api/qimen/passage?cite=遁甲演義·卷二|地遁').json()
    assert d['found'] is True
    assert d['chapter'] == '地遁' and d['vol'] == 2
    assert d['text'] and d['source']
    miss = client.get('/api/qimen/passage?cite=遁甲演義·卷二|没有这篇').json()
    assert miss['found'] is False


def test_year_schema(client):
    d = client.get('/api/year?birth=1996-04-18 14:06&year=2026').json()
    for k in ('year_gz', 'bazi', 'day_master', 'dayun', 'score', 'months'):
        assert k in d, k
    assert len(d['months']) == 12
    assert d['months'][0]['jie'] == '立春'
    assert set(d['months'][0]) >= {'zhi', 'gz', 'jie', 'at', 'ten_god'}
    assert set(d['score']) >= {'value', 'stance', 'ten_god'}
    # 紫微那一半也在同一份报告里
    assert set(d['ziwei']) >= {'age', 'daxian', 'liunian', 'xiaoxian', 'sihua', 'ming'}
    assert len(d['ziwei']['sihua']) == 4


def test_bad_input_is_400_not_500(client):
    """用户打错时间格式，是 400；500 留给真正的服务端故障。"""
    for url in ('/api/chart?birth=bad', '/api/year?birth=bad', '/api/liuren?at=bad',
                '/api/qimen?at=bad', '/api/ziwei?birth=bad'):
        r = client.get(url)
        assert r.status_code == 400, (url, r.status_code)


def test_api_index(client):
    d = client.get('/api').json()
    assert d['version'] and d['docs'] == '/api/docs'
    assert d['examples'] == '/API.md'
    assert len(d['endpoints']) >= 15
    assert {e['tag'] for e in d['endpoints']} == {'读数', '盘', '报告', '原文', '璇玑', '运维'}
    assert '不预测' in d['boundary']


def test_openapi_is_documented(client):
    o = client.get('/api/openapi.json').json()
    assert o['info']['title'].startswith('周天')
    assert o['info']['description']
    assert [t['name'] for t in o['tags']] == ['读数', '盘', '报告', '原文', '璇玑', '运维']
    for path, ops in o['paths'].items():
        for method, op in ops.items():
            assert op.get('summary'), f'{path} 缺 summary'
            assert op.get('tags'), f'{path} 缺 tag'


def test_swagger_page_served(client):
    assert client.get('/api/docs').status_code == 200
    assert client.get('/docs').status_code == 404   # 旧的路径已挪到 /api/docs


def test_unknown_route_404(client):
    assert client.get('/api/nope').status_code == 404
