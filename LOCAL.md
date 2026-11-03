# 本机部署说明

上游：<https://github.com/zaoxu001/celestial-wheel>（MIT，周天 · 十二重同心环）。
这是一份可以直接在本机跑、断网也能跑的副本。

## 跑起来

双击 `start.cmd`，或者：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1 -Port 8788
```

脚本会找空闲端口、起服务，然后打开浏览器。`-NoBrowser` 只起服务不开浏览器。

有 `D:\Dev\tianzhi\.venv` 时走 uvicorn，`/api` 与璇玑面板可用；没有就退成纯静态站。

要给璇玑接真模型，先设 key（只放服务端，别进前端）：

```powershell
$env:DEEPSEEK_API_KEY = 'sk-...'
# 可选：$env:TIANZHI_MODEL = 'deepseek-chat'; $env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
```

没设 key 时面板照样能用，回复是「念读数」的 mock，不是模型输出。

**必须走 http。** 直接双击 `index.html` 不行：ES module 和 `fetch('./src/...')` 在
`file://` 下会被浏览器拦住，页面会黑掉。

## 相对上游改了什么

| 文件 | 改动 |
|---|---|
| `index.html` | importmap 换成本地 three；末尾加一行 `<script src="./src/chat.js">` |
| `vendor/three/` | three r160 的 `build/three.module.js` + 4 个后处理入口按 import 图裁下来，共 11 个文件 |
| `start.ps1` / `start.cmd` | 新增：起服务 + 开浏览器（优先 uvicorn） |
| `vendor/serve.mjs` | 新增：没装 Python 时用 Node 顶上的静态服务器 |
| `vendor/bundle-three.mjs` | 新增：重新生成 `vendor/three/` 用（`node vendor/bundle-three.mjs <three 包解压目录>`） |
| `vendor/check-imports.mjs` | 新增：从 `index.html` 爬 import 图，逐个 HTTP 校验，确认没有 404 |
| `vendor/capture.mjs` | 新增：用 CDP 真实渲染若干秒后截图（`node vendor/capture.mjs <url> <out.png> [waitMs]`） |
| `vendor/shot-chat.mjs` | 新增：打开璇玑面板、问一句、截两张图（`node vendor/shot-chat.mjs <url> <前缀>`） |
| `vendor/verify-focus.mjs` | 新增：P3 验收——问一句节气，检查环有没有转到那一格（`node vendor/verify-focus.mjs`） |
| `vendor/verify-align.mjs` | 新增：P3 验收——打开页面，检查三只环是否对准此刻（`node vendor/verify-align.mjs`） |
| `vendor/verify-mobile.mjs` | 新增：竖屏验收——390×844 下看面板布局（`node vendor/verify-mobile.mjs`） |
| `vendor/verify-readout.mjs` | 新增：读数条验收——有数、点了转环、开面板让位 |
| `vendor/verify-calendar.mjs` | 新增：节气历验收——24 行、此刻标记、三候 |
| `vendor/verify-liuren.mjs` | 新增：六壬盘验收——十二格与 API 逐格比对、三传落位 |
| `vendor/verify-qimen.mjs` | 新增：奇门盘验收——九宫逐格比天盘/地盘/星/门/神，直符直使落宫 |
| `vendor/verify-ziwei.mjs` | 新增：紫微盘验收——十二宫、主星、命身宫、生年四化逐项比 |
| `vendor/verify-plate.mjs` | 新增：换镜头验收——环上十二支与 API 天地盘一致、`indexOf` 对位 |
| `vendor/verify-lens.mjs` | 新增：镜头切换验收——连切 12 次，画布恒 1、上下文不丢 |
| `vendor/verify-passage.mjs` | 新增：出处跳转验收——问一句 → 展开依据 → 点引用 → 原文出现 |
| `vendor/verify-bifa.mjs` | 新增：毕法原文验收——点一条毕法 → 注展开 |
| `vendor/verify-ziwei-src.mjs` | 新增：紫微原文验收——点命宫 → 全书论断展开 |
| `vendor/verify-qimen-src.mjs` | 新增：奇门原文验收——点成格 → 遁甲演义那节展开 |
| `vendor/verify-ziwei-year.mjs` | 新增：紫微流年验收——大限宫/流年宫描边与 API 一致 |
| `vendor/verify-print.mjs` | 新增：打印验收——切打印媒体看配色/控件，再真打一份 PDF 看字节 |
| `server/cal.py` | 新增：把 tianzhi-core 包成 `/api/now` 与 `/api/chart`，唯一允许排盘的地方；`chart.qiyun` 给起运的验算材料（节名/时刻/天数/库给的虚岁） |
| `server/persona.py` | 新增：璇玑的人设与硬约束，含医疗/法律/投资的风险识别 |
| `server/guard.py` | 新增：出口校验器（编造出处 / 越界建议 / 事件预测 / 恐吓词），流式按句判定 |
| `server/dst.py` | 新增：夏令时检测，直接读 IANA tzdata（中国 1986–1991 六档窗口现算，不硬编码） |
| `server/evidence.py` | 新增：把判据整理成界面可展示的分组（历法/四柱/旺衰/格局/用神/岁运/提示） |
| `server/audit.py` | 新增：审计日志（默认不存生辰原值；版本三元组 + 派生量 + 输出） |
| `server/compare.py` | 新增：换一派——四组口径重算同一张盘，返回差异表 |
| `server/sidereal.py` | 新增：恒星时（Meeus 12.4）与二十八宿分界（古度距度归一，起点角宿一 J2000） |
| `server/moon.py` | 新增：月相（日月黄经差，Meeus 截断式）+ 一年的朔望表（二分到秒） |
| `server/claims.py` | 新增：对账——把回答里的事实断言（四柱/节气/旺衰/用神/比例）与库的输出比 |
| `server/passages.py` | 新增：出处原文——穷通宝鉴（120 条干支）、子平真诠（篇章）、神峰通考（篇章） |
| `server/bifa.py` | 新增：《六壬大全》毕法赋百句的原文注，按条号取 |
| `server/ziwei_src.py` | 新增：《紫微斗数全书》卷二「十二宫逐星论断」，宫×星 289 条（含妻妾/奴仆名目对照） |
| `server/qimen_src.py` | 新增：《遁甲演义》80 节原文，按库给的 cite 定位（旧字形归一） |
| `server/metrics.py` | 新增：进程内指标——按路由的调用量/耗时/分位、状态码、事件、慢请求 |
| `server/breaker.py` | 新增：上游熔断——closed/open/half_open 三态，冷却后放一个探针 |
| `server/cost.py` | 新增：成本核算——只认上游的 usage；有 `XJI_DAILY_BUDGET` 就封顶 |
| `server/alerts.py` | 新增：告警规则——错误率、慢路由、降级、限流、守则 |
| `tools/watch.py` | 新增：告警轮询命令行（`--once` 看一次，有 error 则退出码 1） |
| `server/ziwei_year.py` | 新增：紫微流年——大限宫、流年宫、小限、流年四化（查 build_chart 的 daxian/xiaoxian） |
| `server/year.py` | 新增：年度报告——立春起十二个月，月干以五虎遁推；同一份报告里带紫微流年（大限/流年宫/小限/四化） |
| `year.html` + `src/year.js` | 新增：年度报告页——流年/大运/日主/年评分 + 十二个月（月建/流月/十神/交节）；带打印样式，可存 PDF |
| `guide.html` | 使用说明页——四个入口、还有这些（三盘/3D/样例/台账/接口）、从哪开始、表盘怎么读、它不做什么；18 个站内链接由 `verify-guide.mjs` 逐个验 200 |
| `API.md` | 新增：接口接入文档——四组例子（curl/JS/SSE），输出都是真跑过的 |
| `tools/status.py` + `STATUS.md` | 新增：跑一遍生成「已验证 / 未验证」两栏，未验的必须写明为什么 |
| `tools/recheck.py` | 新增：用当前规则重判一份 eval jsonl（不花 token） |
| `tools/samples.py` + `samples.html` | 新增：从最近一次真模型评估里原样摘 5 段问答，生成「它长什么样」页 |
| `tools/report_from_jsonl.py` | 新增：用当前规则重出一页评估报告 |
| `tools/preflight.py` | 新增：接 key 后先验——掩码显示、发一个 max_tokens=1 的请求、看有没有 usage |
| `tools/api_smoke.py` | 新增：照着 API.md 真跑一遍（18 个例子），失败即红 |
| `CORRECTIONS.md` + `corrections.html` | 新增：勘误台账——四类勘误、三种结论、采纳后进哪个黄金集；页面只读 |
| `server/corrections.py` + `tools/corrections.py` | 新增：台账读写/校验/命令行（add / decide / list / check） |
| `README.md` | 改动：顶部加「本地版本说明」，指路 guide/LOCAL/ROADMAP；上游原文保留 |
| `data/classics/*.json` | 新增：vendored 原文数据集（来自 tianzhi-classics，MIT），含原文、今译、核对结论 |
| `tools/audit.py` | 新增：看日志 / 还原一条回答（`--tail`、`--id --replay`、`--verify`、`--purge`） |
| `server/app.py` | 新增：FastAPI，`/api/chat` 流式转发 DeepSeek（SSE），输出经 guard 再送前端；开放 API 元信息（`/api/docs`、`/api/openapi.json`、`/api` 目录） |
| `tools/eval_p1.py` | 新增：P1 五十轮评估，落盘 `eval/p1-*.jsonl` + 一页 `p1-*.md` 报告；`--limit N` 先摸一轮；真模型模式下有越界或对账不符则退出码 1 |
| `tools/verify_calendar.py` | 新增：节气对表（pymeeus 独立实现），产出 `eval/calendar-check.md` |
| `tools/golden.py` | 新增：黄金集 41 例，`--freeze` 冻结 / `--check` 查漂移 |
| `tools/golden_plates.py` | 新增：三盘快照 9 条（六壬三传 / 奇门局数 / 紫微命宫四化），同上 |
| `tools/verify_privacy.py` | 新增：隐私承诺实测（起真服务、读真文件、删了再验，11 项） |
| `tools/check.py` | 新增：一条命令跑完快检（单元测试 + 八字黄金集 + 三盘快照 + 隐私），`--slow` 加节气对表 |
| `tools/check_claims.py` | 新增：对账命令行——`--text` 单句、`--jsonl` 整个 eval 文件、`--self` 自检 |
| `tests/test_guard.py` | 新增：guard 单测（`python -m pytest tests -q`） |
| `tests/test_breaker.py` | 新增：熔断三态机（时钟注入）+ 接口层短路验证 |
| `tests/test_cost.py` | 新增：成本核算（usage 解析、日切、预算、假上游端到端） |
| `tests/test_alerts.py` | 新增：告警规则（错误率/慢路由/降级/熔断） |
| `tests/test_dst.py` | 新增：夏令时单测 |
| `tests/test_golden.py` | 新增：黄金集不漂移的测试（106 个测试全过） |
| `tests/test_golden_plates.py` | 新增：三盘快照不漂移的测试 |
| `tests/test_evidence.py` | 新增：依据面板的数据源测试 |
| `tests/test_audit.py` | 新增：审计日志（字段、隐私掩码、写读、清理、派生量） |
| `tests/test_cal_tz.py` | 新增：海外时区（等价代换、时柱/日柱、警告） |
| `tests/test_focus.py` | 新增：问法→环与字的映射 |
| `tests/test_sidereal.py` | 新增：恒星时（对 ephem）、二十八宿分界闭合、宿的落位 |
| `tests/test_moon.py` | 新增：月相（对 ephem 的照度、边界命名、朔望周期） |
| `tests/test_resilience.py` | 新增：限流（配额/分 IP/窗口过期）与降级文案 |
| `tests/test_api_contract.py` | 新增：API 契约（前端依赖的字段不许消失或换类型） |
| `src/chat.js` | 新增：右下角璇玑面板（自建 DOM 与样式，不动上游 CSS） |
| `src/readout.js` | 新增：左下角常驻读数条（节气/月建/日柱/时柱/真太阳时/宿/日出日落），点了转环 |
| `calendar.html` + `src/calendar.js` | 新增：节气历——24 节气交节时刻 + 七十二候，标此刻；候名直接 import data.js，不复制一份 |
| `liuren.html` + `src/liuren.js` | 新增：大六壬天地盘——外圈天盘随月将转、内圈地盘不动，三传标红；可改时刻重起 |
| `qimen.html` + `src/qimen.js` | 新增：奇门九宫——洛书方位三三格，直符宫描金、直使宫描红，成格带原文 |
| `qimen3d.html` + `src/qimen3d.js` | 新增：奇门方阵的 3D 透视版——九宫斜置，点宫出细节（不共用周天引擎，3×3 进不了环） |
| `ziwei.html` + `src/ziwei.js` | 新增：紫微十二宫——4×4 外环十二格，生年四化标在星上，中宫放命主身主 |
| `plate.html` + `src/plate.js` | 新增：换镜头——`?type=liuren` 两圈天地盘、`ziwei` 十二宫、`qimen` 八宫环、`zhoutian` 十二重；就地切换 |
| `BLUEPRINT.md` | 新增：从 demo 到产品还差什么 |
| `PLATES.md` | 新增：换镜头的设计——四块盘如何映射到「环」这个抽象 |
| `ROADMAP.md` | 新增：到最终形态的分阶段计划（P0–P5）与验收 |
| `legal/` | 新增：隐私政策 / 服务条款 / 免责声明三份草案（**待法务复核**） |

