/* 奇门九宫方阵（3D 透视版）。不共用周天引擎：3×3 是方阵，硬塞进环会变形。
   这一版用 CSS 透视把同一份数据摆成斜置的九宫，交互只做「点开看细节」。 */
const LAYOUT = [
  [4, '巽', '东南'], [9, '离', '南'], [2, '坤', '西南'],
  [3, '震', '东'], [5, '中', '中宫'], [7, '兑', '西'],
  [8, '艮', '东北'], [1, '坎', '北'], [6, '乾', '西北'],
]
const ZHENG = { 1: '正北', 2: '西南', 3: '正东', 4: '东南', 5: '中', 6: '西北', 7: '正西', 8: '东北', 9: '正南' }

const board = document.getElementById('board')
const detail = document.getElementById('detail')
const el = (id) => document.getElementById(id)

const nowBJ = () => new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 16).replace('T', ' ')

function render(r) {
  const pan = r.pan || {}
  const pal = pan.palaces || {}
  board.innerHTML = LAYOUT.map(([g, name, dir]) => {
    const p = pal[String(g)] || {}
    const cls = ['cell']
    if (g === 5) cls.push('center')
    if (pan.zhifu_gong === g) cls.push('zhifu')
    if (pan.zhishi_gong === g) cls.push('zhishi')
    const marks = [pan.zhifu_gong === g ? '直符' : '', pan.zhishi_gong === g ? '直使' : '']
      .filter(Boolean).join(' ')
    const tian = (p.tian || []).join('')
    return `<div class="${cls.join(' ')}" data-gong="${g}" data-tian="${tian}"
                 data-star="${p.star || ''}" data-door="${p.door || ''}"
                 data-shen="${p.shen || ''}" data-di="${(p.di || []).join('')}">
      <div class="top"><span class="shen">${p.shen || ''}</span><span>${name}${g} ${dir}</span></div>
      <div class="mid"><span class="tian">${tian || '—'}</span><span class="star">${p.star || ''}</span></div>
      <div class="door">${p.door ? p.door + '门' : ''}</div>
      ${marks ? `<div class="mark">${marks}</div>` : ''}
      <div class="di">${(p.di || []).join('')}</div>
    </div>`
  }).join('')

  const sz = r.sizhu || {}
  el('sz').textContent = `${sz.year} ${sz.month} ${sz.day} ${sz.hour}`
  el('ju').textContent = `${r.ju?.dun}遁 ${r.ju?.ju} 局 · ${r.ju?.jieqi}${r.ju?.yuan}元`
  el('zf').textContent = `${pan.zhifu} @ ${pan.zhifu_gong} 宫`
  el('zs').textContent = `${pan.zhishi}门 @ ${pan.zhishi_gong} 宫`

  board.querySelectorAll('.cell').forEach((cell) => {
    cell.addEventListener('click', () => {
      const g = +cell.dataset.gong
      if (g === 5) { detail.textContent = '中宫：地盘 ' + (cell.dataset.di || '—') + '；中宫不列门、星、神。'; return }
      detail.innerHTML = `<em>${LAYOUT.find((x) => x[0] === g)[1]}${g} 宫（${ZHENG[g]}）</em>　` +
        `八神 ${cell.dataset.shen || '—'}　天盘 ${cell.dataset.tian || '—'}　` +
        `九星 ${cell.dataset.star || '—'}　八门 ${cell.dataset.door || '—'}门　` +
        `地盘 ${cell.dataset.di || '—'}`
    })
  })
  document.body.dataset.ju = `${r.ju?.dun}|${r.ju?.ju}|${pan.zhifu_gong}|${pan.zhishi_gong}`
}

async function load(at) {
  const q = at ? `?at=${encodeURIComponent(at)}` : ''
  render(await (await fetch(`/api/qimen${q}`)).json())
  const u = new URL(location.href)
  if (at) u.searchParams.set('at', at); else u.searchParams.delete('at')
  history.replaceState(null, '', u)
}

// 轻微视差：让人看出是立体摆放，但不至于晃
const stage = document.querySelector('.scene')
stage.addEventListener('pointermove', (e) => {
  const x = (e.clientX / innerWidth - 0.5) * 8
  const y = (e.clientY / innerHeight - 0.5) * 6
  board.style.transform = `rotateX(${30 - y}deg) rotateZ(${-9 + x}deg) translateY(-140px)`
})
stage.addEventListener('pointerleave', () => {
  board.style.transform = 'rotateX(30deg) rotateZ(-9deg) translateY(-140px)'
})

const atInput = el('at')
const fromUrl = new URLSearchParams(location.search).get('at')
atInput.value = fromUrl || nowBJ()
el('go').addEventListener('click', () => load(atInput.value.trim() || undefined))
atInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') load(atInput.value.trim() || undefined) })
load(atInput.value.trim() || nowBJ())
