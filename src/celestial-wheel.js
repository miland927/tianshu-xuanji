// 周天：十二重同心环，每一重按典籍生成字格，在平面与立体之间往复。
// 全程序化绘制，没有一张图片。
import * as THREE from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { RINGS_DEF, detail } from './data.js'

const FONT = '"Zhuque Fangsong","Songti SC","STSong","Noto Serif SC",serif'
const WHITE = 0xffffff, GOLD = 0xffd9a0

function drawLines(ctx, x, y, w, lines, gap) { const h = gap * .42; lines.forEach((yang, i) => { const yy = y + (lines.length - 1 - i) * gap; if (yang) ctx.fillRect(x, yy, w, h); else { ctx.fillRect(x, yy, w * .42, h); ctx.fillRect(x + w * .58, yy, w * .42, h) } }) }
const D = {
  tri: (c, it, s) => drawLines(c, s * .2, s * .2, s * .6, it.lines, s * .2),
  hex: (c, it, s) => drawLines(c, s * .2, s * .1, s * .6, it.lines, s * .135),
  t1: (c, it, s) => { c.font = `500 ${s * .7}px ${FONT}`; c.fillText(it.label, s / 2, s / 2) },
  t2: (c, it, s) => { c.font = `500 ${s * .42}px ${FONT}`; c.fillText(it.label, s / 2, s / 2) },
  t4: (c, it, s) => { c.font = `500 ${s * .24}px ${FONT}`; c.fillText(it.label, s / 2, s / 2) },
  // 一格多行：宫名在上，下面最多三行星曜。给紫微那种「十二宫各带一串星」的盘用。
  list: (c, it, s) => {
    c.font = `500 ${s * .17}px ${FONT}`
    c.fillStyle = '#f2ede0'
    c.fillText(it.label, s / 2, s * .2)
    const rows = (it.lines || []).slice(0, 4)
    c.font = `500 ${s * .105}px ${FONT}`
    c.fillStyle = '#d8d2c4'
    rows.forEach((t, i) => c.fillText(t, s / 2, s * .40 + i * s * .145))
  },
}
function atlas(items, cell, draw) {
  const cols = Math.ceil(Math.sqrt(items.length)), rows = Math.ceil(items.length / cols)
  const cv = document.createElement('canvas'); cv.width = cols * cell; cv.height = rows * cell
  const ctx = cv.getContext('2d'); ctx.fillStyle = '#f2ede0'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  items.forEach((it, i) => { ctx.save(); ctx.translate((i % cols) * cell, Math.floor(i / cols) * cell); draw(ctx, it, cell); ctx.restore() })
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8; tex.minFilter = THREE.LinearMipmapLinearFilter
  return { tex, cols, rows }
}
const ease = (x) => { x = Math.min(1, Math.max(0, x)); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2 }
const wrap = (x) => Math.atan2(Math.sin(x), Math.cos(x))
// 一帧最长按 50ms 算：切走标签页再回来，不会一步跳过一大截
const MAX_DT = .05

