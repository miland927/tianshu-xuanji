# STATUS：现在到底验了什么

自动生成于 2026-11-03 12:06（`tools/status.py`）。**这张表不靠记忆，靠跑**——重跑一次就对得上。

一句话：离线可验的部分有失败；真模型也跑过了（见下表）。

## 已验证

| 声称 | 怎么验的 | 结果 |
|---|---|---|
| 单元测试全过 | `pytest tests -q` | ✅ 231 passed |
| 八字黄金集不漂 | `tools/golden.py --check` | ✅ 41 例一致 |
| 六壬/奇门/紫微快照不漂 | `tools/golden_plates.py --check` | ✅ 9 条一致 |
| 隐私承诺实测 | `tools/verify_privacy.py`（起真服务、读真文件） | ✅ 11/11 通过 |
| 文档里的接口例子能跑通 | `tools/api_smoke.py`（需要服务在跑） | ✅ 18 个例子，失败 0 |
| 真模型 50 轮（守则 + 对账） | `tools/eval_p1.py` → `tools/recheck.py p1-20261103-120213.jsonl` | ⚠️ 有拦截或对账不符；p50 3630ms |

## 未验证（不是忘了，是没法自己验）

| 声称 | 为什么没验 | 需要什么 |
|---|---|---|
| 备案与内容标识 | 这是行政流程 | 人来办 |
| 法务复核 | 三份草案没请人看过 | 人来看 |
| 真实流量下的限流/熔断/告警 | 只有本机几个请求 | 真实用户 |
| 「算得对」的第三方校验 | 目前是与库、与 pymeeus/ephem 互相印证 | 有人来提勘误 |
| 回答的「有用程度」 | 守则和对账只能查越界与说错，查不了好不好 | 人读，或者更大规模的对照 |

## 现在有什么

- 页面 11 个：`calendar.html`、`corrections.html`、`guide.html`、`index.html`、`liuren.html`、`plate.html`、`qimen.html`、`qimen3d.html`、`samples.html`、`year.html`、`ziwei.html`
- 接口 23 条（`/api/docs` 可试）
- 典籍数据 6 份：`dunjiayanyi.json`、`liurendaquan-bifa.json`、`qiongtong.json`、`shenfeng.json`、`ziping.json`、`ziweiquanshu-gong.json`

## 怎么重跑

```powershell
.venv\Scripts\python.exe tools\check.py        # 单元测试 + 两个黄金集 + 隐私
.venv\Scripts\python.exe tools\api_smoke.py    # 文档里的接口例子（需服务在跑）
.venv\Scripts\python.exe tools\status.py       # 重新生成本页
```

边界（写在接口文档与人设里，也写在这里）：这是传统文化研究与学习工具，不预测具体事件、不判定吉凶、不提供医疗/法律/投资建议。
