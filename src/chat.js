/* 璇玑：接在周天右下角的一个小端口。读数由本地 /api 给，话由模型说。 */
const CSS = `
#xji-trigger {
  position: fixed; right: 24px; bottom: 24px; z-index: 30;
  display: flex; align-items: center; gap: 9px;
  padding: 9px 15px 9px 12px;
  background: rgba(8,8,8,.72); color: var(--ink);
  border: 1px solid rgba(242,237,224,.22); border-radius: 999px;
  font: 12px/1 "PingFang SC","Noto Sans SC",system-ui,sans-serif; letter-spacing: .12em;
  cursor: pointer; backdrop-filter: blur(6px);
  transition: border-color .2s, background .2s, opacity .2s;
}
#xji-trigger:hover { border-color: rgba(242,237,224,.45); background: rgba(14,14,14,.85); }
#xji-trigger .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--zhu); box-shadow: 0 0 8px var(--zhu); }
body.xji-open #xji-trigger { opacity: 0; pointer-events: none; }
body.xji-open #tip { display: none; }

#xji {
  position: fixed; right: 24px; bottom: 24px; z-index: 31;
  width: min(380px, calc(100vw - 48px)); height: min(640px, calc(100vh - 48px));
  display: none; flex-direction: column;
  background: rgba(6,6,6,.94); border: 1px solid rgba(242,237,224,.26);
  box-shadow: 0 18px 60px rgba(0,0,0,.55);
  backdrop-filter: blur(10px);
  font-family: "PingFang SC","Noto Sans SC",system-ui,sans-serif;
}
body.xji-open #xji { display: flex; }

.xji-head {
  display: flex; align-items: baseline; gap: 10px; padding: 14px 16px 10px;
  border-bottom: 1px solid rgba(242,237,224,.12);
}
.xji-head b { font: 500 15px/1 "Songti SC","STSong",serif; letter-spacing: .28em; color: var(--ink); }
.xji-head span { font-size: 10px; letter-spacing: .16em; color: var(--ink-dim); }
.xji-head button {
  margin-left: auto; background: none; border: 0; color: var(--ink-dim);
  font-size: 16px; line-height: 1; cursor: pointer; padding: 2px 4px;
}
.xji-head button + button { margin-left: 2px; }
.xji-head button:hover { color: var(--ink); }

/* key 配置：只在点开时出现，保存后只显示掩码 */
#xji-keybox { padding: 10px 16px 12px; border-bottom: 1px solid rgba(242,237,224,.08);
  font: 10.5px/1.8 ui-monospace,Consolas,monospace; color: var(--ink-dim); }
.kb-status { color: rgba(231,225,211,.6); margin-bottom: 6px; }
.kb-status b { color: var(--gold); font-weight: 400; }
.kb-row { display: flex; gap: 6px; align-items: center; margin-top: 6px; }
#xji-key { flex: 1; background: rgba(255,255,255,.03); border: 1px solid rgba(242,237,224,.14);
  color: var(--ink); font: 11px/1.4 ui-monospace,monospace; padding: 6px 8px; }
#xji-key:focus { border-color: rgba(242,237,224,.34); outline: none; }
#xji-keybox button { background: none; border: 1px solid rgba(242,237,224,.16);
  color: var(--ink-dim); font: 10.5px/1 inherit; padding: 6px 9px; cursor: pointer; }
#xji-keybox button:hover { color: var(--ink); border-color: rgba(242,237,224,.4); }
#xji-kmsg { color: var(--ink-dim); }

#xji-read { padding: 9px 16px; font: 10px/1.7 ui-monospace,Consolas,monospace; color: var(--ink-dim);
  border-bottom: 1px solid rgba(242,237,224,.08); }
#xji-read em { color: var(--ink); font-style: normal; }

#xji-log { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; }
#xji-log .m { font-size: 12.5px; line-height: 1.85; color: rgba(231,225,211,.86); white-space: pre-wrap; }
#xji-log .m.me { color: var(--ink-dim); }
#xji-log .m.me::before { content: "问　"; color: rgba(242,237,224,.3); }
#xji-log .m.sys { font: 9.5px/1.6 ui-monospace,Consolas,monospace; color: rgba(231,225,211,.4);
  letter-spacing: .04em; }
#xji-log .m.sys::before { content: "以　"; color: rgba(231,225,211,.28); }
#xji-log .m.ai::before { content: "璇玑　"; color: var(--zhu); font-size: 10px; letter-spacing: .1em; }
#xji-log .err { color: var(--zhu); font-size: 11px; line-height: 1.7; }

#xji-log .ev { margin-top: -2px; }
#xji-log .ev-btn {
  background: none; border: 1px solid rgba(242,237,224,.18); color: rgba(231,225,211,.55);
  font: 10px/1 inherit; letter-spacing: .1em; padding: 4px 8px; cursor: pointer;
}
#xji-log .ev-btn:hover { color: var(--ink); border-color: rgba(242,237,224,.4); }
#xji-log .ev-btn.on { color: #f0d9b5; border-color: rgba(217,72,63,.5); }
#xji-log .ev-list { display: none; margin-top: 9px; padding-left: 10px;
  border-left: 1px solid rgba(217,72,63,.3); }
#xji-log .ev-list.on { display: block; }
#xji-log .ev-layer { font: 9.5px/1.6 ui-monospace,Consolas,monospace; color: var(--zhu);
  letter-spacing: .2em; margin: 9px 0 2px; }
#xji-log .ev-item { font: 10.5px/1.75 ui-monospace,Consolas,monospace; color: rgba(231,225,211,.62);  word-break: break-word; }
#xji-log .ev-cite { background: none; border: 0; border-bottom: 1px dotted rgba(240,217,181,.7);
  color: #f0d9b5; font: inherit; padding: 0; cursor: pointer; }
#xji-log .ev-cite:hover { border-bottom-style: solid; }
#xji-log .ev-passage { margin: 7px 0 4px; padding: 9px 11px; border-left: 2px solid rgba(240,217,181,.45);
  background: rgba(240,217,181,.035); font: 10.5px/1.85 ui-monospace,Consolas,monospace;
  color: rgba(231,225,211,.78); }
#xji-log .ev-passage b { display: block; color: #f0d9b5; font-weight: 400; font-size: 9.5px;
  letter-spacing: .1em; margin-bottom: 4px; }
#xji-log .ev-passage em { font-style: normal; color: rgba(231,225,211,.45); }
#xji-log .alt { margin-top: 8px; }
#xji-log .alt-body { display: none; margin-top: 9px; padding-left: 10px;
  border-left: 1px solid rgba(242,237,224,.18); }
#xji-log .alt-body.on { display: block; }
#xji-log .alt-field { font: 10.5px/1.8 ui-monospace,Consolas,monospace; color: var(--ink); margin-top: 7px; }
#xji-log .alt-row { font: 10px/1.75 ui-monospace,Consolas,monospace; color: rgba(231,225,211,.55);
  padding-left: 12px; }
#xji-log .alt-note { font: 10px/1.7 ui-monospace,Consolas,monospace; color: rgba(231,225,211,.4);
  margin-top: 8px; }

#xji-meta { padding: 0 16px 10px; display: flex; flex-wrap: wrap; gap: 6px; }
#xji-meta i { font: 10px/1 ui-monospace,Consolas,monospace; font-style: normal; color: rgba(231,225,211,.5);
  border: 1px solid rgba(242,237,224,.14); padding: 4px 6px; }
#xji-meta i.warn { color: var(--zhu); border-color: rgba(217,72,63,.4); }

#xji-form { border-top: 1px solid rgba(242,237,224,.12); padding: 10px 12px 8px; }
#xji-form textarea {
  width: 100%; height: 52px; resize: none; background: rgba(255,255,255,.03); color: var(--ink);
  border: 1px solid rgba(242,237,224,.16); padding: 8px 9px; font: 12px/1.7 inherit;
  outline: none;
}
#xji-form textarea:focus { border-color: rgba(242,237,224,.38); }
#xji-form .row { display: flex; align-items: center; gap: 8px; margin-top: 7px; }
#xji-form .row small { font-size: 9.5px; color: rgba(231,225,211,.36); letter-spacing: .04em; }
#xji-form .row small a { color: rgba(231,225,211,.5); text-decoration: none;
  border-bottom: 1px dotted rgba(242,237,224,.3); margin-left: 2px; }
#xji-form .row small a:hover { color: var(--ink); border-bottom-color: rgba(242,237,224,.6); }
#xji-form button {
  margin-left: auto; padding: 6px 14px; cursor: pointer;
  background: rgba(217,72,63,.14); color: #f0d9b5; border: 1px solid rgba(217,72,63,.45);
  font: 11px/1 inherit; letter-spacing: .14em;
}
#xji-form button:disabled { opacity: .4; cursor: default; }

#xji-birth { border-bottom: 1px solid rgba(242,237,224,.08); }
#xji-birth summary {
  padding: 8px 16px; font-size: 10.5px; color: var(--ink-dim); letter-spacing: .1em; cursor: pointer;
  list-style: none;
}
#xji-birth summary::-webkit-details-marker { display: none; }
#xji-birth summary::before { content: "＋ "; color: rgba(242,237,224,.35); }
#xji-birth[open] summary::before { content: "－ "; }
#xji-birth .fields { display: grid; grid-template-columns: .9fr .9fr .6fr; gap: 6px; padding: 0 16px 10px; }
#xji-birth .fields input#xji-b-date { grid-column: 1 / -1; }
#xji-birth input {
  background: rgba(255,255,255,.03); border: 1px solid rgba(242,237,224,.14);
  color: var(--ink); font: 11px/1.4 ui-monospace,Consolas,monospace; padding: 6px 7px; outline: none; width: 100%;
}
#xji-birth input:focus { border-color: rgba(242,237,224,.34); }

/* 竖屏：整块贴底，别把铜环全遮住 */
@media (max-width: 640px) {
  #xji { right: 0; bottom: 0; width: 100vw; height: 76vh;
         border-left: 0; border-right: 0; border-bottom: 0; }
  #xji-trigger { right: 16px; bottom: 16px; }
  #xji-log .m { font-size: 13px; line-height: 1.9; }
  #xji-read { font-size: 9.5px; }
}
`

