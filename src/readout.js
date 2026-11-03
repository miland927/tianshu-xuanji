/* 底部读数条：不开面板也能读此刻。点某一段，环就转到那一格。 */
import { RINGS_DEF } from './data.js'

const HOU = RINGS_DEF.find((r) => r.key === '七十二候').items.map((i) => i.label)
const DAY = 86400000

// 一个节气三候，每候约五日；余下的零头归最后一候
function houOf(term) {
  if (!term || term.index == null) return null
  const at = Date.parse(term.at.replace(' ', 'T') + '+08:00')
  const days = (Date.now() - at) / DAY
  const i = Math.min(2, Math.max(0, Math.floor(days / 5)))
  return { label: HOU[term.index * 3 + i] || null, nth: ['初', '二', '三'][i] }
}
const CSS = `
#ro {
  position: fixed; left: 0; bottom: 0; z-index: 20;
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 14px;
  width: min(82vw, 1040px); padding: 11px 26px 13px;
  background: linear-gradient(to right, rgba(5,5,5,.97) 0%, rgba(5,5,5,.95) 90%, rgba(5,5,5,0) 100%);
  font: 10.5px/1.9 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color: rgba(231,225,211,.52); letter-spacing: .02em;
  pointer-events: none;
}
#ro .seg { pointer-events: auto; cursor: pointer; border-bottom: 1px solid transparent;
  transition: color .18s, border-color .18s; white-space: nowrap; }
#ro .seg:hover { color: var(--ink); border-bottom-color: rgba(242,237,224,.35); }
#ro .seg b { font-weight: 500; color: rgba(231,225,211,.86); }
#ro a.seg { color: rgba(231,225,211,.5); text-decoration: none; }
#ro a.seg:hover { color: var(--ink); }
#ro .seg.static { cursor: default; }
#ro .seg.static:hover { color: rgba(231,225,211,.52); border-bottom-color: transparent; }
#ro .seg.static b { color: rgba(231,225,211,.86); }
#ro .moonglyph { width: 13px; height: 13px; vertical-align: -2px; margin-right: 5px; display: inline-block; }
#ro .sep { color: rgba(242,237,224,.18); }
#ro .dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%;
  background: var(--zhu); margin-right: 7px; vertical-align: 1px; box-shadow: 0 0 7px var(--zhu); }
body.xji-open #ro { opacity: 0; pointer-events: none; transition: opacity .2s; }

@media (max-width: 640px) {
  #ro { left: 0; right: 0; bottom: 0; max-width: none; font-size: 9.5px;
        padding: 9px 16px 10px; gap: 0 10px; flex-wrap: wrap;
        background: rgba(5,5,5,.92); }
  #ro .seg:nth-child(n+6) { display: none; }
}
`

const seg = (label, value, ring, cell) =>
  `<span class="seg" data-ring="${ring}" data-cell="${cell}">${label} <b>${value}</b></span>`

const holder = document.createElement('div')
holder.id = 'ro'
holder.innerHTML = '<span class="dot"></span><span class="seg">载入读数…</span>'

// 画一个小月亮：逐像素算「这个点有没有被照到」，比拼两段弧稳当
function drawMoon(canvas, illum, waxing) {
  const ctx = canvas.getContext('2d')
  const size = canvas.width
  const r = size / 2 - 1
  const E = Math.acos(Math.max(-1, Math.min(1, 1 - 2 * illum)))   // 0 新月 … π 满月
  const side = waxing ? 1 : -1
  const cosE = Math.cos(E), sinE = Math.sin(E)
  const img = ctx.createImageData(size, size)
  const data = img.data
  for (let py = 0; py < size; py++) {
    for (let px = 0; px < size; px++) {
      const u = (px + 0.5 - size / 2) / r
      const v = (py + 0.5 - size / 2) / r
      const d2 = u * u + v * v
      if (d2 > 1) continue
      const z = Math.sqrt(1 - d2)
      const lit = -z * cosE + u * sinE * side > 0
      const i = (py * size + px) * 4
      const tone = lit ? 231 : 90
      data[i] = tone; data[i + 1] = tone * 0.97; data[i + 2] = tone * 0.88
      data[i + 3] = lit ? 235 : 70
    }
  }
  ctx.putImageData(img, 0, 0)
}

