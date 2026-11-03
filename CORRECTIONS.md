# 勘误：怎么提、怎么判、怎么进黄金集

这套东西的「对」，目前是**我和库互相印证出来的**——节气对过 pymeeus，月相对过 ephem，
三盘有快照，原文有出处。但**没有第三方校验过**。这是它最大的软肋。

所以这份台账存在的意义不是「收集意见」，而是**把「谁说的、什么证据、最后怎么判」留下来**，
让「错」也有据可查。

---

## 什么算勘误

四类（`kind`）：

| kind | 例子 |
|---|---|
| `calc` | 「2026 立春交节算成 04:02，pymeeus 是 04:04」 |
| `cite` | 「这句引文不是《穷通宝鉴》原文，是后人按语」 |
| `wording` | 「这句话读起来像在预测，违反你自己的边界」 |
| `other` | 其余 |

**只接受带证据的**。证据可以是：

1. **原文**（书名、卷次、原句），且给出可核对的版本（如四库全书本、维基文库录文）
2. **独立实现**（pymeeus / ephem / 另一套排盘程序）的计算结果与命令
3. **可复现的样本**：出生时间、经度、参数，以及你认为正确的值

没有证据的意见也会记下来，但状态只能是 `unclear`——**记下不等于采纳**。

## 三种结论

| status | 含义 |
|---|---|
| `open` | 记下了，还没判 |
| `accepted` | 复核后认为我们错了，已改（或已进黄金集） |
| `rejected` | 复核后认为我们没错，附理由 |
| `unclear` | 证据不足，或双方口径不同——**分歧本身就是结论** |

`rejected` 不等于「你说的不对」，可能是「我们按另一套口径」——这种情况会写清楚是哪套口径。

## 为什么「不采纳」也要留名

因为下次还有人会提同样的意见。台账里有一条 `rejected` 加理由，
比每次重新讨论一遍更省事，也更诚实。

## 采纳之后去哪

- `calc` 类：进 `eval/golden.jsonl`（八字）或 `eval/plates-golden.jsonl`（四门），并加一条单测
- `cite` 类：改 `data/classics/*.json` 或 `server/*_src.py` 的映射，测试里加断言
- `wording` 类：改人设与守则，并在 `tests/test_guard.py` 加用例

署名写在台账的 `credit` 字段；改动本身也留在 git 历史里。

---

## 怎么提

本机版没有公网入口，所以两种方式：

1. 直接说给跑这套东西的人
2. 自己写一行进台账：

```powershell
.venv\Scripts\python.exe tools\corrections.py add `
  --kind calc --target /api/year `
  --claim "2026 立春交节时刻差 2 分钟" `
  --evidence "pymeeus 算出 2026-02-04 04:04:11（脚本见 tools/verify_calendar.py）" `
  --credit "你的名字或昵称"
```

判定：

```powershell
.venv\Scripts\python.exe tools\corrections.py decide c-0001 `
  --status accepted --decision "复核：TT/UT 之差未扣，已改" --credit "@someone"
```

查看 / 校验：

```powershell
.venv\Scripts\python.exe tools\corrections.py list
.venv\Scripts\python.exe tools\corrections.py check
```

网页上看：`/corrections.html`（只读，读 `/api/corrections`）。

---

## 一条底线

台账上写着 `accepted` 的，必须是**真的改了**。改了才写结论；
不然这条台账本身就变成了新的「编造出处」。