const HTML = `
<button id="xji-trigger" type="button"><span class="dot"></span>问 璇 玑</button>
<section id="xji" aria-label="璇玑">
  <div class="xji-head">
    <b>璇玑</b><span>器灵 · 只读不算</span>
    <button id="xji-keybtn" type="button" title="配置 API key" aria-label="配置 key">⚙</button>
    <button id="xji-close" type="button" aria-label="关闭">×</button>
  </div>
  <div id="xji-keybox" hidden>
    <div class="kb-status" id="xji-kstatus">检查中…</div>
    <div class="kb-row">
      <input id="xji-key" type="password" placeholder="sk-…（只存在这台机器的内存里）" spellcheck="false" autocomplete="off" />
    </div>
    <div class="kb-row">
      <button id="xji-ksave" type="button">保存并测试</button>
      <button id="xji-kclear" type="button">清除</button>
      <small id="xji-kmsg"></small>
    </div>
  </div>
  <div id="xji-read">读数载入中…</div>
  <details id="xji-birth">
    <summary>报生辰（可选，报了才排盘）</summary>
    <div class="fields">
      <input id="xji-b-date" placeholder="1996-04-18 14:06" />
      <input id="xji-b-lon" placeholder="经度 114.93" />
      <input id="xji-b-std" placeholder="时区经线 120" value="120" />
      <select id="xji-b-sex" style="background:rgba(255,255,255,.03);border:1px solid rgba(242,237,224,.14);color:var(--ink);font:11px ui-monospace,monospace;padding:6px">
        <option value="0">男</option><option value="1">女</option>
      </select>
    </div>
  </details>
  <div id="xji-log">
    <div class="m ai">铜环转着，字是死的。你要问什么，得先说完。</div>
  </div>
  <div id="xji-meta"></div>
  <form id="xji-form" autocomplete="off">
    <textarea id="xji-input" placeholder="问什么？也可以只让我念此刻的读数。" maxlength="500"></textarea>
    <div class="row">
      <small>AI 生成 · 不是预测 · <a href="/legal/disclaimer.html" target="_blank" rel="noopener">免责</a>
        <a href="/legal/privacy.html" target="_blank" rel="noopener">隐私</a>
        <a href="/legal/terms.html" target="_blank" rel="noopener">条款</a></small>
      <button id="xji-send" type="submit">问</button>
    </div>
  </form>
</section>
`

