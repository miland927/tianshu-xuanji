# 接一遍：周天 · 读数 API

这份文档的例子**都真跑过**——`tools/api_smoke.py` 会照着它一条条请求，失败就红。

- 文档（Swagger）：`/api/docs`　schema：`/api/openapi.json`　目录：`/api`
- 版本：`0.1.0`（字段若要改，先走 deprecation，不静默改）
- 数据来源：tianzhi-core（计算）、tianzhi-classics（原文，MIT）

---

## 先看边界

这是**传统文化研究与学习工具**：不预测具体事件、不判定吉凶、不给医疗/法律/投资建议。
所有「分数」都是「与用神顺逆」的折算，不是概率，也不能折算成任何现实事件的可能性。

口径：时间一律按**东八区钟表时间**解释；海外用 `standard_longitude`（当地标准经线）与
`longitude`（当地经度）做等价代换。节气按天文算法算，与 pymeeus 对过表；月相与 ephem 对过表。

---

## 通用约定

| 项 | 约定 |
|---|---|
| 时间 | `YYYY-MM-DD HH:MM`（东八区） |
| 经度 | 东经为正；中国默认 `114.93`（南京） |
| 性别 | `0` 男 / `1` 女（与 tianzhi-core 一致） |
| 错误 | 参数格式不对是 **400**（不是 500），正文 `{"detail": "..."}` |
| 查不到 | 原文接口返回 `{"found": false, "reason": "..."}`，不编造 |

---

## 读数

### 此刻

```bash
curl "http://127.0.0.1:8788/api/now?longitude=114.93"
```

```json
{
  "clock_bj": "2026-11-03 01:50:31",
  "bazi": "丙午 戊戌 辛巳 己丑",
  "month_zhi": "戌",
  "term": {"name": "霜降", "at": "2026-10-23 17:37:57", "index": 17,
           "next": {"name": "立冬", "at": "2026-11-07 17:52:05"}},
  "true_solar": "2026-11-03 01:46:35",
  "moon": {"elong_deg": 281.35, "name": "下弦", "illum": 0.4016, "waxing": false, "age_days": 23.08}
}
```

`month_zhi` 是**月建**（按节算，不是农历初一）；`true_solar` 是按经度校正后的真太阳时；
`moon.illum` 是照度（0–1）。

### 一年的节气与朔望

```bash
curl "http://127.0.0.1:8788/api/calendar?year=2026"
curl "http://127.0.0.1:8788/api/moon-calendar?year=2026"
```

`/api/calendar` 给 24 个节气的交节时刻与 `ring_index`；`/api/moon-calendar` 给当年 12–13 个朔、12–13 个望。

---

## 盘

### 八字

```bash
curl "http://127.0.0.1:8788/api/chart?birth=1996-04-18%2014:06&longitude=114.93&gender=0"
```

```json
{
  "bazi": "丙子 壬辰 乙酉 癸未",
  "strength": {"label": "中和", "ratio": 0.4525},
  "geju": {"name": "偏印格"},
  "yongshen": {"yong": "土", "...": "..."},
  "dayun": [{"pillar": "癸巳", "start_age": 6, "end_age": 15, "start_year": 2001, "end_year": 2010}]
}
```

### 大六壬

```bash
curl "http://127.0.0.1:8788/api/liuren?at=2026-11-03%2001:30"
```

```json
{"yue_jiang": "卯", "zhan_shi": "丑", "three_chuan": {"chu": {"zhi": "寅"}, "zhong": {"zhi": "辰"}, "mo": {"zhi": "午"}, "method": "遥克"}}
```

（上面为摘要，实际还含 `tian_di_pan` 十二格、`four_classes` 四课、`keti`、`bifa`。）

### 奇门 / 紫微

```bash
curl "http://127.0.0.1:8788/api/qimen?at=2026-11-03%2015:00"
curl "http://127.0.0.1:8788/api/ziwei?birth=1996-04-18%2014:06&gender=0"
```

奇门给 `ju`（节气/元/遁/局/定局）、`pan`（九宫、直符直使）、`geju`；
紫微给 `ming`/`shen`/`ju_name` 与十二宫（含星曜、庙旺、四化、大限）。

---

