/* 大六壬天地盘：外圈天盘（随月将转），内圈地盘（不动）。数据全部来自 /api/liuren。 */
const ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
const SECTORS = { plateIn: 206, plateOut: 268, heavenIn: 280, heavenOut: 344 }

const svg = document.getElementById('plate')
const kv = document.getElementById('kv')
const keTable = document.getElementById('ke')
const chuanBox = document.getElementById('chuan')
const ketiList = document.getElementById('keti')
const bifaList = document.getElementById('bifa')

const CX = 360, CY = 360

function pt(r, deg) {
  const a = (deg * Math.PI) / 180
  return [CX + r * Math.cos(a), CY + r * Math.sin(a)]
}

function wedge(r0, r1, a0, a1) {
  const [x0, y0] = pt(r1, a0)
  const [x1, y1] = pt(r1, a1)
  const [x2, y2] = pt(r0, a1)
  const [x3, y3] = pt(r0, a0)
  return `M${x0} ${y0} A${r1} ${r1} 0 0 1 ${x1} ${y1} L${x2} ${y2} A${r0} ${r0} 0 0 0 ${x3} ${y3} Z`
}

// 子在中轴上方，顺时针排
const center = (i) => -90 + i * 30

function el(name, attrs, text) {
  const n = document.createElementNS('http://www.w3.org/2000/svg', name)
  for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v)
  if (text != null) n.textContent = text
  return n
}

function draw(k) {
  svg.textContent = ''
  const heaven = k.tian_di_pan            // 地盘支 → 天盘支
  const jiang = k.tian_jiang_map          // 天盘支 → 天将
  const kong = new Set(k.xun_kong || [])
  const chuan = k.three_chuan || {}
  const marks = {}
  for (const [i, key] of ['chu', 'zhong', 'mo'].entries()) {
    const zhi = chuan[key] && chuan[key].zhi
    if (!zhi) continue
    const pos = Object.keys(heaven).find((d) => heaven[d] === zhi)
    if (pos) marks[pos] = ['初', '中', '末'][i]
  }
  const dayGanHome = (k.four_classes && k.four_classes[0] && k.four_classes[0].down_position) || null

  // 参考圆
  svg.appendChild(el('circle', { cx: CX, cy: CY, r: SECTORS.plateOut, fill: 'none', stroke: 'rgba(242,237,224,.16)' }))
  svg.appendChild(el('circle', { cx: CX, cy: CY, r: SECTORS.plateIn, fill: 'none', stroke: 'rgba(242,237,224,.10)' }))
  svg.appendChild(el('circle', { cx: CX, cy: CY, r: SECTORS.heavenOut, fill: 'none', stroke: 'rgba(242,237,224,.16)' }))
  svg.appendChild(el('circle', { cx: CX, cy: CY, r: 96, fill: 'none', stroke: 'rgba(242,237,224,.08)' }))
  svg.appendChild(el('text', { x: CX, y: CY - 16, 'text-anchor': 'middle', fill: 'rgba(231,225,211,.35)',
                               'font-size': 11, 'letter-spacing': 4 }, '天地盘'))
  svg.appendChild(el('text', { x: CX, y: CY + 22, 'text-anchor': 'middle', fill: 'rgba(231,225,211,.6)',
                               'font-size': 16 }, `${k.yue_jiang}将加${k.zhan_shi}时`))

  ZHI.forEach((zhi, i) => {
    const a0 = center(i) - 15
    const a1 = center(i) + 15
    const up = heaven[zhi]
    const isChuan = Boolean(marks[zhi])

    // 地盘
    svg.appendChild(el('path', {
      d: wedge(SECTORS.plateIn, SECTORS.plateOut, a0, a1),
      fill: dayGanHome === zhi ? 'rgba(240,217,181,.07)' : 'rgba(255,255,255,.012)',
      stroke: 'rgba(242,237,224,.10)',
    }))
    const [px, py] = pt((SECTORS.plateIn + SECTORS.plateOut) / 2, center(i))
    svg.appendChild(el('text', { x: px, y: py + 6, 'text-anchor': 'middle',
                                 fill: dayGanHome === zhi ? '#f0d9b5' : 'rgba(231,225,211,.55)',
                                 'font-size': 20 }, zhi))

    // 天盘
    const path = el('path', {
      d: wedge(SECTORS.heavenIn, SECTORS.heavenOut, a0, a1),
      fill: isChuan ? 'rgba(217,72,63,.10)' : 'rgba(255,255,255,.012)',
      stroke: isChuan ? 'rgba(217,72,63,.55)' : 'rgba(242,237,224,.10)',
    })
    path.dataset.pos = zhi
    path.dataset.up = up
    if (marks[zhi]) path.dataset.mark = marks[zhi]
    svg.appendChild(path)
    const [hx, hy] = pt(SECTORS.heavenIn + 22, center(i))
    svg.appendChild(el('text', { x: hx, y: hy + 7, 'text-anchor': 'middle', fill: kong.has(up) ? 'rgba(231,225,211,.4)' : '#e7e1d3',
                                 'font-size': 22 }, up))
    const [jx, jy] = pt(SECTORS.heavenOut - 14, center(i))
    svg.appendChild(el('text', { x: jx, y: jy + 4, 'text-anchor': 'middle', fill: 'rgba(231,225,211,.45)',
                                 'font-size': 10 }, jiang[up] || ''))

    if (marks[zhi]) {
      const [mx, my] = pt(SECTORS.heavenOut - 2, center(i))
      svg.appendChild(el('circle', { cx: mx, cy: my, r: 11, fill: '#0a0a0a', stroke: 'rgba(217,72,63,.8)' }))
      svg.appendChild(el('text', { x: mx, y: my + 4, 'text-anchor': 'middle', fill: '#d9483f', 'font-size': 11 },
        marks[zhi]))
    }
  })
}

