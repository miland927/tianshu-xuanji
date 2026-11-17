/* 铭文栏：观 → 问 → 定。
 *
 *   观  周天自己转（landing）。右下角一根发丝线「问璇玑」。
 *   问  仪器退到右边（calm），左侧渐显铭文栏：无底板、无边框，字直接浮在墨上。
 *       起盘行里拨动生辰，「六十甲子」环实时转到日柱。
 *   定  按「起」：四柱在环上点亮成金，栏里落下命盘，璇玑接着批注。
 *   Esc 一次退一层：定 → 问 → 观。
 *
 * 只管层级、布局、起盘与仪器联动。对话（流式、依据、换一派、key）在 chat.js。
 * 四柱由本地 /api/chart 算（含真太阳时校正），前端不另算一份，免得两处结果不一致。
 *
 * DOM id 沿用旧面板（#xji-*），vendor/verify-*.mjs 与 shot-chat.mjs 不用改。
 */

const CSS = `
/* ---------- 观：触发器。一根发丝线 + 三个字 ---------- */
#xji-trigger {
  position: fixed; right: 24px; bottom: 20px; z-index: 30;
  display: flex; align-items: center; gap: 14px;
  padding: 8px 0 8px 8px; background: none; border: 0; cursor: pointer;
  color: var(--ink); font: 500 13px/1 var(--f-glyph); letter-spacing: .42em;
  transition: opacity .25s;
}
#xji-trigger .line { width: 34px; height: 1px; background: var(--hair-3);
  transition: width .6s var(--ease), background-color .25s; }
#xji-trigger:hover .line, #xji-trigger:focus-visible .line { width: 58px; background: var(--hair-hi); }
#xji-trigger .dot { width: 5px; height: 5px; border-radius: 50%; margin-left: -6px;
  background: var(--zhu); box-shadow: 0 0 7px var(--zhu); }
#xji-trigger:focus-visible { outline: none; }
body.xji-open #xji-trigger { opacity: 0; pointer-events: none; }
body.xji-open #tip { display: none; }

/* ---------- 问：左侧铭文栏 ---------- */
#xji {
  position: fixed; left: 0; top: 0; bottom: 0; z-index: 31;
  width: min(46vw, 600px); padding: 92px 40px 20px 24px;
  display: flex; flex-direction: column;
  /* 不是底板：只是一层向右散开的墨，让字从打字机底纹上浮出来 */
  background: linear-gradient(to right, rgba(5,5,5,.88) 0%, rgba(5,5,5,.66) 64%, rgba(5,5,5,0) 100%);
  font-family: var(--f-ui); color: var(--ink);
  opacity: 0; visibility: hidden; transform: translateX(-10px);
  transition: opacity .45s var(--ease), transform .45s var(--ease), visibility 0s linear .45s;
}
body.xji-open #xji {
  opacity: 1; visibility: visible; transform: none;
  transition: opacity .6s var(--ease) .18s, transform .6s var(--ease) .18s, visibility 0s;
}
#xji button { font-family: inherit; }

.xji-head { display: flex; align-items: baseline; gap: 12px;
  padding-bottom: 11px; border-bottom: 1px solid var(--hair-2); }
.xji-head b { font: 500 17px/1 var(--f-glyph); letter-spacing: .32em; color: var(--ink); }
.xji-head span { font-size: 10px; letter-spacing: .22em; color: var(--ink-dim); }
.xji-head button { background: none; border: 0; padding: 2px 0 2px 10px; cursor: pointer;
  font: 12px/1 var(--f-glyph); letter-spacing: .1em; color: var(--ink-dim); transition: color .2s; }
.xji-head button:first-of-type { margin-left: auto; }
.xji-head button:hover, .xji-head button[aria-expanded="true"] { color: var(--ink); }

/* key：点「钥」才出现，保存后只显示掩码 */
#xji-keybox { padding: 10px 0 12px; border-bottom: 1px solid var(--hair-1);
  font: 10.5px/1.8 var(--f-mono); color: var(--ink-dim); }
.kb-status { color: rgba(231,225,211,.6); margin-bottom: 4px; }
.kb-status b { color: var(--gold); font-weight: 400; }
.kb-row { display: flex; gap: 14px; align-items: baseline; margin-top: 6px; }
#xji-keybox button { background: none; border: 0; border-bottom: 1px solid var(--hair-3); padding: 2px 0;
  color: rgba(231,225,211,.62); font: 10.5px/1.4 var(--f-mono); cursor: pointer; transition: color .2s, border-color .2s; }
#xji-keybox button:hover { color: var(--ink); border-bottom-color: var(--hair-hi); }

#xji-read { padding: 9px 0; font: 10px/1.75 var(--f-mono); color: rgba(231,225,211,.42);
  border-bottom: 1px solid var(--hair-1); }
#xji-read em { color: rgba(231,225,211,.86); font-style: normal; }

/* ---------- 起盘行：命令式，下划线输入 ---------- */
#xji-birth { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 12px;
  padding: 16px 0 4px; font: 10.5px/1.9 var(--f-mono); color: rgba(231,225,211,.42); }
.cmd-verb { font: 500 14px/1 var(--f-glyph); letter-spacing: .3em; color: var(--ink); margin-right: 2px; }
.cmd-k { letter-spacing: .1em; }
.u { background: none; border: 0; border-bottom: 1px solid var(--hair-3); border-radius: 0;
  color: var(--ink); font: 12px/1.6 var(--f-mono); padding: 1px 0 2px; outline: none;
  caret-color: var(--zhu); transition: border-color .2s; }
.u:hover, .u:focus { border-bottom-color: var(--hair-hi); }
.u::placeholder { color: rgba(231,225,211,.26); }
#xji-b-date { width: 16.6ch; cursor: ns-resize; }
#xji-b-date:focus { cursor: text; }
#xji-b-lon { width: 6.6ch; }
#xji-b-std { width: 3.6ch; }
.sex { white-space: nowrap; }
.sex button { background: none; border: 0; padding: 0 1px; cursor: pointer;
  font: 13px/1 var(--f-glyph); letter-spacing: .12em; color: rgba(231,225,211,.34); transition: color .2s; }
.sex button:hover { color: rgba(231,225,211,.7); }
.sex button.on { color: var(--gold); }
.sex i { font-style: normal; color: rgba(242,237,224,.18); margin: 0 3px; }
.zhu { margin-left: auto; padding: 6px 13px 5px; cursor: pointer;
  background: rgba(217,72,63,.14); border: 1px solid rgba(217,72,63,.45); border-radius: 0;
  color: var(--gold); font: 500 13px/1 var(--f-glyph); transition: background-color .2s, border-color .2s; }
.zhu:hover { background: rgba(217,72,63,.22); border-color: rgba(217,72,63,.7); }
.zhu:disabled { opacity: .4; cursor: default; }

#xji-pre { min-height: 22px; padding: 2px 0 10px; font: 10px/1.9 var(--f-mono); color: rgba(231,225,211,.36);
  border-bottom: 1px solid var(--hair-1); }
#xji-pre b { font: 500 13px/1 var(--f-glyph); color: rgba(231,225,211,.86); letter-spacing: .08em; margin: 0 2px 0 4px; }
#xji-pre .sep { color: rgba(242,237,224,.18); margin: 0 6px; }
#xji-pre .warn { color: var(--zhu); }

/* ---------- 定：命盘 ---------- */
#xji-pan { padding: 16px 0 12px; border-bottom: 1px solid var(--hair-1); transition: opacity .4s; }
#xji-pan[hidden] { display: none; }
#xji-pan.stale { opacity: .35; }
.pan-cols { display: grid; grid-template-columns: repeat(4, 58px); gap: 0 10px; margin-bottom: 12px; }
.pan-col { text-align: center; animation: xji-in .7s var(--ease) both; }
.pan-col i { display: block; font: 9.5px/1.6 var(--f-mono); font-style: normal; letter-spacing: .24em;
  color: rgba(231,225,211,.36); margin-bottom: 4px; }
.pan-col b { display: block; font: 500 26px/1.22 var(--f-glyph); color: var(--ink); }
.pan-col.ri b { color: var(--gold); }
.pan-col.ri i { color: var(--zhu); }
.pan-rows { font: 10.5px/1.85 var(--f-mono); color: rgba(231,225,211,.78); animation: xji-in .7s var(--ease) .5s both; }
.pan-rows span { color: rgba(231,225,211,.36); display: inline-block; min-width: 5.5em; }
.pan-rows .warn { color: var(--zhu); }
@keyframes xji-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

/* ---------- 对话 ---------- */
#xji-log { flex: 1; min-height: 80px; overflow-y: auto; padding: 16px 6px 12px 0;
  display: flex; flex-direction: column; gap: 14px;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 22px, #000 100%);
  mask-image: linear-gradient(to bottom, transparent 0, #000 22px, #000 100%);
  scrollbar-width: thin; scrollbar-color: rgba(242,237,224,.14) transparent; }
#xji-log .m { font: 14px/1.95 var(--f-glyph); color: rgba(231,225,211,.86); white-space: pre-wrap; }
#xji-log .m.me { font: 12px/1.8 var(--f-ui); color: var(--ink-dim); }
#xji-log .m.me::before { content: "问　"; color: rgba(242,237,224,.3); }
#xji-log .m.sys { font: 9.5px/1.6 var(--f-mono); color: rgba(231,225,211,.4); letter-spacing: .04em; }
#xji-log .m.sys::before { content: "以　"; color: rgba(231,225,211,.28); }
#xji-log .m.ai::before { content: "璇玑　"; color: var(--zhu); font: 10px/1 var(--f-ui); letter-spacing: .1em; }
#xji-log .err { color: var(--zhu); font-size: 11px; line-height: 1.7; }

#xji-log .ev { margin-top: -4px; }
#xji-log .ev-btn { background: none; border: 0; border-bottom: 1px solid var(--hair-3); padding: 2px 0;
  color: rgba(231,225,211,.55); font: 10px/1.4 var(--f-mono); letter-spacing: .1em; cursor: pointer;
  margin-right: 14px; transition: color .2s, border-color .2s; }
#xji-log .ev-btn:hover { color: var(--ink); border-bottom-color: var(--hair-hi); }
#xji-log .ev-btn.on { color: var(--gold); border-bottom-color: rgba(217,72,63,.6); }
#xji-log .ev-list { display: none; margin-top: 9px; padding-left: 10px; border-left: 1px solid rgba(217,72,63,.3); }
#xji-log .ev-list.on { display: block; }
#xji-log .ev-layer { font: 9.5px/1.6 var(--f-mono); color: var(--zhu); letter-spacing: .2em; margin: 9px 0 2px; }
#xji-log .ev-item { font: 10.5px/1.75 var(--f-mono); color: rgba(231,225,211,.62); word-break: break-word; }
#xji-log .ev-cite { background: none; border: 0; border-bottom: 1px dotted rgba(240,217,181,.7);
  color: var(--gold); font: inherit; padding: 0; cursor: pointer; }
#xji-log .ev-cite:hover { border-bottom-style: solid; }
#xji-log .ev-passage { margin: 7px 0 4px; padding: 9px 11px; border-left: 2px solid rgba(240,217,181,.45);
  background: rgba(240,217,181,.035); font: 10.5px/1.85 var(--f-mono); color: rgba(231,225,211,.78); }
#xji-log .ev-passage b { display: block; color: var(--gold); font-weight: 400; font-size: 9.5px;
  letter-spacing: .1em; margin-bottom: 4px; }
#xji-log .ev-passage em { font-style: normal; color: rgba(231,225,211,.45); }
#xji-log .alt { display: inline; }
#xji-log .alt-body { display: none; margin-top: 9px; padding-left: 10px; border-left: 1px solid var(--hair); }
#xji-log .alt-body.on { display: block; }
#xji-log .alt-field { font: 10.5px/1.8 var(--f-mono); color: var(--ink); margin-top: 7px; }
#xji-log .alt-row { font: 10px/1.75 var(--f-mono); color: rgba(231,225,211,.55); padding-left: 12px; }
#xji-log .alt-note { font: 10px/1.7 var(--f-mono); color: rgba(231,225,211,.4); margin-top: 8px; }

#xji-meta { padding: 0 0 8px; display: flex; flex-wrap: wrap; gap: 4px 12px; }
#xji-meta i { font: 9.5px/1.6 var(--f-mono); font-style: normal; color: rgba(231,225,211,.45); }
#xji-meta i::before { content: "· "; color: rgba(242,237,224,.2); }
#xji-meta i.warn { color: var(--zhu); }

#xji-form { padding-top: 10px; border-top: 1px solid var(--hair-2); }
#xji-form .ask { display: flex; align-items: baseline; gap: 14px; }
#xji-input { flex: 1; min-width: 0; background: none; border: 0; border-bottom: 1px solid var(--hair-3); border-radius: 0;
  color: var(--ink); font: 13px/1.8 var(--f-glyph); padding: 3px 0; outline: none; caret-color: var(--zhu);
  transition: border-color .2s; }
#xji-input:hover, #xji-input:focus { border-bottom-color: var(--hair-hi); }
#xji-input::placeholder { color: rgba(231,225,211,.28); }
#xji-send { margin-left: 0; }
#xji-form small { display: block; margin-top: 8px; font-size: 9.5px; color: rgba(231,225,211,.32); letter-spacing: .04em; }
#xji-form small a { color: rgba(231,225,211,.46); text-decoration: none; border-bottom: 1px dotted rgba(242,237,224,.3); margin-left: 4px; }
#xji-form small a:hover { color: var(--ink); border-bottom-color: rgba(242,237,224,.6); }

/* ---------- 禁令补漏：选区、键盘焦点、等待提示 ---------- */
#xji ::selection { background: rgba(217,72,63,.34); color: var(--ink); }
#xji button:focus-visible, #xji a:focus-visible { outline: 1px solid var(--hair-hi); outline-offset: 3px; }
#xji .u:focus-visible, #xji-input:focus-visible { outline: none; }
#xji-input.wait { border-bottom-color: rgba(217,72,63,.7); }
#xji-input.wait::placeholder { color: var(--zhu); }

/* 竖屏或矮屏：命盘一落，对话区会被挤没，输入框会被推出屏外。
   改成整条铭文栏一起滚，问话那一行粘在底部，永远够得着。 */
@media (max-width: 640px), (max-height: 680px) {
  #xji { overflow-y: auto; overscroll-behavior: contain; scrollbar-width: none; }
  #xji::-webkit-scrollbar { display: none; }
  #xji-log { flex: none; min-height: 0; overflow: visible; -webkit-mask-image: none; mask-image: none; }
  #xji-form { position: sticky; bottom: -20px; margin-top: auto; padding-bottom: 20px; background: var(--bg); }
}

/* 竖屏：铭文栏贴底，盘留在上方 */
@media (max-width: 640px) {
  #xji { top: auto; left: 0; right: 0; width: 100vw; height: 66vh; padding: 18px 16px 12px;
    background: linear-gradient(to top, rgba(5,5,5,.95) 0%, rgba(5,5,5,.88) 82%, rgba(5,5,5,0) 100%);
    transform: translateY(12px); }
  #xji-form { bottom: -12px; padding-bottom: 12px; }
  #xji-trigger { right: 16px; bottom: 44px; }
  #xji-log .m { font-size: 13.5px; line-height: 1.9; }
  .pan-cols { grid-template-columns: repeat(4, 1fr); }
  .pan-col b { font-size: 22px; }
}
`