const style = document.createElement('style')
style.textContent = CSS
document.head.appendChild(style)

const holder = document.createElement('div')
holder.innerHTML = HTML
document.body.append(holder.firstElementChild, holder.lastElementChild)

const $ = (s) => document.querySelector(s)
const log = $('#xji-log')
// 依据里能落到原文的引用：「穷通宝鉴·乙日辰月」「子平真诠·论用神」等
const CITE_RE = /(?:穷通宝鉴|窮通寶鑑)·[甲乙丙丁戊己庚辛壬癸]日[子丑寅卯辰巳午未申酉戌亥]月|子平真[诠詮]·[^\s·，,。；;]+|神[峰峯]通考·[^\s·，,。；;]+|金不换[喜忌]·[甲乙丙丁戊己庚辛壬癸]/
const input = $('#xji-input')
const sendBtn = $('#xji-send')
const meta = $('#xji-meta')
const readLine = $('#xji-read')

const history = []
let busy = false

const escape = (s) => s.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]))

function addMsg(role, text) {
  const div = document.createElement('div')
  div.className = 'm ' + (role === 'user' ? 'me' : 'ai')
  div.textContent = text
  log.appendChild(div)
  log.scrollTop = log.scrollHeight
  return div
}

function readParams() {
  const birth = $('#xji-b-date').value.trim()
  const lonRaw = $('#xji-b-lon').value.trim()
  const longitude = Number(lonRaw) || 114.93
  const stdRaw = $('#xji-b-std').value.trim()
  const standard_longitude = Number(stdRaw) === 0 ? 120 : (Number(stdRaw) || 120)
  const gender = Number($('#xji-b-sex').value)
  return { birth: birth || null, longitude, gender, standard_longitude }
}

