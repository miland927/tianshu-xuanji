// P3 验收：换一派——同一张盘，四组口径重算，差异逐条摆出来。
// usage: node vendor/verify-compare.mjs [url]
import { writeFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
const port = 9338
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-compare-'))

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
  await sleep(4500)

  await evalJs(`
    document.querySelector('#xji-trigger').click();
    document.querySelector('#xji-b-date').value = '1996-04-18 15:05';
    document.querySelector('#xji-b-lon').value = '114.93';
    document.querySelector('#xji-input').value = '这个盘旺衰怎么样？';
    document.querySelector('#xji-form').requestSubmit();
    'sent'
  `)
  await sleep(2000)

  await evalJs(`(() => {
    const b = [...document.querySelectorAll('#xji-log .ev-btn')].find((x) => x.textContent === '换一派');
    if (!b) return 'no-btn';
    b.click();
    return 'clicked';
  })()`)
  await sleep(1800)

  const probe = await evalJs(`JSON.stringify({
    fields: [...document.querySelectorAll('#xji-log .alt-field')].map(e => e.textContent),
    rows: [...document.querySelectorAll('#xji-log .alt-row')].map(e => e.textContent),
    note: document.querySelector('#xji-log .alt-note')?.textContent || null
  })`)
  console.log('probe', probe)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('compare-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved compare-shot.png')
  ws.close()
} finally {
  browser.kill()
}