const HTML = `
<button id="xji-trigger" type="button" aria-label="问璇玑"><span class="line"></span>问璇玑<span class="dot"></span></button>
<section id="xji" aria-label="璇玑铭文栏">
  <div class="xji-head">
    <b>璇玑</b><span>器灵 · 只读不算</span>
    <button id="xji-keybtn" type="button" title="配置 API key" aria-label="配置 key" aria-expanded="false">钥</button>
    <button id="xji-close" type="button" title="收起（Esc）" aria-label="收起">收</button>
  </div>
  <div id="xji-keybox" hidden>
    <div class="kb-status" id="xji-kstatus">检查中…</div>
    <div class="kb-row">
      <input id="xji-key" class="u" style="flex:1" type="password" placeholder="sk-…（只存在这台机器的内存里）" spellcheck="false" autocomplete="off" />
    </div>
    <div class="kb-row">
      <button id="xji-ksave" type="button">保存并测试</button>
      <button id="xji-kclear" type="button">清除</button>
      <small id="xji-kmsg"></small>
    </div>
  </div>
  <div id="xji-read">读数载入中…</div>
  <div id="xji-birth" role="group" aria-label="八字起盘">
    <span class="cmd-verb">起八字</span>
    <input id="xji-b-date" class="u" placeholder="1996-04-18 14:06" spellcheck="false" autocomplete="off"
           title="滚轮拨动光标所指的年/月/日/时/分；↑↓ 同理；回车起盘" />
    <span class="cmd-k">东经</span><input id="xji-b-lon" class="u" placeholder="114.93" inputmode="decimal" autocomplete="off" />
    <span class="cmd-k">经线</span><input id="xji-b-std" class="u" value="120" inputmode="decimal" autocomplete="off" title="出生地时区的标准经线：中国 120，东京 135，纽约 -75" />
    <span class="sex" role="radiogroup" aria-label="乾造或坤造"><button type="button" data-v="0" class="on" role="radio" aria-checked="true">乾造</button><i>｜</i><button type="button" data-v="1" role="radio" aria-checked="false">坤造</button></span>
    <input id="xji-b-sex" type="hidden" value="0" />
    <button id="xji-qi" class="zhu" type="button" title="排盘（回车）">起</button>
  </div>
  <div id="xji-pre">滚轮拨年月日时 · 回车或「起」排盘</div>
  <div id="xji-pan" hidden></div>
  <div id="xji-log">
    <div class="m ai">铜环转着，字是死的。你要问什么，得先说完。</div>
  </div>
  <div id="xji-meta"></div>
  <form id="xji-form" autocomplete="off">
    <div class="ask">
      <input id="xji-input" placeholder="问什么？也可以只让我念此刻的读数。" maxlength="500" />
      <button id="xji-send" class="zhu" type="submit">问</button>
    </div>
    <small>AI 生成 · 不是预测 ·<a href="/legal/disclaimer.html" target="_blank" rel="noopener">免责</a><a href="/legal/privacy.html" target="_blank" rel="noopener">隐私</a><a href="/legal/terms.html" target="_blank" rel="noopener">条款</a></small>
  </form>
</section>
`