async function loadNow() {
  const { longitude, standard_longitude } = readParams()
  try {
    const r = await fetch(`/api/now?longitude=${longitude}&standard_longitude=${standard_longitude}`)
    const n = await r.json()
    // 钟表按出生地时区的标准经线算；真太阳时再按经度与均时差校正。
    readLine.innerHTML =
      `钟表 <em>${n.clock_local || n.clock_bj}</em>（经线 ${standard_longitude}°） · ` +
      `${(n.term && n.term.name) || n.jie.name}${n.term ? ' ' + n.term.at.slice(5, 16) : ''} · 月建 <em>${n.month_zhi}</em><br>` +
      `真太阳时 <em>${n.true_solar}</em>（校正 ${n.correction_minutes} 分）· 四柱 <em>${n.bazi}</em>`
    return n
  } catch (e) {
    readLine.textContent = '读数取不到：本地接口没起（server/app.py）。'
    return null
  }
}

function paintMeta(m) {
  const chips = []
  if (m.risk && m.risk.length) chips.push(`<i class="warn">触及 ${m.risk.join('/')} · 只讲象不给建议</i>`)
  if (m.warnings && m.warnings.length) {
    for (const w of m.warnings) chips.push(`<i class="warn">${w.kind === 'dst' ? '夏令时 +' + w.offset_minutes + ' 分' : w.kind}</i>`)
  }
  if (m.chart) chips.push(`<i>盘 ${m.chart}</i>`)
  if (m.focus) chips.push(`<i>聚焦 ${m.focus.ring}·${m.focus.label}</i>`)
  if (m.degraded) chips.push('<i class="warn">降级 · 只念读数</i>')
  if (m.blocked) chips.push(`<i class="warn">出口拦下 ${m.blocked} 条</i>`)
  chips.push(m.mock ? '<i class="warn">未接模型 · 演示读数</i>' : '<i>deepseek</i>')
  meta.innerHTML = chips.join('')
}

