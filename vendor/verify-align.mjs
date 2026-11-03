// P3 验收：打开页面，三只环是否已经对准此刻的读数。
// usage: node vendor/verify-align.mjs [url]
import { writeFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
const port = 9337
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-align-'))

const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1600,900',
  '--enable-unsafe-swiftshader', '--use-angle=swiftshader', 'about:blank',
], { stdio: 'ignore' })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const send = (ws, id, method, params = {}) => new Promise((resolve, reject) => {
  const onMessage = (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.id !== id) return
    ws.removeEventListener('message', onMessage)
    msg.error ? reject(new Error(method + ': ' + msg.error.message)) : resolve(msg.result)
  }
  ws.addEventListener('message', onMessage)
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

  const evalJs = async (expression) => {
    const r = await send(ws, ++id, 'Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    return r.result?.value
  }

  await send(ws, ++id, 'Page.enable')
  await send(ws, ++id, 'Runtime.enable')
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url })
  await sleep(1000)
  const early = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('align-flat.png', Buffer.from(early.data, 'base64'))

  await sleep(2900)

  console.log('alignInfo:', await evalJs('JSON.stringify(window.__alignInfo || null)'))

  // 再对准一次再量，排除自转造成的漂移
  const probe = await evalJs(`(() => {
    const out = [];
    for (const it of (window.__alignInfo || [])) {
      if (it.error) continue;
      window.__wheel.setAngle(it.ring, it.index);
      out.push({ ring: it.ring, label: it.label, offset: +window.__wheel.angleOf(it.ring, it.index).toFixed(4) });
    }
    return JSON.stringify(out);
  })()`)
  console.log('offset after realign:', probe)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('align-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved align-shot.png')
  ws.close()
} finally {
  browser.kill()
}