const style = document.createElement('style')
style.textContent = CSS
document.head.appendChild(style)
const holder = document.createElement('div')
holder.innerHTML = HTML
document.body.append(...holder.children)

const $ = (s) => document.querySelector(s)
const wheel = () => window.__wheel || null
const RING = '六十甲子'
const MOBILE = matchMedia('(max-width: 640px)')
// 竖屏时盘在上方居中，铭文栏在下
const MOBILE_VIEW = { pos: [0, 12.5, 6.2], look: [0, 0, 2.4] }

const dateEl = $('#xji-b-date'), lonEl = $('#xji-b-lon'), stdEl = $('#xji-b-std'), sexEl = $('#xji-b-sex')
const pre = $('#xji-pre'), pan = $('#xji-pan'), qiBtn = $('#xji-qi')

// ---------------- 层级 ----------------
let layer = 'guan'
let asker = null
const openHooks = []
// 起盘票号：收起、退层、改生辰都会作废还在路上的那次「起」，免得结果回来时把状态拽回「定」
let qiSeq = 0, qiBusy = false, dingKey = ''

function setLayer(l) {
  layer = l
  document.body.dataset.layer = l
}

function open() {
  // 以「栏是否打开」为准，不以 layer 为准：layer 万一被异步结果写坏，也不会把入口锁死
  if (document.body.classList.contains('xji-open')) return
  document.body.classList.add('xji-open')
  const w = wheel()
  if (w) { w.setMode('calm'); w.setView?.(MOBILE.matches ? MOBILE_VIEW : null) }
  setLayer('wen')
  openHooks.forEach((f) => f())
  // 读过一次生辰就把预演接回来
  if (dateEl.value.trim()) schedulePreview(0)
  setTimeout(() => (dateEl.value.trim() ? $('#xji-input') : dateEl).focus({ preventScroll: true }), 260)
}

