/* 一台仪器，三副镜头：周天 / 六壬 / 紫微。
   切换时把旧的 dispose() 掉再建新的；dispose 里会 forceContextLoss，避免 WebGL 上下文堆积。 */
import { createCelestialWheel } from './celestial-wheel.js'

const ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
const LENSES = { zhoutian: '周天 · 十二重', liuren: '六壬 · 天地盘', ziwei: '紫微 · 十二宫' }

const tip = document.getElementById('tip')
const host = document.getElementById('wheel')
const el = (id) => document.getElementById(id)
const setSide = (rows) => { el('rows').innerHTML = rows.map(([a, b]) => `<div class="row"><span>${a}</span><b>${b}</b></div>`).join('') }
const setHead = (title, sub) => { el('title').textContent = title; el('sub').textContent = sub }
const nowBJ = () => new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 16).replace('T', ' ')

let wheel = null
let current = null
const stats = { created: 0, disposed: 0 }

function onFocus({ cell }) {
  if (!cell) { tip.classList.remove('on'); return }
  tip.innerHTML = `<b>${cell.label}</b><br>${cell.ring} · 第 ${cell.index + 1} 格`
  tip.classList.add('on')
}

function teardown() {
  if (wheel) { wheel.dispose(); wheel = null; stats.disposed += 1 }
  host.innerHTML = ''
}