function renderEvidence(afterEl, groups) {
  if (!Array.isArray(groups) || !groups.length) return
  const count = groups.reduce((s, g) => s + (g.items || []).length, 0)
  const wrap = document.createElement('div')
  wrap.className = 'ev'

  const btn = document.createElement('button')
  btn.type = 'button'
  btn.className = 'ev-btn'
  btn.textContent = `依据 ${count} 条`

  const list = document.createElement('div')
  list.className = 'ev-list'
  for (const g of groups) {
    const h = document.createElement('div')
    h.className = 'ev-layer'
    h.textContent = g.layer
    list.appendChild(h)
    for (const it of g.items || []) {
      const row = document.createElement('div')
      row.className = 'ev-item'
      const m = String(it).match(CITE_RE)
      if (!m) {
        row.textContent = it
        list.appendChild(row)
        continue
      }
      const cite = m[0]
      row.append(document.createTextNode(String(it).slice(0, m.index)))
      const citeBtn = document.createElement('button')
      citeBtn.type = 'button'
      citeBtn.className = 'ev-cite'
      citeBtn.textContent = cite
      citeBtn.title = '看原文'
      row.appendChild(citeBtn)
      row.append(document.createTextNode(String(it).slice(m.index + cite.length)))
      citeBtn.addEventListener('click', async () => {
        const old = row.nextElementSibling
        if (old && old.classList.contains('ev-passage')) { old.remove(); return }
        const box = document.createElement('div')
        box.className = 'ev-passage'
        box.textContent = '查原文…'
        row.after(box)
        try {
          const d = await (await fetch(`/api/passage?cite=${encodeURIComponent(cite)}`)).json()
          if (!d.found) {
            box.textContent = `查不到原文：${d.reason || ''}`
            return
          }
          box.textContent = ''
          const h = document.createElement('b')
          h.textContent = `${d.title} · ${d.loc || ''}${d.verdict_text ? ' · ' + d.verdict_text : ''}`
          const q = document.createElement('div')
          q.textContent = `「${d.quote}」`
          const src = document.createElement('em')
          src.textContent = `　${d.quote_source || ''}`
          box.append(h, q, src)
          if (d.gloss) {
            const g = document.createElement('div')
            g.style.marginTop = '5px'
            g.textContent = `今译：${d.gloss}`
            const gs = document.createElement('em')
            gs.textContent = `　（${d.gloss_by || ''}）`
            g.appendChild(gs)
            box.appendChild(g)
          }
          if (d.note) {
            const n = document.createElement('div')
            n.style.marginTop = '4px'
            n.textContent = `按：${d.note}`
            box.appendChild(n)
          }
        } catch (e) {
          box.textContent = '取原文失败'
        }
        log.scrollTop = log.scrollHeight
      })
      list.appendChild(row)
    }
  }
  btn.addEventListener('click', () => {
    const on = list.classList.toggle('on')
    btn.classList.toggle('on', on)
    log.scrollTop = log.scrollHeight
  })

  // 换一派：同一张盘，另一组口径重算，差异逐条摆出来
  const alt = document.createElement('div')
  alt.className = 'alt'
  const altBtn = document.createElement('button')
  altBtn.type = 'button'
  altBtn.className = 'ev-btn'
  altBtn.textContent = '换一派'
  const altBody = document.createElement('div')
  altBody.className = 'alt-body'
  altBtn.addEventListener('click', () => {
    const on = altBody.classList.toggle('on')
    altBtn.classList.toggle('on', on)
    if (!on) { log.scrollTop = log.scrollHeight; return }
    const go = () => alt.scrollIntoView({ block: 'start' })
    if (!altBody.dataset.loaded) loadCompare(altBody).then(go)
    else go()
  })
  alt.append(altBtn, altBody)

  wrap.append(btn, list, alt)
  afterEl.after(wrap)
}