function close() {
  qiSeq++; seq++; clearTimeout(timer)
  document.body.classList.remove('xji-open')
  const w = wheel()
  if (w) { w.turnTo?.(RING, null); w.setView?.(null); w.setMode('landing') }
  setLayer('guan')
  $('#xji-trigger').focus({ preventScroll: true })
}

// 定 → 问：熄掉金格，命盘留着但变淡，生辰还在，可以接着拨
function unsettle() {
  qiSeq++
  if (layer !== 'ding') return
  wheel()?.leave()
  pan.classList.add('stale')
  setLayer('wen')
}

function back() {
  if (layer === 'ding') unsettle()
  else if (layer === 'wen') close()
}

$('#xji-trigger').addEventListener('click', open)
$('#xji-close').addEventListener('click', close)
addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || layer === 'guan') return
  e.preventDefault()
  back()
})
MOBILE.addEventListener?.('change', () => { if (layer !== 'guan') wheel()?.setView?.(MOBILE.matches ? MOBILE_VIEW : null) })

// ---------------- 乾造｜坤造 ----------------
document.querySelectorAll('.sex button').forEach((b) => b.addEventListener('click', () => {
  sexEl.value = b.dataset.v
  document.querySelectorAll('.sex button').forEach((x) => {
    const on = x === b
    x.classList.toggle('on', on)
    x.setAttribute('aria-checked', String(on))
  })
  onBirthChange()
}))