async function specFor(type) {
  if (type === 'liuren') {
    const k = await (await fetch(`/api/liuren?at=${encodeURIComponent(nowBJ())}`)).json()
    const h = k.tian_di_pan
    setHead('LIUREN', '大 六 壬 · 天 地 盘')
    setSide([
      ['四柱', Object.values(k.ganzhi || {}).join(' ')],
      ['月将 · 占时', `${k.yue_jiang} · ${k.zhan_shi}`],
      ['三传', ['chu', 'zhong', 'mo'].map((x) => k.three_chuan[x].zhi).join(' ')],
      ['取传', `${k.three_chuan.method}${k.three_chuan.ge ? '·' + k.three_chuan.ge : ''}`],
    ])
    return {
      plate: [
        { key: '天盘', r: 2.42, w: 0.52, speed: 0.012, kind: 't1', items: ZHI.map((z) => ({ label: h[z] })) },
        { key: '地盘', r: 1.82, w: 0.46, speed: -0.008, kind: 't2', items: ZHI.map((z) => ({ label: z })) },
      ],
      key: `liuren|${k.three_chuan?.chu?.zhi || ''}`,
    }
  }

  if (type === 'ziwei') {
    const z = await (await fetch('/api/ziwei?birth=1996-04-18%2013:46&gender=0')).json()
    const byZhi = Object.fromEntries(z.palaces.map((p) => [p.zhi, p]))
    const items = ZHI.map((zhi) => {
      const p = byZhi[zhi] || { stars: [], name: '—' }
      const mains = (p.stars || []).filter((s) => s.kind === 'main')
      const minors = (p.stars || []).filter((s) => s.kind !== 'main')
      const line1 = mains.length ? mains.map((s) => s.name + (s.hua ? '化' + s.hua : '')).join(' ') : '（无主星）'
      const line2 = mains.map((s) => s.miao || '').filter(Boolean).join(' ')
      return {
        label: p.name,
        lines: [line1, line2,
                minors.slice(0, 3).map((s) => s.name).join(' '),
                minors.slice(3, 6).map((s) => s.name).join(' ')].filter(Boolean),
      }
    })
    setHead('ZIWEI', '紫 微 斗 数 · 十 二 宫')
    setSide([
      ['命宫 · 身宫', `${z.ming} · ${z.shen}`],
      ['五行局', z.ju_name],
      ['命主 · 身主', `${z.ming_zhu} · ${z.shen_zhu}`],
      ['行运', z.forward ? '顺行' : '逆行'],
    ])
    return {
      plate: [
        { key: '十二宫', r: 2.30, w: 1.30, speed: 0.008, kind: 'list', items },
        { key: '地支', r: 1.00, w: 0.34, speed: -0.012, kind: 't2', items: ZHI.map((z) => ({ label: z })) },
      ],
      key: `ziwei|${z.ming}`,
    }
  }

  // 奇门：九宫进不了环形，取八宫排成一圈（坎1在北，顺时针），中宫记在侧栏
  if (type === 'qimen') {
    const r = await (await fetch(`/api/qimen?at=${encodeURIComponent(nowBJ())}`)).json()
    const pal = r.pan.palaces || {}
    const ORDER = [[1, '坎'], [8, '艮'], [3, '震'], [4, '巽'], [9, '离'], [2, '坤'], [7, '兑'], [6, '乾']]
    const items = ORDER.map(([g, name]) => {
      const p = pal[String(g)] || {}
      return {
        label: `${name}${g}`,
        lines: [
          `${(p.tian || []).join('') || '—'} ${p.star || ''}`.trim(),
          `${p.door || '—'}门`,
          p.shen || '',
        ].filter(Boolean),
      }
    })
    const center = pal['5'] || {}
    setHead('QIMEN', '奇 门 遁 甲 · 八 宫')
    setSide([
      ['四柱', Object.values(r.sizhu || {}).join(' ')],
      ['局', `${r.ju.dun}遁 ${r.ju.ju} 局 · ${r.ju.jieqi}${r.ju.yuan}元`],
      ['直符 · 直使', `${r.pan.zhifu}@${r.pan.zhifu_gong} · ${r.pan.zhishi}@${r.pan.zhishi_gong}`],
      ['中宫地盘', (center.di || []).join('') || '—'],
      ['旬空 · 马星', `${r.kong?.zhi || ''} · ${r.ma?.zhi || ''}`],
    ])
    return {
      plate: [{ key: '八宫', r: 2.20, w: 1.36, speed: 0.006, kind: 'list', items }],
      key: `qimen|${r.ju.ju}|${r.pan.zhifu_gong}`,
    }
  }

  // 周天：不传 plate，用 data.js 的十二重；再把四只环对准此刻
  const n = await (await fetch('/api/now')).json()
  const [, , day, hour] = n.bazi.split(' ')
  setHead('CELESTIAL WHEEL', '周 天 · 十 二 重')
  setSide([
    ['节气 · 候', `${n.term.name} · ${n.bazi.split(' ')[3]}`],
    ['月建 · 日柱', `${n.month_zhi} · ${day}`],
    ['恒星时 · 宿', `${n.sidereal.lst_hms} · ${n.sidereal.xiu.name}`],
    ['月相', `${n.moon.name} ${Math.round(n.moon.illum * 100)}%`],
  ])
  return {
    plate: null,
    align: [['二十四节气', n.term.name], ['六十甲子', day], ['十二地支', hour[1]],
            ['二十八宿', n.sidereal.xiu.name]],
    key: 'zhoutian',
  }
}

async function mount(type) {
  if (type === current) return
  teardown()
  current = type
  const spec = await specFor(type)
  wheel = createCelestialWheel(host, { plate: spec.plate, onFocus })
  wheel.setMode('landing')
  stats.created += 1
  if (spec.align) {
    for (const [ring, label] of spec.align) {
      const i = wheel.indexOf(ring, label)
      if (i >= 0) wheel.setAngle(ring, i)
    }
  }
  document.body.dataset.plate = spec.key
  window.__wheel = wheel
  window.__plate = spec
  window.__switchStats = stats
  document.querySelectorAll('#lenses button').forEach((b) => b.classList.toggle('here', b.dataset.type === type))
}

document.querySelectorAll('#lenses button').forEach((b) => {
  b.addEventListener('click', () => mount(b.dataset.type))
})

window.__mount = mount
const start = new URLSearchParams(location.search).get('type') || 'zhoutian'
mount(start)
