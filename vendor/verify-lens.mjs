// 镜头切换验收：连切 12 次，看画布是否只有一个、上下文有没有丢。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9348
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-lens-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1400,1000',
  '--enable-unsafe-swiftshader', '--use-angle=swiftshader', 'about:blank',
], { stdio: 'ignore' })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const send = (ws, id, method, params = {}) => new Promise((resolve, reject) => {
  const on = (ev) => {
    const m = JSON.parse(ev.data)
    if (m.id !== id) return
    ws.removeEventListener('message', on)
    m.error ? reject(new Error(m.error.message)) : resolve(m.result)
  }
  ws.addEventListener('message', on)
  ws.send(JSON.stringify({ id, method, params }))
})

let id = 0
try {
  for (let i = 0; i < 80; i++) {
    try { if ((await fetch(`http://127.0.0.1:${port}/json/version`)).ok) break } catch { }
    await sleep(250)
  }
  const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
  const ws = new WebSocket(tab.webSocketDebuggerUrl)
  await new Promise((r, j) => { ws.addEventListener('open', r); ws.addEventListener('error', j) })
  const evalJs = async (e) => (await send(ws, ++id, 'Runtime.evaluate',
    { expression: e, awaitPromise: true, returnByValue: true })).result?.value

  await send(ws, ++id, 'Page.enable')
  await send(ws, ++id, 'Runtime.enable')
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/plate.html' })
  await sleep(3200)

  const order = ['liuren', 'ziwei', 'qimen', 'zhoutian']
  const log = []
  for (let i = 0; i < 12; i++) {
    const t = order[i % order.length]
    await evalJs(`window.__mount(${JSON.stringify(t)})`)
    await sleep(700)
    const st = await evalJs(`JSON.stringify({
      plate: document.body.dataset.plate,
      canvases: document.querySelectorAll('#wheel canvas').length,
      lost: (() => { const c = document.querySelector('#wheel canvas'); if (!c) return 'no-canvas';
                     const gl = c.getContext('webgl2') || c.getContext('webgl'); return gl ? gl.isContextLost() : 'no-gl' })()
    })`)
    log.push(st)
  }

  const last = JSON.parse(log[log.length - 1])
  const multi = log.filter((s) => JSON.parse(s).canvases !== 1)
  console.log('切换 12 次，画布数不为 1 的次数：', multi.length)
  console.log('末态：', JSON.stringify(last))
  const stats = await evalJs(`JSON.stringify(window.__switchStats || null)`)
  console.log('统计：', stats)

  await evalJs(`window.__mount('ziwei')`)
  await sleep(2000)
  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('lens-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved lens-shot.png')
  ws.close()
} finally {
  browser.kill()
}