其余文件（`src/`、`README.md`、`LICENSE`、`preview.png`）与上游一致。

想换回 CDN 版：把 `index.html` 里 importmap 的三行改回注释里的 jsdelivr 地址即可。

## 自检

```powershell
# 所有模块可解析、无 404
node .\vendor\check-imports.mjs http://127.0.0.1:8788/

# 真实渲染 + 检查 canvas / 打字机 / WebGL
node .\vendor\capture.mjs http://127.0.0.1:8788/ .\preview-local.png 7000
# -> probe {"canvases":1,"codeChars":537,"webgl":true}

# 接口：此刻 / 一张盘
curl.exe -s "http://127.0.0.1:8788/api/now?longitude=114.93"
curl.exe -s "http://127.0.0.1:8788/api/chart?birth=1996-04-18%2014:06&longitude=114.93"

# 璇玑面板开合 + 一轮问答的截图
node .\vendor\shot-chat.mjs http://127.0.0.1:8788/ .\shot
```

## 部署到公网

轮子本身是纯静态，没有构建步骤，也没有任何运行时外部请求（字体用系统衬线体），
整个目录丢给 GitHub Pages / Cloudflare Pages / Vercel / 任意 nginx 都能用。
importmap 里用的是相对路径，放在子目录（比如 `/celestial-wheel/`）也正常。

**但加了 `/api` 之后不一样了**：`server/` 那层必须跑在服务器上，因为它握着
`DEEPSEEK_API_KEY`（绝不能进前端），并且要 import tianzhi-core。
公网部署就是把「静态目录 + uvicorn」一起放进容器，前面挂 nginx。

## 注意

- 需要 WebGL2。极老的显卡或关掉硬件加速的浏览器会黑屏或掉帧。
- 环上的汉字用系统衬线体渲染（`Zhuque Fangsong` → `Songti SC` → `STSong` → `Noto Serif SC`）。
  装了思源宋体最好看；想换字体改 `src/celestial-wheel.js` 顶部的 `FONT`。
- 两处可调的观感参数在 `src/celestial-wheel.js`：
  `UnrealBloomPass(..., .38, .7, .8)`（强度 / 半径 / 阈值）与 `renderer.toneMappingExposure = 1.05`。
- 22 秒一轮的「平面 ↔ 立体」节奏在 `frame()` 里：`const cyc = t % 22`，四段分别是 4s 平、6s 抬、6s 立体、6s 落。
