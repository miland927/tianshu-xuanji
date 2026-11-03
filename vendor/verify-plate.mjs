// 换镜头验收：?type=liuren 两圈、?type=ziwei 十二宫；顺带验聚焦后的读字效果。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const TYPE = process.argv[2] ?? 'liuren'
const FOCUS = process.argv[3] ?? ''
const port = 9347
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-plate2-'))
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
  await send(ws, ++id, 'Page.navigate', { url: `http://127.0.0.1:8788/plate.html?type=${TYPE}` })
  await sleep(3000)

  const probe = await evalJs(`(() => {
    try {
      const bands = (window.__plate && window.__plate.plate) ? window.__plate.plate.map(b => [b.key, b.items.length, b.kind]) : null;
      return JSON.stringify({
        plate: document.body.dataset.plate || null,
        bands,
        first: window.__plate && window.__plate.plate ? window.__plate.plate[0].items[0] : null,
        idx: (bands && window.__wheel) ? window.__wheel.indexOf(bands[0][0], window.__plate.plate[0].items[0].label) : null
      });
    } catch (e) { return JSON.stringify({ error: String(e) }) }
  })()`)
  console.log('probe:', probe)

  if (FOCUS) {
    const r = await evalJs(`(() => {
      const w = window.__wheel, b = window.__plate.plate[0];
      const i = w.indexOf(b.key, ${JSON.stringify(FOCUS)});
      if (i < 0) return 'not-found';
      w.focusCell(b.key, i);
      return 'focused:' + i;
    })()`)
    console.log('focus:', r)
    await sleep(2200)
  }

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync(`plate-${TYPE}${FOCUS ? '-focus' : ''}.png`, Buffer.from(shot.data, 'base64'))
  console.log('saved')
  ws.close()
} finally {
  browser.kill()
}