async function loadCompare(host) {
  const { birth, longitude, gender, standard_longitude } = readParams()
  if (!birth) {
    host.textContent = '先报生辰，才谈得上换一派。'
    host.dataset.loaded = '1'
    return
  }
  host.textContent = '重算中…'
  try {
    const u = `/api/compare?birth=${encodeURIComponent(birth)}&longitude=${longitude}` +
              `&gender=${gender}&standard_longitude=${standard_longitude}`
    const d = await (await fetch(u)).json()
    host.innerHTML = ''
    if (!d.diff || !d.diff.length) {
      const p = document.createElement('div')
      p.className = 'alt-note'
      p.textContent = '四种口径在这张盘上算出的结果一致——没有分歧可摆。'
      host.appendChild(p)
    } else {
      const baseKey = d.variants[0].key
      for (const row of d.diff) {
        const head = document.createElement('div')
        head.className = 'alt-field'
        head.textContent = `${row.field}：${row.values[baseKey]}`
        host.appendChild(head)
        for (const v of d.variants.slice(1)) {
          if (String(v[row.key]) === String(row.values[baseKey])) continue
          const li = document.createElement('div')
          li.className = 'alt-row'
          li.textContent = `${v.label} → ${v[row.key]}`
          host.appendChild(li)
        }
      }
      const note = document.createElement('div')
      note.className = 'alt-note'
      note.textContent = '两版都是真的，差别在口径。选哪一派，是你的决定，不是它的。'
      host.appendChild(note)
    }
    host.dataset.loaded = '1'
  } catch (e) {
    host.textContent = '取不到：' + e.message
  }
}

function applyFocus(f) {
  if (!f || !f.ring || !f.label) return
  const w = window.__wheel
  if (!w || typeof w.indexOf !== 'function') return
  const idx = w.indexOf(f.ring, f.label)
  if (idx < 0) return
  w.focusCell(f.ring, idx)
  // 供自检读取：环、字、格
  document.body.dataset.focus = `${f.ring}:${f.label}:${idx}`
}

async function ask(text) {
  if (busy) return
  busy = true
  sendBtn.disabled = true
  addMsg('user', text)
  history.push({ role: 'user', content: text })
  const { birth, longitude, gender, standard_longitude } = readParams()
  const bubble = addMsg('assistant', '')
  let acc = ''
  let metaState = {}
  let blocked = 0
  // 复述确认：先说清这次用的是哪份输入，免得答的是别人
  if (birth) {
    const line = document.createElement('div')
    line.className = 'm sys'
    line.textContent = `${birth} · 东经 ${longitude}（时区经线 ${standard_longitude}）· ${gender ? '女' : '男'}`
    log.insertBefore(line, bubble)
  }

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ messages: history.slice(-12), birth, gender,
                             place: { longitude, standard_longitude } }),
    })
    if (!res.ok) {
      let body = ''
      try { body = await res.text() } catch { }
      let hint = body.slice(0, 160)
      try {
        const j = JSON.parse(body)
        hint = j.hint || (j.retry_after ? `等 ${Math.ceil(j.retry_after)} 秒` : hint)
      } catch { }
      const err = document.createElement('div')
      err.className = 'err'
      err.textContent = res.status === 429 ? '太频繁了。' + hint : `接口 ${res.status}：${hint}`
      log.appendChild(err)
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const frames = buf.split('\n\n')
      buf = frames.pop()
      for (const frame of frames) {
        const ev = /^event: (.+)$/m.exec(frame)?.[1]
        const dataLine = /^data: (.+)$/m.exec(frame)?.[1]
        if (!ev || !dataLine) continue
        const data = JSON.parse(dataLine)
        if (ev === 'meta') { metaState = data; paintMeta(metaState); applyFocus(data.focus) }
        else if (ev === 'delta') { acc += data.text; bubble.textContent = acc; log.scrollTop = log.scrollHeight }
        else if (ev === 'degraded') {
          metaState = { ...metaState, degraded: data.reason }
          paintMeta(metaState)
        }
        else if (ev === 'violation') {
          blocked += data.length
          paintMeta({ ...metaState, blocked })
        }
        else if (ev === 'error') {
          const e = document.createElement('div')
          e.className = 'err'
          e.textContent = '接口出错：' + (data.body || data.message || data.status)
          log.appendChild(e)
        }
      }
    }
    if (acc) history.push({ role: 'assistant', content: acc })
    renderEvidence(bubble, metaState.evidence)
  } catch (e) {
    const err = document.createElement('div')
    err.className = 'err'
    err.textContent = '连不上本地接口：' + e.message
    log.appendChild(err)
  } finally {
    busy = false
    sendBtn.disabled = false
    log.scrollTop = log.scrollHeight
  }
}

