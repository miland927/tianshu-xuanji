# eval/ 里都是什么

三样东西，各管一件事，别混着看。

| 文件 | 怎么来的 | 管什么 | 不管什么 |
|---|---|---|---|
| `calendar-check.md` | `tools/verify_calendar.py` | 节气时刻与独立实现对表（624 个样本，2010–2035） | 排盘、判断 |
| `golden.jsonl` | `tools/golden.py --freeze` | 三十个生辰的输出**不许漂** | 不证明算得对，只证明没变 |
| `p1-*.jsonl` | `tools/eval_p1.py` | 五十轮对话的原文与拦截记录 | 不评「说得好不好」 |

## 怎么读

- **calendar**：看「平均/最大误差」。现在是 6.28 / 15.9 秒，全在 30 秒内。误差随年份增长是 ΔT 外推不同，不是 bug。
- **golden**：`--check` 退出码非 0 就是漂了。漂了先问「是不是故意的」，故意的就重新 `--freeze`，并在提交信息里写为什么。
- **p1**：`mock: true` 的记录不计分。接了 key 之后，看四类（cite / medical / legal / finance / predict / scare）是否全 0；normal 若被拦，是误杀，改规则。

## 两个坑，写在这里省得再踩

1. **pyephem 的 `ra/dec` 是 astrometric，不是视位置**。直接当视黄经用，节气会偏十几分钟。要用 `a_ra/a_dec`，或者换 pymeeus。
2. **pymeeus 吃的是 TT，钟表是 UT**。不扣 ΔT（2020 年约 69 秒），整年的节气会集体偏一分多钟。
