/* 紫微十二宫：4×4 外环十二格，中间 2×2 放命主身主。数据来自 /api/ziwei。 */
const POS = {
  巳: [1, 1], 午: [1, 2], 未: [1, 3], 申: [1, 4],
  辰: [2, 1], /* 中宫 2,2-3,3 */        酉: [2, 4],
  卯: [3, 1],                             戌: [3, 4],
  寅: [4, 1], 丑: [4, 2], 子: [4, 3], 亥: [4, 4],
}

const board = document.getElementById('board')

const huaBadge = (hua) => `<span class="hua${hua === '忌' ? ' ji' : ''}">${hua}</span>`

function starHTML(s) {
  const cls = s.kind === 'main' ? 'main' : ''
  const miao = s.miao ? `<span class="miao">${s.miao}</span>` : ''
  // 生年四化直接挂在星上（库里的 st["hua"]），不要拿宫干飞化去凑
  return `<span class="${cls}">${s.name}</span>${miao}${s.hua ? huaBadge(s.hua) : ''}`
}

function render(zw) {
  const cells = zw.palaces.map((p) => {
    const [row, col] = POS[p.zhi] || [1, 1]
    const cls = ['palace']
    if (p.zhi === zw.ming) cls.push('ming')
    if (p.is_shen) cls.push('shen')
    const mains = (p.stars || []).filter((s) => s.kind === 'main')
    const minors = (p.stars || []).filter((s) => s.kind !== 'main')
    const mainHTML = mains.length
      ? mains.map((s) => starHTML(s)).join('　')
      : '<span style="color:rgba(231,225,211,.28)">（无主星）</span>'
    const minorHTML = minors.slice(0, 6)
      .map((s) => `<span>${s.name}</span>${s.hua ? huaBadge(s.hua) : ''}`).join('　')
    const dx = p.daxian ? `${p.daxian[0]}–${p.daxian[1]}` : ''
    return `<div class="${cls.join(' ')}" style="grid-row:${row};grid-column:${col}"
                 data-zhi="${p.zhi}" data-name="${p.name}" data-mains="${mains.map((s) => s.name).join(',')}">
      <div class="head"><span class="gname">${p.name}</span><span class="gz">${p.gan}${p.zhi}</span></div>
      <div class="mains">${mainHTML}</div>
      <div class="minors">${minorHTML}</div>
      <div class="foot"><span>${p.changsheng || ''} ${p.boshi || ''}</span><span class="daxian">${dx}</span></div>
    </div>`
  }).join('')

  const center = `<div class="center">
    <div class="big">${zw.ju_name} · 命宫${zw.ming}</div>
    <div class="kv">
      <span>命主</span><b>${zw.ming_zhu}</b>
      <span>身主</span><b>${zw.shen_zhu}</b>
      <span>身宫</span><b>${zw.shen}</b>
      <span>行运</span><b>${zw.forward ? '顺行' : '逆行'}</b>
    </div>
  </div>`

  board.innerHTML = cells + center
  document.body.dataset.ziwei = `${zw.ming}|${zw.shen}|${zw.ju_name}|${zw.palaces.length}`

  // 点一宫 → 看《紫微斗数全书》对这一宫主星的论断
  board.querySelectorAll('.palace').forEach((cell) => {
    const p = zw.palaces.find((x) => x.zhi === cell.dataset.zhi)
    const mains = (p?.stars || []).filter((s) => s.kind === 'main').map((s) => s.name)
    cell.addEventListener('click', async () => {
      await showSource(p?.name || cell.dataset.name, mains)
    })
  })
}

const srcBox = document.getElementById('src')
srcBox.querySelector('.close').addEventListener('click', () => srcBox.classList.remove('on'))

async function showSource(palace, stars) {
  const body = srcBox.querySelector('.body')
  srcBox.querySelector('h3').textContent = `${palace} · ${stars.join('、') || '—'}`
  body.textContent = '查原文…'
  srcBox.classList.add('on')
  const q = `?palace=${encodeURIComponent(palace)}&stars=${encodeURIComponent(stars.join(','))}`
  const d = await (await fetch(`/api/ziwei/passage${q}`)).json()
  if (!d.found) { body.textContent = d.reason || '查不到'; return }
  srcBox.querySelector('h3').textContent = `${d.palace}${d.palace_alias ? '（今作' + d.palace_alias + '）' : ''} · ${d.star}`
  body.textContent = ''
  const main = document.createElement('div')
  main.textContent = d.text
  body.appendChild(main)
  for (const [label, text] of [['十二支宫', (d.branches || []).join('\n')], ['男命', d.male], ['女命', d.female], ['入限', d.xian]]) {
    if (!text) continue
    const sec = document.createElement('div')
    sec.className = 'sec'
    const b = document.createElement('b')
    b.textContent = label
    const t = document.createElement('div')
    t.textContent = text
    sec.append(b, t)
    body.appendChild(sec)
  }
  const src = document.createElement('div')
  src.className = 'sec'
  const sb = document.createElement('b')
  sb.textContent = '出处'
  const st = document.createElement('div')
  st.textContent = `${d.edition} · 卷二 十二宫逐星论断`
  src.append(sb, st)
  body.appendChild(src)
}

