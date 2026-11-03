/* 奇门九宫：三三格，按洛书方位排。数据来自 /api/qimen，页面只负责画。 */
const LAYOUT = [
  [4, '巽', '东南'], [9, '离', '南'], [2, '坤', '西南'],
  [3, '震', '东'], [5, '中', '中宫'], [7, '兑', '西'],
  [8, '艮', '东北'], [1, '坎', '北'], [6, '乾', '西北'],
]

const grid = document.getElementById('grid')
const kv = document.getElementById('kv')
const zhifuBox = document.getElementById('zhifu')
const gejuList = document.getElementById('geju')

function cell(gong, num, dir, p, flags) {
  const cls = ['gong']
  if (num === 5) cls.push('center')
  if (flags.zhifu) cls.push('zhifu')
  if (flags.zhishi) cls.push('zhishi')
  const di = (p.di || []).join('')
  const tian = (p.tian || []).join('')
  const mark = [flags.zhifu ? '直符' : '', flags.zhishi ? '直使' : ''].filter(Boolean).join(' ')
  return `<div class="${cls.join(' ')}" data-gong="${num}" data-tian="${tian}" data-door="${p.door || ''}"
               data-star="${p.star || ''}" data-shen="${p.shen || ''}" data-di="${di}">
    <div class="top"><span class="shen">${p.shen || ''}</span><span class="corner">${gong}${num} ${dir}${mark ? ' · ' + mark : ''}</span></div>
    <div class="mid"><span class="tian">${tian || '—'}</span><span class="star">${p.star || ''}</span></div>
    <div class="door">${p.door || ''}</div>
    <div class="di">${di}</div>
  </div>`
}

function draw(r) {
  const pan = r.pan || {}
  const palaces = pan.palaces || {}
  grid.innerHTML = LAYOUT.map(([num, gong, dir]) =>
    cell(gong, num, dir, palaces[String(num)] || {}, {
      zhifu: pan.zhifu_gong === num,
      zhishi: pan.zhishi_gong === num,
    })).join('')

  const ju = r.ju || {}
  const sz = r.sizhu || {}
  const sizhu = typeof sz === 'object' ? `${sz.year || ''} ${sz.month || ''} ${sz.day || ''} ${sz.hour || ''}`.trim() : String(sz)
  kv.innerHTML = [
    ['四柱', sizhu], ['节气', `${ju.jieqi || ''} ${ju.yuan || ''}元`],
    ['局', `${ju.dun || ''}遁 ${ju.ju || ''} 局`], ['定局', ju.mode || ''],
    ['符头', ju.futou || ''], ['交节', ju.jieqi_time || ''],
    ['旬', pan.xun || ''], ['旬空', r.kong?.zhi || ''],
    ['马星', r.ma?.zhi ? `${r.ma.zhi}（${r.ma.gong}宫）` : ''],
    ['占时', pan.hour || ''],
  ].map(([a, b]) => `<span>${a} <b>${b}</b></span>`).join('')

  const gongName = (n) => {
    if (n == null) return '—'
    const hit = LAYOUT.find((x) => x[0] === n)
    return hit ? hit[1] + n : `${n}`
  }
  zhifuBox.innerHTML = [
    ['直符', `${pan.zhifu || ''} → ${gongName(pan.zhifu_gong)}宫`],
    ['直使', `${pan.zhishi || ''}门 → ${gongName(pan.zhishi_gong)}宫`],
  ].map(([a, b]) => `<span>${a} <b>${b}</b></span>`).join('')

  gejuList.innerHTML = (r.geju || []).map((x) => {
    const bad = x.verdict === '凶'
    return `<li class="${bad ? 'xiong' : ''}" data-cite="${x.cite || ''}">
      <span class="name">${x.name}</span>
      <span style="color:var(--dim);font-size:11px">${x.verdict} · ${gongName(x.gong)}宫</span>
      <small>「${x.quote || ''}」${x.cite ? '——' + x.cite.replace('|', '·') : ''}</small>
    </li>`
  }).join('') || '<li><span class="name">无</span><small>这一局没有成格</small></li>'

  gejuList.querySelectorAll('li[data-cite]').forEach((li) => {
    li.style.cursor = 'pointer'
    li.addEventListener('click', async () => {
      const old = li.querySelector('.src')
      if (old) { old.remove(); return }
      const box = document.createElement('div')
      box.className = 'src'
      box.textContent = '查原文…'
      li.appendChild(box)
      try {
        const d = await (await fetch(`/api/qimen/passage?cite=${encodeURIComponent(li.dataset.cite)}`)).json()
        box.textContent = d.found
          ? `〔${d.title} 卷${d.vol} · ${d.chapter}〕　${d.edition}\n${d.text}`
          : (d.reason || '查不到')
      } catch (e) {
        box.textContent = '取原文失败'
      }
    })
  })

  document.body.dataset.ju = `${ju.dun}|${ju.ju}|${pan.zhifu_gong}|${pan.zhishi_gong}|${(r.geju || []).length}`
}

function nowBJ() {
  return new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 16).replace('T', ' ')
}

async function load(at) {
  const q = at ? `?at=${encodeURIComponent(at)}` : ''
  draw(await (await fetch(`/api/qimen${q}`)).json())
  // 把这一刻写进 URL：同一局可以发给别人，勘误也有东西可复现
  const u = new URL(location.href)
  if (at) u.searchParams.set('at', at)
  else u.searchParams.delete('at')
  history.replaceState(null, '', u)
}

const atInput = document.getElementById('at')
const fromUrl = new URLSearchParams(location.search).get('at')
atInput.value = fromUrl || nowBJ()
document.getElementById('go').addEventListener('click', () => load(atInput.value.trim() || undefined))
atInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') load(atInput.value.trim() || undefined) })
load(atInput.value.trim() || nowBJ())
