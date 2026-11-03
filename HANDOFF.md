# HANDOFF：换一台电脑，怎么把这套东西跑起来

这份文档写给「换机器之后的自己」。按顺序做，最后一条命令能跑通，就说明环境齐了。

---

## 一、需要什么

| 东西 | 版本 / 说明 |
|---|---|
| Windows | 这套东西在 PowerShell 5.1 上验证过（`start.cmd` 用 `-ExecutionPolicy Bypass`） |
| Python | **3.12**（tianzhi-core 0.7.0 的验证版本）。装在任意位置都行 |
| Node.js | 可选，只在跑页面验收脚本（`vendor/verify-*.mjs`）时需要 |
| Edge / Chrome | 可选，同上；脚本里写的是 `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |
| 网络 | 首次装 Python 依赖要能上 PyPI；接真模型要能上 `api.deepseek.com` |

**不需要**数据库、不需要 Docker、不需要构建步骤。前端是原生 ES module。

---

## 二、目录

```
celestial-wheel\
├── index.html  plate.html  calendar.html  liuren.html  qimen.html
├── qimen3d.html  ziwei.html  year.html  samples.html  corrections.html  guide.html
├── server\          后端（FastAPI）：计算包装、守则、原文、运维
├── src\             前端模块（含上游的 celestial-wheel.js / data.js）
├── vendor\          three.js r160（本地化）+ 二十来个验收脚本
├── data\classics\   六份典籍数据（穷通宝鉴/子平真诠/神峰通考/六壬毕法/遁甲演义/紫微全书）
├── tests\           223 个单元测试
├── tools\           验证、评测、运维命令行
├── legal\           隐私/条款/免责三份草案
├── eval\            黄金集、盘面快照、接口示例结果、真模型 50 轮记录
└── *.md             文档（见下）
```

文档分工：

| 文件 | 写给谁 |
|---|---|
| `README.md` | 第一次打开仓库 |
| `guide.html` | 第一次用网页的人 |
| `HANDOFF.md`（本文） | 换机器、重装环境 |
| `ROUNDS.md` | 想回顾「每一轮做了什么」 |
| `STATUS.md` | 自动生成：验过什么、没验什么 |
| `ROADMAP.md` | 接下来做什么 |
| `API.md` / `/api/docs` | 要接接口的人 |
| `PLATES.md` | 换镜头的设计取舍 |
| `CORRECTIONS.md` | 想提勘误的人 |
| `LOCAL.md` | 逐文件改动清单（相对上游） |

---

## 三、一次性设置

### 1. 建虚拟环境并装依赖

```powershell
python -m venv D:\Dev\tianzhi\.venv
D:\Dev\tianzhi\.venv\Scripts\python.exe -m pip install -U pip
D:\Dev\tianzhi\.venv\Scripts\python.exe -m pip install `
    "tianzhi-core==0.7.0" lunar-python tzdata fastapi uvicorn httpx pytest pymeeus ephem
```

> 为什么路径写死成 `D:\Dev\tianzhi\.venv`：`start.ps1` 里认这个路径。想换位置就改
> `start.ps1` 第 28 行的 `$venv`，或者把新路径加进去。

### 2. 确认依赖齐了

```powershell
D:\Dev\tianzhi\.venv\Scripts\python.exe -c "import tianzhi_core, fastapi, httpx, pymeeus, ephem; print('ok')"
```

### 3. 起服务

```powershell
.\start.cmd
# 或指定端口：
powershell -ExecutionPolicy Bypass -File .\start.ps1 -Port 8788
```

脚本会找空闲端口、起 uvicorn、开浏览器。`-NoBrowser` 只起服务。

---

## 四、配 key（两种方式，任选）

### 方式 A：网页上填（推荐给玩家）

1. 打开首页 → 右下角「问 璇 玑」→ 标题栏的 **⚙**
2. 贴 key → 「保存并测试」
3. 状态会变成 `已配置 sk-5…17ba（网页填的）`，并显示一次最小请求的 usage

**只存在服务端内存**，不落盘、不回显全文，重启服务就没了。

### 方式 B：环境变量（推荐给部署）

```powershell
$env:DEEPSEEK_API_KEY = 'sk-...'
# 可选
# $env:TIANZHI_MODEL = 'deepseek-chat'
# $env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
```