## 报告

```bash
curl "http://127.0.0.1:8788/api/year?birth=1996-04-18%2014:06&year=2026"
curl "http://127.0.0.1:8788/api/ziwei/year?birth=1996-04-18%2014:06&year=2026"
```

```json
{"year_gz": "丙午", "score": {"value": 59.6, "stance": "顺"},
 "months": [{"jie": "立春", "gz": "庚寅", "ten_god": "正财", "at": "2026-02-04 04:02:08"}]}
```

```json
{"year_gz": "丙午", "age": 31, "daxian": {"name": "福德", "range": [26, 35]},
 "liunian": {"name": "子女"},
 "sihua": [["禄", "天同", "疾厄"], ["权", "天机", "兄弟"], ["科", "文昌", "迁移"], ["忌", "廉贞", "官禄"]]}
```

年度报告按**立春**起算；紫微的 `age` 是虚岁，六岁前没起运时 `daxian` 为 `null`。

---

## 原文

四门各一个接口，查得到给原句，查不到给 `found: false` 与原因。

```bash
curl "http://127.0.0.1:8788/api/passage?cite=%E7%A9%B7%E9%80%9A%E5%AE%9D%E9%89%B4%C2%B7%E4%B9%99%E6%97%A5%E8%BE%B0%E6%9C%88"
curl "http://127.0.0.1:8788/api/liuren/bifa?no=52"
curl "http://127.0.0.1:8788/api/ziwei/passage?palace=%E5%91%BD%E5%AE%AB&stars=%E7%B4%AB%E5%BE%AE"
curl "http://127.0.0.1:8788/api/qimen/passage?cite=%E9%81%81%E7%94%B2%E6%BC%94%E7%BE%A9%C2%B7%E5%8D%B7%E4%BA%8C%7C%E9%9D%92%E9%BE%8D%E5%9B%9E%E9%A6%96"
```

```json
{"found": true, "cite": "穷通宝鉴·乙日辰月", "loc": "三春乙木 · 三月",
 "quote": "三月乙木，阳气愈炽，先癸后丙。", "verdict": "data_ok",
 "gloss": "三月阳气更盛，先取癸水，后用丙火。"}
```

奇门的 `cite` 直接用 `/api/qimen` 返回的 `geju[].cite`——**格名与篇名常不一致**
（青龙返首 / 青龍回首），以库给的 cite 为准。

---

## 璇玑（SSE）

```bash
curl -N -X POST "http://127.0.0.1:8788/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"此刻什么节气？"}],
       "birth":"1996-04-18 14:06","gender":0,
       "place":{"longitude":114.93,"latitude":30.59,"standard_longitude":120.0}}'
```

事件顺序：`meta` → `delta`×N →（可能 `violation`）→ `done`。

```
event: meta
data: {"id": "…", "now": {…}, "chart": "丙子 壬辰 乙酉 癸未", "evidence": […], "risk": {…}, "mock": true}

event: delta
data: {"text": "此刻是霜降"}

event: done
data: {"mock": true, "id": "…"}
```

浏览器里：

```js
const r = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages: [{ role: 'user', content: '此刻什么节气？' }] }),
})
const reader = r.body.getReader()
const dec = new TextDecoder()
let buf = ''
for (;;) {
  const { value, done } = await reader.read()
  if (done) break
  buf += dec.decode(value, { stream: true })
  // 按 "\n\n" 切事件；"event: x" 与 "data: {...}"
}
```

没有设 key 时 `meta.mock` 为 `true`，返回「念读数」的降级文本——**不是模型输出**。
上游坏了会发 `degraded` 事件，同样带 `mock:false` 与降级原因。

---

## 运维

```bash
curl "http://127.0.0.1:8788/api/health"
curl "http://127.0.0.1:8788/api/metrics"
curl "http://127.0.0.1:8788/api/alerts"
```

设了 `XJI_METRICS_TOKEN` 时，后两个要加 `?token=…`，否则 403。

---

## 自检

```bash
.venv/Scripts/python.exe tools/api_smoke.py
# 18 个例子，失败 0，合计 ~600ms
```

它跑的就是上面这些命令要的东西：状态码、关键字段、SSE 事件序列。