$('#xji-trigger').addEventListener('click', () => {
  document.body.classList.add('xji-open')
  loadNow()
  input.focus()
})
$('#xji-close').addEventListener('click', () => document.body.classList.remove('xji-open'))

// ---- API key：网页上填，只存服务端内存 ----
const keyBox = $('#xji-keybox')
const keyStatus = $('#xji-kstatus')
const keyMsg = $('#xji-kmsg')
const keyInput = $('#xji-key')

async function refreshKey() {
  try {
    const d = await (await fetch('/api/config')).json()
    const src = { ui: '网页填的', env: '环境变量', none: '' }[d.key_source] || ''
    keyStatus.innerHTML = d.key_present
      ? `已配置 <b>${d.key_mask}</b>${src ? `（${src}）` : ''} · 模型 ${d.model}`
      : '还没配置 key —— 现在给我什么我都只能念读数，不会解释。'
  } catch (e) {
    keyStatus.textContent = '读不到配置'
  }
}

$('#xji-keybtn').addEventListener('click', () => {
  keyBox.hidden = !keyBox.hidden
  if (!keyBox.hidden) { refreshKey(); keyInput.focus() }
})

$('#xji-ksave').addEventListener('click', async () => {
  const key = keyInput.value.trim()
  if (!key) { keyMsg.textContent = '先贴一个 key'; return }
  keyMsg.textContent = '保存中…'
  try {
    const r = await fetch('/api/config/key', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key }),
    })
    if (!r.ok) { keyMsg.textContent = (await r.json()).detail || '没存上'; return }
    keyInput.value = ''
    keyMsg.textContent = '测试中…'
    const t = await (await fetch('/api/config/key/test', { method: 'POST' })).json()
    keyMsg.textContent = t.ok
      ? `可用（usage ${t.usage.prompt_tokens}+${t.usage.completion_tokens}）`
      : `保存了，但测试失败：${t.reason || ''}`
    refreshKey()
    loadNow()
  } catch (e) {
    keyMsg.textContent = '存不上：' + e.message
  }
})

$('#xji-kclear').addEventListener('click', async () => {
  await fetch('/api/config/key', { method: 'DELETE' })
  keyMsg.textContent = '已清除（环境变量里的 key 仍然生效，如果有的话）'
  refreshKey()
  loadNow()
})
addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && document.body.classList.contains('xji-open')) {
    document.body.classList.remove('xji-open')
  }
})
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    const text = input.value.trim()
    if (!text) return
    input.value = ''
    ask(text)
  }
})
$('#xji-form').addEventListener('submit', (e) => {
  e.preventDefault()
  const text = input.value.trim()
  if (!text) return
  input.value = ''
  ask(text)
})
$('#xji-birth').addEventListener('toggle', loadNow)