然后重启服务。网页上填的会**覆盖**环境变量，清除后回落到环境变量。

验证 key：

```powershell
.venv\Scripts\python.exe tools\preflight.py     # 掩码显示 + 打一次 max_tokens=1
```

---

## 五、确认环境没问题（三条命令）

```powershell
.venv\Scripts\python.exe tools\check.py        # 单元测试 + 两个黄金集 + 隐私
.venv\Scripts\python.exe tools\api_smoke.py    # 文档里的 18 个接口例子（需服务在跑）
.venv\Scripts\python.exe tools\status.py       # 重新生成 STATUS.md
```

期望输出：

```
PASS  单元测试     223 passed
PASS  八字黄金集不漂 41 例一致
PASS  三盘快照不漂  9 条一致
PASS  隐私承诺实测  11/11
4/4 通过

18 个例子，失败 0
```

---

## 六、想跑真模型评测

```powershell
# 花一点钱：50 轮 ≈ ¥0.4
.venv\Scripts\python.exe tools\eval_p1.py --limit 5   # 先摸 5 轮
.venv\Scripts\python.exe tools\eval_p1.py             # 跑满 50 轮，出 jsonl + md 报告

# 改了守则/对账规则后，用旧回答重新判（不花钱）
.venv\Scripts\python.exe tools\recheck.py eval\p1-xxx.jsonl
.venv\Scripts\python.exe tools\report_from_jsonl.py eval\p1-xxx.jsonl
```

报告落在 `eval/p1-<时间>.md`，三张表：守则拦截、对账不符、延迟分位。

---

## 七、页面验收（可选，需要 Node + Edge）

```powershell
node vendor\check-imports.mjs http://127.0.0.1:8788/    # 所有模块 200
node vendor\verify-readout.mjs                           # 读数条
node vendor\verify-guide.mjs                             # 说明页 18 个站内链接
node vendor\verify-lens.mjs                              # 四副镜头切换不泄漏
node vendor\verify-qimen3d.mjs                           # 3D 方阵九宫与 API 一致
node vendor\verify-key-ui.mjs                            # 网页配 key（设 $env:TEST_KEY）
```

---

## 八、常见坑（都踩过）

| 现象 | 原因 / 办法 |
|---|---|
| 页面全黑、控制台 `file://` 报错 | **必须走 http**，不能双击 `index.html` |
| `start.ps1` 报语法错误 | 文件被存成无 BOM 的 UTF-8，PowerShell 5.1 按 GBK 读。用 node 写文件时加 BOM，或用 `pwsh` 7 |
| 中文变成「濂囬棬」 | **不要用** `Get-Content \| Set-Content` 改 UTF-8 文件（会按 GBK 往返）。用编辑工具或 Python 读写 |
| `git clone/push` 报 `SEC_E_NO_CREDENTIALS` | 本机没有可用的 git 凭据。用 PAT（`https://<token>@github.com/...`）或换 SSH |
| 无头浏览器起不来 / 崩溃 | 沙箱限制。验收脚本需要放宽权限运行 |
| `/api/*` 全是 404 | 走的是静态服务器（没装 Python 或 venv 路径不对）。看启动日志 |
| 聊天回复「模型暂时不可用」 | key 无效或熔断中。`/api/metrics` 看 `breaker` 与 `events`，`/api/alerts` 看告警 |

---

## 九、想改东西时从哪下手

| 想改 | 文件 |
|---|---|
| 人物设定 / 硬约束 | `server/persona.py` |
| 出口守则（拦截规则） | `server/guard.py` + `tests/test_guard.py` |
| 对账规则 | `server/claims.py` + `tests/test_claims.py` |
| 读数条 | `src/readout.js` |
| 璇玑面板 | `src/chat.js` |
| 环的视觉（字体、辉光、节奏） | `src/celestial-wheel.js` 顶部常量 |
| 换镜头（新盘） | `src/plate.js` + `PLATES.md` |
| 接口 | `server/app.py`（新增路由记得补 `ROUTE_META`，否则契约测试会红） |

**改完必跑**：`tools/check.py`。它会在你忘记的时候提醒你黄金集漂了。
