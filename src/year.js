/* 年度报告：一年十二个月，按节气排。 */
const head = document.getElementById('head')
const tbl = document.getElementById('tbl')

const nowBJ = () => new Date(Date.now() + 8 * 3600e3)

function renderZiwei(z) {
  const box = document.getElementById('zw')
  if (!z || z.error) {
    box.innerHTML = `<div style="grid-column:1/-1;background:#070707"><div class="k">紫微</div>
      <div class="v" style="font-size:12px">${z && z.error ? '排不出来：' + z.error : '没有数据'}</div></div>`
    return
  }
  const cell = (k, v, s) => `<div><div class="k">${k}</div><div class="v">${v}${s ? `<small>${s}</small>` : ''}</div></div>`
  box.innerHTML = [
    cell('虚岁', z.age),
    cell('大限', z.daxian ? z.daxian.name + '宫' : '未起运', z.daxian ? `${z.daxian.range[0]}–${z.daxian.range[1]}` : ''),
    cell('流年宫', z.liunian ? z.liunian.name : '—'),
    cell('小限', z.xiaoxian ? z.xiaoxian.name : '—'),
    cell('命宫', z.ming.name, z.ming.zhi),
  ].join('') + `<div class="hua" style="grid-column:1/-1">流年四化：` +
    (z.sihua || []).map((s) => `${s.star}化<em>${s.hua}</em>→${s.palace}`).join('　') + '</div>'
}

function render(r) {
  const dy = r.dayun
  head.innerHTML = [
    ['流年', r.year_gz, r.year],
    ['大运', dy ? dy.pillar : '—', dy ? `${dy.start_year}–${dy.end_year}` : ''],
    ['日主', r.day_master, '月干十神以日主为准'],
    ['年评分', r.score.value, `${r.score.stance} · 50 为不偏`],
  ].map(([k, v, s]) => `<div><div class="k">${k}</div><div class="v">${v}${s ? `<small>${s}</small>` : ''}</div></div>`).join('')

  const today = nowBJ().toISOString().slice(0, 10)
  const cur = r.months.filter((m) => m.at.slice(0, 10) <= today).pop()
  tbl.innerHTML = `<tr><th>月建</th><th>流月</th><th>十神</th><th>交节</th><th>大运</th></tr>`
    + r.months.map((m) => `<tr class="${cur && m.index === cur.index ? 'now' : ''}" data-gz="${m.gz}" data-jie="${m.jie}">
        <td class="zhi">${m.zhi}月</td><td class="gz">${m.gz}</td><td>${m.ten_god}</td>
        <td>${m.jie} ${m.at.slice(5, 16)}</td><td>${m.dayun || '—'}</td></tr>`).join('')
  document.body.dataset.year = `${r.year_gz}|${r.months.length}|${cur ? cur.gz : ''}`
  renderZiwei(r.ziwei)
}

async function load(birth, gender, year) {
  const q = `?birth=${encodeURIComponent(birth)}&gender=${gender}&year=${year}`
  render(await (await fetch(`/api/year${q}`)).json())
}

const birth = document.getElementById('birth')
const sex = document.getElementById('sex')
const yearInput = document.getElementById('year')
yearInput.value = String(nowBJ().getFullYear())
document.getElementById('go').addEventListener('click', () => load(birth.value.trim(), sex.value, yearInput.value.trim()))
document.getElementById('pdf').addEventListener('click', () => {
  // 交给浏览器的打印对话（可存为 PDF）。不自己拼 PDF，省得排版两套。
  document.body.classList.add('printing')
  window.print()
  setTimeout(() => document.body.classList.remove('printing'), 400)
})
birth.addEventListener('keydown', (e) => { if (e.key === 'Enter') load(birth.value.trim(), sex.value, yearInput.value.trim()) })
load(birth.value, sex.value, yearInput.value)