const style = document.createElement('style')
style.textContent = CSS
document.head.appendChild(style)
document.body.appendChild(holder)

let last = null

function render(n) {
  last = n
  const [, , day, hour] = n.bazi.split(' ')
  const sid = n.sidereal || {}
  const xiu = sid.xiu ? sid.xiu.name : ''
  const sun = n.sunrise_sunset ? `日出 ${n.sunrise_sunset[0].slice(11, 16)} · 日落 ${n.sunrise_sunset[1].slice(11, 16)}` : ''
  const hou = houOf(n.term)
  holder.innerHTML = [
    '<span class="dot"></span>',
    seg('节气', `${n.term ? n.term.name : n.jie.name}${hou ? '·' + hou.nth + '候' : ''}`, '二十四节气', n.term ? n.term.name : n.jie.name),
    '<span class="sep">/</span>',
    hou ? seg('候', hou.label, '七十二候', hou.label) : '',
    hou ? '<span class="sep">/</span>' : '',
    seg('月建', n.month_zhi, '十二地支', n.month_zhi),
    '<span class="sep">/</span>',
    seg('日柱', day, '六十甲子', day),
    '<span class="sep">/</span>',
    seg('时柱', hour, '十二地支', hour[1]),
    '<span class="sep">/</span>',
    seg('真太阳', `${n.true_solar.slice(11, 16)}`, '二十四节气', n.term ? n.term.name : n.jie.name),
    '<span class="sep">/</span>',
    xiu ? seg('宿', xiu, '二十八宿', xiu) : '',
    n.moon ? `<span class="sep">/</span><span class="seg static"><canvas class="moonglyph" width="34" height="34"></canvas>月 <b>${n.moon.name} ${Math.round(n.moon.illum * 100)}%</b></span>` : '',
    sun ? `<span class="sep">/</span><span class="seg static">${sun}</span>` : '',
    '<span class="sep">/</span><a class="seg" href="/calendar.html" title="节气历">历</a>',
    '<span class="sep">/</span><a class="seg" href="/liuren.html" title="六壬天地盘">课</a>',
    '<span class="sep">/</span><a class="seg" href="/qimen.html" title="奇门九宫">门</a>',
    '<span class="sep">/</span><a class="seg" href="/ziwei.html" title="紫微十二宫">微</a>',
    '<span class="sep">/</span><a class="seg" href="/year.html" title="年度报告">年</a>',
    '<span class="sep">/</span><a class="seg" href="/guide.html" title="怎么用">?</a>',
  ].join('')

  const glyph = holder.querySelector('.moonglyph')
  if (glyph && n.moon) drawMoon(glyph, n.moon.illum, n.moon.waxing)
}

async function load() {
  try {
    const n = await (await fetch('/api/now')).json()
    render(n)
    document.body.dataset.readout = `${n.month_zhi}|${n.bazi}|${n.sidereal?.xiu?.name || ''}`
  } catch {
    holder.innerHTML = '<span class="dot"></span><span class="seg">读数取不到（接口没起）</span>'
  }
}

holder.addEventListener('click', (e) => {
  const el = e.target.closest('.seg')
  if (!el || !el.dataset.ring || !window.__wheel) return
  const ring = el.dataset.ring
  const label = el.dataset.cell
  const idx = window.__wheel.indexOf(ring, label)
  if (idx < 0) return
  window.__wheel.focusCell(ring, idx)
  document.body.dataset.focus = `${ring}:${label}:${idx}`
})

load()
setInterval(load, 60_000)
document.addEventListener('visibilitychange', () => { if (!document.hidden) load() })
window.__readout = () => last
