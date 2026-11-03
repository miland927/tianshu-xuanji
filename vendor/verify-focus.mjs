// P3 验收：问一句「现在什么节气」，看铜环有没有真的转到那一格。
// usage: node vendor/verify-focus.mjs [url]
import { writeFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
const port = 9336
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-focus-'))

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
  await sleep(5000)

  const ok = await evalJs(`(() => {
    if (!window.__wheel || typeof window.__wheel.indexOf !== 'function') return 'no-indexOf'
    document.querySelector('#xji-trigger').click()
    return 'ok'
  })()`)
  console.log('wheel api:', ok)

  await evalJs(`
    document.querySelector('#xji-input').value = '现在是什么节气？';
    document.querySelector('#xji-form').requestSubmit();
    'sent'
  `)
  await sleep(2200)

  const probe = await evalJs(`JSON.stringify({
    focus: document.body.dataset.focus || null,
    idxCheck: window.__wheel.indexOf('二十四节气', '寒露'),
    chip: [...document.querySelectorAll('#xji-meta i')].map(e => e.textContent)
  })`)
  console.log('probe', probe)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('focus-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved focus-shot.png')
  ws.close()
} finally {
  browser.kill()
}
