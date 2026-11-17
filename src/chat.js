/* 璇玑的对话逻辑：流式回答、依据、换一派、key。
 * 版面与层级（观 → 问 → 定）在 inscription-panel.js；这里只用它建好的 #xji-* 节点。 */
import { panel } from './inscription-panel.js'

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
let lastEcho = ''

// 桌面上滚的是对话区；竖屏/矮屏上整条铭文栏一起滚（见 inscription-panel 的 CSS），两边都推到底
const panelEl = $('#xji')
function scrollEnd() {
  log.scrollTop = log.scrollHeight
  if (panelEl.scrollHeight > panelEl.clientHeight + 1) panelEl.scrollTop = panelEl.scrollHeight
}

const escape = (s) => s.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]))

function addMsg(role, text) {
  const div = document.createElement('div')
  div.className = 'm ' + (role === 'user' ? 'me' : 'ai')
  div.textContent = text
  log.appendChild(div)
  scrollEnd()
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
        scrollEnd()
      })
      list.appendChild(row)
    }
  }
  btn.addEventListener('click', () => {
    const on = list.classList.toggle('on')
    btn.classList.toggle('on', on)
    scrollEnd()
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
    if (!on) { scrollEnd(); return }
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
  // 只在「问」里转环：定 时四柱已经点亮，别换成单格；观 时栏已收起，回答迟到也不该把镜头拽走
  if (panel.layer !== 'wen') return
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
  // 同一份生辰只复述一次；换了生辰才再说
  const echo = birth ? `${birth} · 东经 ${longitude}（时区经线 ${standard_longitude}）· ${gender ? '坤造' : '乾造'}` : ''
  if (echo && echo !== lastEcho) {
    const line = document.createElement('div')
    line.className = 'm sys'
    line.textContent = echo
    log.insertBefore(line, bubble)
  }
  lastEcho = echo

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
        else if (ev === 'delta') { acc += data.text; bubble.textContent = acc; scrollEnd() }
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
    scrollEnd()
    // 「起」的时候璇玑正忙：那一问排在这里，说完接着问
    if (queued) { const t = queued; queued = null; setTimeout(() => ask(t), 0) }
  }
}

// 打开、收起、Esc 逐层回退都归铭文栏管；这里只在打开时刷新读数，并接住「起」之后的那一问
let queued = null
panel.onOpen(loadNow)
panel.setAsker((text) => { if (busy) queued = text; else ask(text) })

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

$('#xji-keybtn').addEventListener('click', (e) => {
  keyBox.hidden = !keyBox.hidden
  e.currentTarget.setAttribute('aria-expanded', String(!keyBox.hidden))
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
// 璇玑还在说的时候不收新问题：字留在输入框里，不清空、不吞掉，说完再发
function send() {
  const text = input.value.trim()
  if (!text) return
  if (busy) { input.classList.add('wait'); setTimeout(() => input.classList.remove('wait'), 900); return }
  input.value = ''
  ask(text)
}
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
})
$('#xji-form').addEventListener('submit', (e) => { e.preventDefault(); send() })
// 经度、时区经线一改，顶上的读数（钟表、真太阳时）跟着改
for (const id of ['#xji-b-lon', '#xji-b-std']) $(id).addEventListener('change', loadNow)