// ---------------- 游标卡尺：滚轮 / ↑↓ 拨动光标所指的那一段 ----------------
// 字符位置：0123-56-89 1112:1415
const SEG = [[0, 4, 'y'], [5, 7, 'M'], [8, 10, 'd'], [11, 13, 'h'], [14, 16, 'm']]
const RE = /^(\d{4})-(\d{1,2})-(\d{1,2})[ T]+(\d{1,2}):(\d{2})$/
const pad = (n, w = 2) => String(n).padStart(w, '0')
const fmt = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`

function parse(s) {
  const m = RE.exec((s || '').trim())
  if (!m) return null
  const [y, M, d, h, mi] = m.slice(1).map(Number)
  const dt = new Date(y, M - 1, d, h, mi)
  if (dt.getFullYear() !== y || dt.getMonth() !== M - 1 || dt.getDate() !== d || h > 23 || mi > 59) return null
  return dt
}

function bump(dt, unit, n) {
  const d = new Date(dt)
  if (unit === 'y' || unit === 'M') {
    // 年、月按日历拨，日子溢出就贴到月末（1 月 31 日 +1 月 = 2 月 28/29 日）
    const day = d.getDate()
    d.setDate(1)
    if (unit === 'y') d.setFullYear(d.getFullYear() + n); else d.setMonth(d.getMonth() + n)
    d.setDate(Math.min(day, new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()))
  } else {
    d.setTime(d.getTime() + n * { d: 864e5, h: 36e5, m: 6e4 }[unit])
  }
  const y = d.getFullYear()
  return y < 1900 || y > 2100 ? dt : d
}

let cw = 0
function charWidth() {
  if (cw) return cw
  const cs = getComputedStyle(dateEl)
  const ctx = document.createElement('canvas').getContext('2d')
  ctx.font = `${cs.fontSize} ${cs.fontFamily}`
  return (cw = ctx.measureText('0000000000').width / 10)
}
function segByChar(i) {
  let best = SEG[0], bd = Infinity
  for (const s of SEG) { const c = (s[0] + s[1]) / 2, dd = Math.abs(i + .5 - c); if (dd < bd) { bd = dd; best = s } }
  return best
}
function segAtX(clientX) {
  const r = dateEl.getBoundingClientRect()
  const x = clientX - r.left - parseFloat(getComputedStyle(dateEl).paddingLeft || 0) + dateEl.scrollLeft
  return segByChar(Math.floor(x / charWidth()))
}

function dial(seg, n) {
  const cur = parse(dateEl.value) || parse(dateEl.placeholder)
  dateEl.value = fmt(bump(cur, seg[2], n))
  if (document.activeElement === dateEl) dateEl.setSelectionRange(seg[0], seg[1])
  onBirthChange()
}

let wheelAcc = 0
dateEl.addEventListener('wheel', (e) => {
  e.preventDefault()
  const seg = segAtX(e.clientX)
  // 鼠标滚一格（deltaY 约 100，或按行计）就拨一下；触控板很碎，攒够 40 再拨
  if (e.deltaMode !== 0 || Math.abs(e.deltaY) >= 50) { wheelAcc = 0; dial(seg, e.deltaY < 0 ? 1 : -1); return }
  wheelAcc += e.deltaY
  if (Math.abs(wheelAcc) >= 40) { dial(seg, wheelAcc < 0 ? 1 : -1); wheelAcc = 0 }
}, { passive: false })

dateEl.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault()
    const seg = segByChar(Math.max(0, (dateEl.selectionStart ?? 0) - (dateEl.selectionStart === dateEl.selectionEnd ? 1 : 0)))
    dial(seg, e.key === 'ArrowUp' ? 1 : -1)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    qi()
  }
})
dateEl.addEventListener('input', onBirthChange)
for (const el of [lonEl, stdEl]) {
  el.addEventListener('input', onBirthChange)
  el.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); qi() } })
}

// ---------------- 预演：拨到哪，环就转到哪 ----------------
function birthParams() {
  const birth = dateEl.value.trim()
  const longitude = Number(lonEl.value.trim()) || 114.93
  const std = Number(stdEl.value.trim())
  return { birth, longitude, standard_longitude: std === 0 ? 120 : (std || 120), gender: Number(sexEl.value) || 0 }
}

async function fetchChart(p) {
  const u = `/api/chart?birth=${encodeURIComponent(p.birth)}&longitude=${p.longitude}` +
            `&gender=${p.gender}&standard_longitude=${p.standard_longitude}`
  const r = await fetch(u)
  if (!r.ok) { let d = ''; try { d = (await r.json()).detail } catch { } throw new Error(d || `接口 ${r.status}`) }
  return r.json()
}

const PILLAR = ['年', '月', '日', '时']
const escape = (s) => String(s ?? '').replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]))

let seq = 0, timer = 0, lastChart = null
function schedulePreview(ms = 140) { clearTimeout(timer); timer = setTimeout(preview, ms) }

function onBirthChange() {
  unsettle()
  lastChart = null
  schedulePreview()
}

async function preview() {
  const p = birthParams()
  const w = wheel()
  if (!p.birth) { seq++; pre.textContent = '滚轮拨年月日时 · 回车或「起」排盘'; w?.turnTo?.(RING, null); return }
  if (!parse(p.birth)) { seq++; pre.innerHTML = `<span class="warn">${badDate(p.birth)}</span>`; return }
  const my = ++seq
  try {
    const c = await fetchChart(p)
    if (my !== seq) return
    lastChart = { key: JSON.stringify(p), chart: c }
    const ps = c.bazi.split(' ')
    pre.innerHTML = '预演' + ps.map((g, i) => `<span class="sep">/</span>${PILLAR[i]}<b>${escape(g)}</b>`).join('') +
      `<span class="sep">/</span>真太阳 ${escape((c.true_solar || '').slice(11, 16))}` +
      (c.warnings && c.warnings.length ? `<span class="sep">/</span><span class="warn">${c.warnings.map((x) => x.kind === 'dst' ? '夏令时' : x.kind === 'tz' ? '时区?' : x.kind).join(' ')}</span>` : '')
    // 日柱是日主：转到正前方
    if (w && layer === 'wen') w.turnTo?.(RING, w.indexOf(RING, ps[2]))
  } catch (e) {
    if (my !== seq) return
    pre.innerHTML = `<span class="warn">${escape(e.message === 'Failed to fetch' ? '预演取不到（本地接口没起）' : e.message)}</span>`
  }
}

// ---------------- 起：进入「定」 ----------------
function renderPan(c) {
  const ps = c.bazi.split(' ')
  const st = c.strength || {}, g = c.geju || {}, y = c.yongshen || {}, cur = c.current || {}
  const dayun = (c.dayun || []).slice(0, 6).map((d) => `${d.pillar}<em style="font-style:normal;color:rgba(231,225,211,.36)">${d.start_age}</em>`).join('  ')
  const row = (k, v) => v ? `<div><span>${k}</span>${v}</div>` : ''
  pan.innerHTML =
    `<div class="pan-cols">${ps.map((p, i) => `<div class="pan-col${i === 2 ? ' ri' : ''}" style="animation-delay:${i * .12}s"><i>${PILLAR[i]}柱${i === 2 ? '·主' : ''}</i><b>${escape(p[0])}</b><b>${escape(p[1])}</b></div>`).join('')}</div>` +
    `<div class="pan-rows">` +
      row('真太阳时', escape(c.true_solar)) +
      row('旺衰', st.label ? `${escape(st.label)} ${st.ratio ?? ''}` : '') +
      row('格局', escape(g.name)) +
      row('用神', y.yong ? `${escape(y.yong)}${y.method ? ' · ' + escape(y.method) : ''}` : '') +
      row('大运', dayun) +
      row('今年', cur.year_gz ? `${escape(cur.year_gz)}${cur.dayun ? ' · 运 ' + escape(cur.dayun) : ''}` : '') +
      (c.warnings || []).map((w) => `<div class="warn">${escape(w.text || (w.kind === 'dst' ? `夏令时 +${w.offset_minutes} 分` : w.kind))}</div>`).join('') +
    `</div>`
  pan.classList.remove('stale')
  pan.hidden = false
}

async function qi() {
  // 按钮 disabled 拦不住回车，所以另设一把锁
  if (qiBusy) return
  const p = birthParams()
  if (!p.birth) { pre.innerHTML = '<span class="warn">先报生辰：YYYY-MM-DD HH:MM</span>'; dateEl.focus(); return }
  if (!parse(p.birth)) { pre.innerHTML = `<span class="warn">${badDate(p.birth)}</span>`; dateEl.focus(); return }
  // 已经定在这张盘上：再按「起」什么也不做，免得璇玑把同一张盘念两遍
  if (layer === 'ding' && dingKey === JSON.stringify(p)) return
  if (!document.body.classList.contains('xji-open')) open()
  qiBusy = true
  qiBtn.disabled = true
  const ticket = ++qiSeq
  try {
    const key = JSON.stringify(p)
    const c = lastChart && lastChart.key === key ? lastChart.chart : await fetchChart(p)
    // 等结果的时候人已经收起栏、退了层或改了生辰：这份结果作废
    if (ticket !== qiSeq || !document.body.classList.contains('xji-open')) return
    renderPan(c)
    const w = wheel()
    if (w) {
      const ps = c.bazi.split(' ')
      w.turnTo?.(RING, null)
      // 日柱在前：它是主焦点，转到正前方
      const lit = w.setFocus
        ? w.setFocus([2, 0, 1, 3].map((i) => ({ ring: RING, index: w.indexOf(RING, ps[i]) })).filter((f) => f.index >= 0))
        : 0
      document.body.dataset.lit = `${RING}:${ps.join(',')}:${lit}`
    }
    setLayer('ding')
    dingKey = key
    asker?.('读这张盘。')
  } catch (e) {
    if (ticket === qiSeq) pre.innerHTML = `<span class="warn">${escape(e.message === 'Failed to fetch' ? '排不了：本地接口没起（server/app.py）' : e.message)}</span>`
  } finally {
    qiBusy = false
    qiBtn.disabled = false
  }
}
// 格式错和「没有这一天」分开说
function badDate(s) {
  return RE.test(String(s).trim()) ? '没有这一天（日期或时刻越界）' : '格式：YYYY-MM-DD HH:MM'
}
qiBtn.addEventListener('click', qi)

setLayer('guan')

export const panel = {
  get layer() { return layer },
  open, close, back,
  // chat.js 注册：「起」之后由它让璇玑开口
  setAsker(fn) { asker = fn },
  onOpen(fn) { openHooks.push(fn) },
  birthParams,
}
window.__xji = panel