function panel(k) {
  const g = k.ganzhi || {}
  kv.innerHTML = [
    ['四柱', `${g.year} ${g.month} ${g.day} ${g.hour}`],
    ['月将', k.yue_jiang], ['占时', k.zhan_shi],
    ['昼占', k.is_day_time ? '是' : '否'], ['贵人', k.gui_ren],
    ['旬首', k.xun_shou], ['旬空', (k.xun_kong || []).join(' ')],
  ].map(([a, b]) => `<span>${a} <b>${b}</b></span>`).join('')

  const cols = (k.four_classes || []).slice().reverse()  // 四课在左，一课在右
  keTable.innerHTML = `<tr>${cols.map((_, i) => `<th>${['四课', '三课', '二课', '一课'][i]}</th>`).join('')}</tr>`
    + `<tr>${cols.map((c) => `<td class="up">${c.up}</td>`).join('')}</tr>`
    + `<tr>${cols.map((c) => `<td class="down">${c.down_show || c.down}</td>`).join('')}</tr>`
    + `<tr>${cols.map((c) => `<td class="meta">${c.up_info.liu_qin}·${c.up_info.tian_jiang}${c.up_info.is_kong ? '·空' : ''}</td>`).join('')}</tr>`

  const t = k.three_chuan || {}
  chuanBox.innerHTML = ['chu', 'zhong', 'mo'].map((key, i) => {
    const c = t[key] || {}
    return `<div><div class="lab">${['初传', '中传', '末传'][i]}</div>
      <div class="zhi">${c.zhi || '—'}</div>
      <div class="meta">${c.liu_qin || ''} ${c.tian_jiang || ''}${c.is_kong ? ' 空亡' : ''}</div></div>`
  }).join('') + `<div style="flex:0 0 auto;border:0;text-align:left;padding-left:6px">
      <div class="lab">取传</div><div class="meta">${t.method || ''}<br>${t.ge || ''}</div></div>`

  ketiList.innerHTML = (k.keti || []).map((x) =>
    `<li><em>${x.name}${x.ge ? '·' + x.ge : ''}</em> ${x.vol ? `<small>卷${x.vol}</small>` : ''}<br>
     <small>${x.text || ''}</small></li>`).join('') || '<li>无</li>'

  const hit = (k.bifa || []).filter((b) => b.checked)
  bifaList.innerHTML = (hit.length ? hit : (k.bifa || []).slice(0, 2)).map((b) =>
    `<li class="item" data-no="${b.no}"><em>${b.verse}</em>
     <small>第${b.no}条 · ${b.checked ? '成立' : '未成立'}${b.vol ? ' · 卷' + b.vol : ''}</small><br>
     <small>${b.rule || ''}</small></li>`).join('') || '<li>无</li>'
}

// 点毕法条目 → 展开《六壬大全》那句注
bifaList.addEventListener('click', async (ev) => {
  const li = ev.target.closest('li.item')
  if (!li) return
  const old = li.querySelector('.src')
  if (old) { old.remove(); return }
  const box = document.createElement('div')
  box.className = 'src'
  box.textContent = '查原文…'
  li.appendChild(box)
  try {
    const d = await (await fetch(`/api/liuren/bifa?no=${li.dataset.no}`)).json()
    if (!d.found) { box.textContent = d.reason || '查不到'; return }
    box.textContent = d.no_commentary
      ? `〔${d.verse}〕卷${d.vol}\n这一条原书没有注——不补写。`
      : `〔${d.verse}〕卷${d.vol}　${d.edition}\n${d.commentary}`
  } catch (e) {
    box.textContent = '取原文失败'
  }
})

function nowBJ() {
  const d = new Date(Date.now() + 8 * 3600e3)
  return d.toISOString().slice(0, 16).replace('T', ' ')
}

async function load(at) {
  const q = at ? `?at=${encodeURIComponent(at)}` : ''
  const k = await (await fetch(`/api/liuren${q}`)).json()
  draw(k)
  panel(k)
  document.body.dataset.ke = `${k.yue_jiang}|${k.zhan_shi}|${k.three_chuan?.method || ''}`
  // 把这一刻写进 URL：同一张盘可以发给别人，勘误也有东西可复现
  syncUrl({ at: at || '' })
}

function syncUrl(params) {
  const u = new URL(location.href)
  for (const [k, v] of Object.entries(params)) {
    if (v) u.searchParams.set(k, v)
    else u.searchParams.delete(k)
  }
  history.replaceState(null, '', u)
}

const atInput = document.getElementById('at')
const fromUrl = new URLSearchParams(location.search).get('at')
atInput.value = fromUrl || nowBJ()
document.getElementById('go').addEventListener('click', () => load(atInput.value.trim() || undefined))
atInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') load(atInput.value.trim() || undefined) })

load(atInput.value.trim() || nowBJ())
