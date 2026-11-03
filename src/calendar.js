/* 节气历：从 /api/calendar 拿交节时刻，从 data.js 拿七十二候的名字——候名只有一份。 */
import { RINGS_DEF } from './data.js'

const list = document.getElementById('list')
const moonBox = document.getElementById('moons')
const yearLabel = document.getElementById('yearLabel')
let year = new Date().getFullYear()

const HOU = RINGS_DEF.find((r) => r.key === '七十二候').items.map((i) => i.label)
const DAY = 86400000

function addDays(stamp, n) {
  const [d, t] = stamp.split(' ')
  // 交节时刻按 +08:00 解析，算完再折回东八区墙钟，避免看的人本地时区把它推到隔天
  const base = Date.parse(`${d}T${t}+08:00`)
  const x = new Date(base + n * DAY + 8 * 3600e3)
  return `${String(x.getUTCMonth() + 1).padStart(2, '0')}-${String(x.getUTCDate()).padStart(2, '0')}`
}

function nowStamps() {
  // 东八区当下的钟表时间，用来标记「现在落在哪一节气」
  return new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 19).replace('T', ' ')
}

async function renderMoons() {
  moonBox.textContent = '载入中…'
  const d = await (await fetch(`/api/moon-calendar?year=${year}`)).json()
  const now = nowStamps().slice(0, 16)
  const next = d.events.find((e) => e.at >= now)
  moonBox.innerHTML = d.events.map((e) => {
    const cls = next && e.at === next.at ? ' next' : ''
    return `<span class="moon${cls}"><b>${e.kind}</b>${e.at.slice(5, 16)}</span>`
  }).join('') || '<span class="moon">这一年没有朔望记录</span>'
}

async function render() {
  yearLabel.textContent = `${year} 年`
  list.textContent = '载入中…'
  const d = await (await fetch(`/api/calendar?year=${year}`)).json()
  const now = nowStamps()
  let currentName = null
  for (const t of d.terms) if (t.at <= now) currentName = t.name

  list.innerHTML = d.terms.map((t) => {
    const hou = HOU.slice(t.ring_index * 3, t.ring_index * 3 + 3)
    const nowCls = t.name === currentName ? ' now' : ''
    const badge = t.name === currentName ? '<span class="badge">此刻</span>' : ''
    const houLine = hou.map((h, i) => `<b>${h}</b> ${addDays(t.at, i * 5)}`).join('　')
    return `<div class="row${nowCls}">
      <div class="name">${t.name}${badge}</div>
      <div class="at">${t.at}</div>
      <div class="hou">${houLine}</div>
    </div>`
  }).join('')

  renderMoons()
}

document.getElementById('prev').addEventListener('click', () => { year -= 1; render() })
document.getElementById('next').addEventListener('click', () => { year += 1; render() })
document.getElementById('today').addEventListener('click', async () => {
  year = new Date().getFullYear()
  await render()
  document.querySelector('.row.now')?.scrollIntoView({ block: 'center', behavior: 'smooth' })
})
render()
