// 说明页验收：链接是否都 200，页面是否真渲染出来。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const BASE = 'http://127.0.0.1:8788'
const port = 9355
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-guide-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1200,1400',
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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1100, height: 1500, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: `${BASE}/guide.html` })
  await sleep(900)

  const info = JSON.parse(await evalJs(`JSON.stringify({
    cards: document.querySelectorAll('.card').length,
    steps: document.querySelectorAll('.steps li').length,
    rows: document.querySelectorAll('table tr').length - 1,
    nos: document.querySelectorAll('.no div').length,
    links: [...document.querySelectorAll('a')].map(a => a.getAttribute('href')).filter(h => h && h.startsWith('/'))
  })`))
  console.log('页面结构：', JSON.stringify({ cards: info.cards, steps: info.steps, rows: info.rows, nos: info.nos }))

  // 站内链接逐个请求，必须都是 200
  const bad = []
  for (const href of [...new Set(info.links)]) {
    const r = await fetch(BASE + href, { method: 'GET' })
    if (r.status !== 200) bad.push(`${href} → ${r.status}`)
  }
  console.log('站内链接：', info.links.length, '个引用 /', [...new Set(info.links)].length, '个不同目标；失败', bad.length)
  for (const b of bad) console.log('  ', b)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
  writeFileSync('guide-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved guide-shot.png')
  ws.close()
} finally {
  browser.kill()
}
