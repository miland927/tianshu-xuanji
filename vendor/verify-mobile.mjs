// 竖屏验收：390×844，看面板是不是贴底、不遮住铜环。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
const port = 9339
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-mobile-'))

const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=390,844',
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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride',
    { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })
  await send(ws, ++id, 'Page.navigate', { url })
  await sleep(4500)

  await evalJs(`
    document.querySelector('#xji-trigger').click();
    document.querySelector('#xji-input').value = '现在什么节气？';
    document.querySelector('#xji-form').requestSubmit();
    'sent'
  `)
  await sleep(2000)

  const probe = await evalJs(`(() => {
    const p = document.querySelector('#xji').getBoundingClientRect();
    return JSON.stringify({ w: Math.round(p.width), h: Math.round(p.height),
      left: Math.round(p.left), bottom: Math.round(innerHeight - p.bottom),
      vw: innerWidth, codeHidden: getComputedStyle(document.querySelector('#code')).display });
  })()`)
  console.log('probe', probe)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('mobile-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved mobile-shot.png')
  ws.close()
} finally {
  browser.kill()
}