export function createCelestialWheel(host, { onFocus, plate } = {}) {
  const canvas = document.createElement('canvas'); host.appendChild(canvas)
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setSize(host.clientWidth, host.clientHeight)
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x050505)
  const camera = new THREE.PerspectiveCamera(36, host.clientWidth / host.clientHeight, .1, 100)
  const world = new THREE.Group(); scene.add(world)
  const pickables = [], geo = new THREE.PlaneGeometry(1, 1)
  const lineMat = new THREE.LineBasicMaterial({ color: WHITE, transparent: true, opacity: .22 })
  const circle = (r, y = 0, seg = 256, mat = lineMat) => { const pts = []; for (let k = 0; k <= seg; k++) { const a = (k / seg) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r)) } return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat) }
  const RINGS = (plate || RINGS_DEF).map((r) => ({ ...r }))
  const byKey = Object.fromEntries(RINGS.map((r) => [r.key, r]))
  RINGS.forEach((R) => {
    const g = new THREE.Group(); world.add(g); R.group = g; R.angle = Math.random() * 6.28; R.cur = R.speed; R.aim = null
    const cell = R.kind === 'list' ? 176 : 96; const { tex, cols, rows } = atlas(R.items, cell, D[R.kind])
    const n = R.items.length, circ = 2 * Math.PI * R.r, tang = Math.min(R.w, circ / n * .92)
    R.cells = []
    R.items.forEach((it, i) => {
      const m = new THREE.MeshBasicMaterial({ map: tex.clone(), transparent: true, depthWrite: false, side: THREE.DoubleSide, opacity: .9 })
      m.map.needsUpdate = true; m.map.repeat.set(1 / cols, 1 / rows); m.map.offset.set((i % cols) / cols, 1 - (Math.floor(i / cols) + 1) / rows)
      const mesh = new THREE.Mesh(geo, m); const a = (i / n) * Math.PI * 2
      mesh.position.set(Math.cos(a) * R.r, 0, Math.sin(a) * R.r); mesh.scale.set(tang, R.w, 1)
      mesh.userData = { ring: R, item: it, index: i, a }
      g.add(mesh); pickables.push(mesh); R.cells.push(mesh)
    })
    R.lines = [circle(R.r - R.w * .6)]; if (R.tick) R.lines.push(circle(R.r + R.w * .6))
    if (R.tick) {
      const pts = []; for (let k = 0; k < 360; k++) { const a = k / 180 * Math.PI; const r0 = R.r + R.w * .7, r1 = r0 + (k % 30 === 0 ? .22 : k % 10 === 0 ? .12 : .06); pts.push(new THREE.Vector3(Math.cos(a) * r0, 0, Math.sin(a) * r0), new THREE.Vector3(Math.cos(a) * r1, 0, Math.sin(a) * r1)) }
      R.lines.push(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: WHITE, transparent: true, opacity: .5 })), circle(R.r + R.w * .7 + .24))
    }
    R.lines.forEach((l) => { l.userData.base = l.material.opacity; g.add(l) })
    R.q = randomPose(.9); R.qT = randomPose(.9); R.lfoA = .12 + Math.random() * .18; R.lfoW = .15 + Math.random() * .25; R.lfoP = Math.random() * 6.28; R.yOff = 0; R.yOffT = 0; R.flipT0 = 0; R.boost = 0
  })
  function randomPose(strength = 1) { const e = new THREE.Euler((Math.random() - .5) * 2.6 * strength, Math.random() * Math.PI * 2, (Math.random() - .5) * 2.6 * strength, 'YXZ'); return new THREE.Quaternion().setFromEuler(e) }
  // 中心太极
  const taiji = (() => { const cv = document.createElement('canvas'); cv.width = cv.height = 256; const x = cv.getContext('2d'); const c = 128, r = 108
    x.fillStyle = '#f2ede0'; x.beginPath(); x.arc(c, c, r, -Math.PI / 2, Math.PI / 2); x.fill(); x.fillStyle = '#050505'; x.beginPath(); x.arc(c, c, r, Math.PI / 2, -Math.PI / 2); x.fill()
    x.fillStyle = '#f2ede0'; x.beginPath(); x.arc(c, c - r / 2, r / 2, 0, Math.PI * 2); x.fill(); x.fillStyle = '#050505'; x.beginPath(); x.arc(c, c + r / 2, r / 2, 0, Math.PI * 2); x.fill()
    x.fillStyle = '#050505'; x.beginPath(); x.arc(c, c - r / 2, r * .15, 0, Math.PI * 2); x.fill(); x.fillStyle = '#f2ede0'; x.beginPath(); x.arc(c, c + r / 2, r * .15, 0, Math.PI * 2); x.fill()
    x.strokeStyle = '#f2ede0'; x.lineWidth = 3; x.beginPath(); x.arc(c, c, r, 0, Math.PI * 2); x.stroke()
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace
    const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: t, transparent: true, side: THREE.DoubleSide, opacity: .85 })); m.rotation.x = -Math.PI / 2; m.scale.setScalar(.5); world.add(m); return m })()
  const orbits = []
  for (const [r, tx, tz] of [[5.6, .9, .2], [5.9, -.7, .5], [5.3, .3, -.9], [6.2, 1.2, .8]]) { const l = circle(r, 0, 360, new THREE.LineBasicMaterial({ color: WHITE, transparent: true, opacity: .14 })); l.userData = { tx, tz }; world.add(l); orbits.push(l) }

  const N = 2200, pos = new Float32Array(N * 3)
  for (let i = 0; i < N; i++) { const r = .8 + Math.random() * 6, a = Math.random() * Math.PI * 2, y = (Math.random() - .5) * 3; pos[i * 3] = Math.cos(a) * r; pos[i * 3 + 1] = y; pos[i * 3 + 2] = Math.sin(a) * r }
  const dust = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(pos, 3)), new THREE.PointsMaterial({ color: WHITE, size: .02, transparent: true, opacity: .5, depthWrite: false })); world.add(dust)
  const composer = new EffectComposer(renderer)
  composer.addPass(new RenderPass(scene, camera)); const bloom = new UnrealBloomPass(new THREE.Vector2(host.clientWidth, host.clientHeight), .38, .7, .8); composer.addPass(bloom); composer.addPass(new OutputPass())

  // ---------- 状态 ----------
  const state = { mode: 'landing', k: 0, kT: 0, paused: false, t0: performance.now() / 1000 }
  let px = 0, py = 0, tx = 0, ty = 0, hover = null, zoom = 1, zoomT = 1, nextEvent = 0, running = true, raf = 0, last = 0
  // 焦点可以是多格：第一格是主焦点（镜头与转环都对它）；每个被锁的环记住它自己的第一格
  let focusList = []
  const focusSet = new Set(), locked = new Map()
  let tempo = 1, tempoT = 1, view = null, bloomS = .38
  const camPos = new THREE.Vector3(), camLook = new THREE.Vector3()
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2()

  function eventTick(now) {
    if (now < nextEvent) return; nextEvent = now + 1.6 + Math.random() * 2.6
    const R = RINGS[Math.floor(Math.random() * RINGS.length)]; if (locked.has(R)) return
    const roll = Math.random()
    if (roll < .55) { R.qT = randomPose(1); R.flipT0 = now }
    else if (roll < .75) { R.speed = Math.sign(-R.speed) * Math.min(.12, Math.abs(R.speed) * (1 + Math.random())) }
    else if (roll < .9) { R.yOffT = (Math.random() - .5) * 2.2 }
    else { for (const X of RINGS) X.qT = randomPose(.35) }
  }
  function pick(cx, cy) { ndc.set((cx / host.clientWidth) * 2 - 1, -(cy / host.clientHeight) * 2 + 1); ray.setFromCamera(ndc, camera); return ray.intersectObjects(pickables, false)[0]?.object || null }
  function onMove(e) { tx = (e.clientX / innerWidth - .5) * 2; ty = (e.clientY / innerHeight - .5) * 2; if (state.mode !== 'landing') { hover = null; return } const h = pick(e.clientX, e.clientY); hover = h; host.style.cursor = h ? 'pointer' : 'default'; onFocus?.({ type: 'hover', cell: h ? cellInfo(h) : null, x: e.clientX, y: e.clientY }) }
  function onClick(e) {
    if (state.mode !== 'landing') return; if (e.target.closest && e.target.closest('button, input, select, textarea, a, form')) return
    if (hover) { setFocusMeshes([hover]); onFocus?.({ type: 'focus', cell: cellInfo(hover) }) } else if (focusList.length) leave()
  }
  function onKey(e) { if (e.code === 'Escape') leave(); if (e.code === 'Space' && state.mode === 'landing' && e.target === document.body) { state.paused = !state.paused; e.preventDefault() } }
  function onWheel(e) { if (state.mode !== 'landing' || focusList.length) return; zoomT = Math.min(1.8, Math.max(.6, zoomT + e.deltaY * .001)) }
  function cellInfo(m) { const { ring, item, index } = m.userData; return { label: item.label, ring: ring.key, index, total: ring.items.length, text: detail(ring, item, index) } }
  function setFocusMeshes(meshes) {
    focusList = [...new Set(meshes.filter(Boolean))]
    focusSet.clear(); locked.clear()
    for (const m of focusList) { focusSet.add(m); if (!locked.has(m.userData.ring)) locked.set(m.userData.ring, m) }
  }
  function leave() { setFocusMeshes([]); for (const R of RINGS) R.boost = 0; onFocus?.({ type: 'leave' }) }
  addEventListener('pointermove', onMove); addEventListener('click', onClick); addEventListener('keydown', onKey); addEventListener('wheel', onWheel, { passive: true })
  const ro = new ResizeObserver(() => { const w = host.clientWidth, h = host.clientHeight; if (!w || !h) return; camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h); composer.setSize(w, h) }); ro.observe(host)

  function frame() {
    if (!running) return
    raf = requestAnimationFrame(frame)
    const now = performance.now() / 1000; const t = now - state.t0
    // 真实帧间隔：60Hz 与 120Hz 屏上转速一样；切屏回来最多补 50ms
    const dt = last ? Math.min(MAX_DT, Math.max(0, now - last)) : 0; last = now
    // 逐帧追随系数原本按 60fps 调过手感；换算成与帧率无关的形式，60fps 下与原值完全相同
    const L = (a) => 1 - Math.pow(1 - a, dt * 60)
    const landing = state.mode === 'landing'
    const primary = focusList[0] || null
    // 变换进度
    if (landing) { if (!state.paused) { const cyc = t % 22; state.kT = cyc < 4 ? 0 : cyc < 10 ? ease((cyc - 4) / 6) : cyc < 16 ? 1 : 1 - ease((cyc - 16) / 6) }; if (primary) state.kT = 1 }
    else state.kT = .85 // calm：静置底景，环停在近乎立体的姿态
    const k = state.k += (state.kT - state.k) * L(.08)
    if (landing && !state.paused && k > .6 && !primary) eventTick(now)
    px += (tx - px) * L(.04); py += (ty - py) * L(.04); zoom += (zoomT - zoom) * L(.06)
    tempo += (tempoT - tempo) * L(.03)
    const breath = 1 + .03 * Math.sin(now * .6)
    // 世界姿态
    if (primary) world.rotation.y += wrap(0 - world.rotation.y) * L(.06); else world.rotation.y += dt * (.03 + (1 - k) * .05) * tempo
    const tiltOn = primary ? 0 : (landing ? 1 : .4)
    world.rotation.x = (py * .3) * k * tiltOn; world.rotation.z = (px * .25) * k * tiltOn
    world.scale.setScalar(breath)
    // 相机。只有观（landing）里聚焦才飞镜头；calm 里聚焦保持构图，让字格转到正前方即可。
    // rotateY(θ) 把布局角 a 的点送到 a-θ，要落在正对镜头的 π/2，就得 θ = a-π/2。
    // 写成 π/2-a 会送到 2a-π/2，正是以正前方为轴的镜像位置——只有 a=π/2 那一格碰巧正确。
    const fly = primary && landing
    if (fly) { const R = primary.userData.ring; const r = R.r * (1 + R.boost) * breath; camLook.set(0, 0, r - .2); camPos.set(0, 2.6, r + 3.1) }
    else if (landing) { const o = now * .07; camPos.set(Math.sin(o) * 9.8 * k * zoom, (14 * (1 - k) + (3.4 + Math.sin(now * .11) * 1.6) * k) * zoom, (.001 * (1 - k) + Math.cos(o) * 9.8 * k) * zoom); camLook.set(0, 0, 0) }
    else if (view) { const o = now * .05; camPos.set(view.pos[0] + Math.sin(o) * .6, view.pos[1], view.pos[2] + Math.cos(o) * .3); camLook.set(...view.look) }
    else { const o = now * .05; camPos.set(-4.8 + Math.sin(o) * 1.2, 4.2, 9.5 + Math.cos(o) * .6); camLook.set(-3.8, .2, 0) } // calm：盘偏右，左侧留白
    camera.position.lerp(camPos, L(fly ? .06 : landing ? .1 : .05)); camera.lookAt(camLook)
    // 各环
    const dimBase = landing ? 1 : .36
    const multi = focusList.length > 1
    // 「正前方」：观里镜头会飞到 +z（π/2）；calm 里镜头偏在左前方，就转向镜头真正所在的方位，
    // 否则主焦点会落在画面外。世界本身也在绕 Y 转，一并减掉。
    const front = landing ? Math.PI / 2 : Math.atan2(camera.position.z, camera.position.x)
    for (const R of RINGS) {
      const lockCell = locked.get(R) || null
      // 锁定格优先；其次是外部 turnTo 给的目标角；都没有就自转
      const a0 = lockCell ? lockCell.userData.a : R.aim
      const aim = a0 == null ? null : a0 - front - world.rotation.y
      R.cur += ((aim != null ? 0 : R.speed * tempo) - R.cur) * L(.04)
      if (aim != null) R.angle += wrap(aim - R.angle) * L(lockCell ? .12 : .07)
      else R.angle += dt * R.cur * 2
      R.q.slerp(R.qT, L(R.flipT0 && now - R.flipT0 < 2.5 ? .05 : .012))
      const q = R.q.clone(); q.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.sin(now * R.lfoW + R.lfoP) * R.lfoA, 0, Math.cos(now * R.lfoW * .8 + R.lfoP) * R.lfoA)))
      const flat = lockCell || (!landing && R.aim != null)
      const kk = flat ? 0 : (landing ? k : k * .35)
      R.group.quaternion.identity().slerp(q, kk); R.group.rotateY(R.angle)
      R.boost += ((lockCell ? .18 : 0) - R.boost) * L(.08); R.group.scale.setScalar(1 + R.boost)
      R.yOff += (R.yOffT - R.yOff) * L(.03); R.group.position.y = R.yOff * kk
      // 透明度：有焦点时只亮被锁的环；calm 里被 turnTo 指着的环也提亮，好让人看见它在转
      const dim = primary ? (lockCell ? (multi ? .42 : .95) : .05)
        : (!landing && R.aim != null) ? .8
        : (hover && hover.userData.ring !== R ? .7 : .9) * dimBase
      for (const c of R.cells) {
        const u = c.userData; const on = c === hover || focusSet.has(c)
        c.material.opacity += ((on ? 1 : dim) - c.material.opacity) * L(.12)
        c.material.color.setHex(on ? GOLD : WHITE)
        c.rotation.set(-Math.PI / 2 * (1 - kk), -u.a + Math.PI / 2, 0, 'YXZ')
      }
      const lineT = (primary && !lockCell) ? .03 : (!landing && R.aim != null) ? l0(R) : null
      for (const l of R.lines) l.material.opacity += ((lineT ?? l.userData.base * dimBase) - l.material.opacity) * L(.1)
    }
    orbits.forEach((o, i) => { o.rotation.set(o.userData.tx * k, now * .02 * (i % 2 ? 1 : -1), o.userData.tz * k); o.material.opacity = .14 * k * dimBase })
    taiji.rotation.z += dt * .2 * tempo; taiji.material.opacity = .85 * dimBase
    dust.material.opacity = (.15 + .35 * k) * dimBase; dust.rotation.y -= dt * .01 * tempo
    // 定：calm 里落下焦点时泛光轻提一点，像金字自己亮了
    bloomS += ((landing ? .38 : .23 + (primary ? .12 : 0)) - bloomS) * L(.05)
    bloom.strength = bloomS
    composer.render()
  }
  const l0 = (R) => R.lines[0].userData.base * .9
  frame()

  const cellAt = (ringKey, index) => byKey[ringKey]?.cells[index] || null

  return {
    // 'landing'：平面与立体之间往复；'calm'：静置底景
    setMode(mode) {
      const m = mode === 'calm' ? 'calm' : 'landing'
      if (m === state.mode) return
      state.mode = m; leave(); host.style.visibility = 'visible'
      if (m !== 'landing') { zoomT = 1; state.paused = false }
      else for (const R of RINGS) R.aim = null
    },
    get mode() { return state.mode },
    focusCell(ringKey, index) { const c = cellAt(ringKey, index); if (!c) return; setFocusMeshes([c]); onFocus?.({ type: 'focus', cell: cellInfo(c) }) },
    // 多格聚焦：[{ ring, index }, …]，第一格为主焦点。返回实际点亮的格数；传空数组等于 leave()。
    setFocus(list = []) {
      const meshes = list.map((f) => cellAt(f.ring, f.index)).filter(Boolean)
      if (!meshes.length) { leave(); return 0 }
      setFocusMeshes(meshes)
      onFocus?.({ type: 'focus', cell: cellInfo(focusList[0]), cells: focusList.map(cellInfo) })
      return focusList.length
    },
    get focused() { return focusList.map(cellInfo) },
    // 把某一格平滑转到正前方（不点亮、不锁环）；index 传 null 放手，环恢复自转
    turnTo(ringKey, index) {
      const R = byKey[ringKey]; if (!R) return false
      const c = index == null || index < 0 ? null : R.cells[index]
      R.aim = c ? c.userData.a : null   // 存布局角；转到哪由 frame 按镜头方位算
      return !!c
    },
    // 整体转速倍率：1 为原速，0 为停；过渡平滑
    setTempo(x) { tempoT = Math.min(4, Math.max(0, Number(x) || 0)) },
    // calm 下的机位：{ pos:[x,y,z], look:[x,y,z] }；传 null 回到默认（盘偏右、左侧留白）
    setView(v) { view = v && Array.isArray(v.pos) && Array.isArray(v.look) ? { pos: v.pos.slice(0, 3), look: v.look.slice(0, 3) } : null },
    pause(on) { state.paused = on == null ? !state.paused : !!on; return state.paused },
    // 按字找格：外部只知道「环 + 字」，索引由这里给，免得两处各排一遍
    indexOf(ringKey, label) { const R = byKey[ringKey]; if (!R) return -1; return R.items.findIndex((it) => it.label === label) },
    // 读数驱动初始角：把某一格转到正前方（at=π/2，与 focus 用的是同一个基准）。
    // rotateY(θ) 把布局角 a 送到 a-θ（见 frame 里那段注释），所以 θ = a - at。
    setAngle(ringKey, index, at = Math.PI / 2) {
      const R = byKey[ringKey]; if (!R) return null
      const cell = R.cells[index]; if (!cell) return null
      R.angle += wrap(cell.userData.a - at - R.angle)
      return R.angle
    },
    // 这一格现在偏了多少（0 = 正对镜头），自检用
    angleOf(ringKey, index) {
      const R = byKey[ringKey]; if (!R) return null
      const cell = R.cells[index]; if (!cell) return null
      return wrap(R.angle - (cell.userData.a - Math.PI / 2))
    },
    leave,
    dispose() { running = false; cancelAnimationFrame(raf); ro.disconnect(); removeEventListener('pointermove', onMove); removeEventListener('click', onClick); removeEventListener('keydown', onKey); removeEventListener('wheel', onWheel); renderer.forceContextLoss(); renderer.dispose(); host.innerHTML = '' },
  }
}