async function load(birth, gender) {
  const q = `?birth=${encodeURIComponent(birth || '1996-04-18 13:46')}&gender=${gender || 0}`
  render(await (await fetch(`/api/ziwei${q}`)).json())
  const u = new URL(location.href)
  u.searchParams.set('birth', (birth || '1996-04-18 13:46').trim())
  u.searchParams.set('gender', String(gender || 0))
  history.replaceState(null, '', u)
}

const birthInput = document.getElementById('birth')
const sexInput = document.getElementById('sex')
document.getElementById('go').addEventListener('click', () => load(birthInput.value.trim(), sexInput.value))
birthInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') load(birthInput.value.trim(), sexInput.value) })

const flowBox = document.getElementById('flow')
const ryear = document.getElementById('ryear')
ryear.value = String(new Date(Date.now() + 8 * 3600e3).getFullYear())

async function showYear() {
  const y = (ryear.value || '').trim() || String(new Date().getFullYear())
  const q = `?birth=${encodeURIComponent(birthInput.value.trim())}&gender=${sexInput.value}&year=${y}`
  const d = await (await fetch(`/api/ziwei/year${q}`)).json()

  board.querySelectorAll('.palace').forEach((c) => c.classList.remove('daxian', 'liunian'))
  for (const [kind, v] of [['daxian', d.daxian], ['liunian', d.liunian]]) {
    if (!v) continue
    const cell = board.querySelector(`.palace[data-zhi="${v.zhi}"]`)
    if (cell) cell.classList.add(kind)
  }

  const hua = (d.sihua || []).map((s) => `${s.star}化<em>${s.hua}</em>→${s.palace}`).join('　')
  flowBox.innerHTML = `
    <button class="close" type="button" title="收起">✕</button>
    <div class="row">
      <span>流年 <b>${d.year_gz}</b>（${d.year}）</span>
      <span>虚岁 <b>${d.age}</b></span>
      <span>大限 <b>${d.daxian ? d.daxian.name + '宫 ' + d.daxian.range[0] + '–' + d.daxian.range[1] : '未起运'}</b></span>
      <span>流年宫 <b>${d.liunian ? d.liunian.name : '—'}</b></span>
      <span>小限 <b>${d.xiaoxian ? d.xiaoxian.name : '—'}</b></span>
      <span>命宫 <b>${d.ming.name}（${d.ming.zhi}）</b></span>
    </div>
    <div class="hua">流年四化：${hua}</div>`
  flowBox.classList.add('on')
  flowBox.querySelector('.close').addEventListener('click', () => {
    flowBox.classList.remove('on')
    board.querySelectorAll('.palace').forEach((c) => c.classList.remove('daxian', 'liunian'))
  })
  document.body.dataset.flow = `${d.year_gz}|${d.daxian ? d.daxian.zhi : ''}|${d.liunian ? d.liunian.zhi : ''}`
  syncUrl({ year: d.year })
}

function syncUrl(params) {
  const u = new URL(location.href)
  for (const [k, v] of Object.entries(params)) {
    if (v) u.searchParams.set(k, v)
    else u.searchParams.delete(k)
  }
  history.replaceState(null, '', u)
}

document.getElementById('rgo').addEventListener('click', showYear)
ryear.addEventListener('keydown', (e) => { if (e.key === 'Enter') showYear() })

// 链接里带 birth / gender / year：同一张盘可以直接发给别人
const qs = new URLSearchParams(location.search)
if (qs.get('birth')) birthInput.value = qs.get('birth')
if (qs.get('gender')) sexInput.value = qs.get('gender')
if (qs.get('year')) ryear.value = qs.get('year')

load(birthInput.value, sexInput.value).then(() => {
  if (qs.get('year')) showYear()
})
