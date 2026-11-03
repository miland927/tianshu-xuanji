// Screenshot the page through CDP so the animation runs in real time (no virtual
// time), which is what the ticker and the ring easing need.
// usage: node vendor/capture.mjs <url> <out.png> [waitMs]
import { writeFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
const out = process.argv[3] ?? 'shot.png'
const waitMs = Number(process.argv[4] ?? 6000)
const port = 9333

const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-cdp-'))

const browser = spawn(edge, [
  '--headless=new',
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`,
  '--no-first-run',
  '--disable-extensions',
  '--hide-scrollbars',
  '--window-size=1600,900',
  '--enable-unsafe-swiftshader',
  '--use-angle=swiftshader',
  'about:blank',
], { stdio: 'ignore' })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function version() {
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`)
      if (res.ok) return await res.json()
    } catch { }
    await sleep(250)
  }
  throw new Error('CDP endpoint never came up')
}

const send = (ws, id, method, params = {}) =>
  new Promise((resolve, reject) => {
    const onMessage = (ev) => {
      const msg = JSON.parse(ev.data)
      if (msg.id !== id) return
      ws.removeEventListener('message', onMessage)
      msg.error ? reject(new Error(method + ': ' + msg.error.message)) : resolve(msg.result)
    }
    ws.addEventListener('message', onMessage)
    ws.send(JSON.stringify({ id, method, params }))
  })

try {
  await version()
  const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
  const ws = new WebSocket(tab.webSocketDebuggerUrl)
  await new Promise((r, j) => { ws.addEventListener('open', r); ws.addEventListener('error', j) })

  let id = 0
  await send(ws, ++id, 'Page.enable')
  await send(ws, ++id, 'Runtime.enable')
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url })
  await sleep(waitMs)

  const probe = await send(ws, ++id, 'Runtime.evaluate', {
    expression: `JSON.stringify({
      canvases: document.querySelectorAll('canvas').length,
      codeChars: (document.getElementById('code')?.textContent ?? '').trim().length,
      webgl: !!document.querySelector('canvas')?.getContext('webgl2')
    })`,
    returnByValue: true,
  })
  console.log('probe', probe.result.value)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync(out, Buffer.from(shot.data, 'base64'))
  console.log('saved', out)
  ws.close()
} finally {
  browser.kill()
}
