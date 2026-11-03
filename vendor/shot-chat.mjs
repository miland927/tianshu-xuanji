// 打开璇玑面板、问一句、截两张图。只依赖 Edge 的 CDP，不装 playwright。
// usage: node vendor/shot-chat.mjs <url> <outPrefix>
import { writeFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
const prefix = process.argv[3] ?? 'shot'
const port = 9334
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-chat-'))

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

async function connect() {
  for (let i = 0; i < 80; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`)
      if (r.ok) return
    } catch { }
    await sleep(250)
  }
  throw new Error('CDP never came up')
}

let id = 0
try {
  await connect()
  const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
  const ws = new WebSocket(tab.webSocketDebuggerUrl)
  await new Promise((r, j) => { ws.addEventListener('open', r); ws.addEventListener('error', j) })

  const evalJs = async (expression) => {
    const r = await send(ws, ++id, 'Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    return r.result?.value
  }
  const shot = async (file) => {
    const s = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
    writeFileSync(file, Buffer.from(s.data, 'base64'))
    console.log('saved', file)
  }

  await send(ws, ++id, 'Page.enable')
  await send(ws, ++id, 'Runtime.enable')
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url })
  await sleep(5000)

  await evalJs(`document.querySelector('#xji-trigger').click()`)
  await sleep(1200)
  await evalJs(`document.querySelector('#xji-birth').open = true`)
  await sleep(800)
  await shot(`${prefix}-open.png`)

  await evalJs(`
    document.querySelector('#xji-b-date').value = '1996-04-18 14:06';
    document.querySelector('#xji-b-lon').value = '114.93';
    const i = document.querySelector('#xji-input');
    i.value = '我这个盘旺衰怎么样？凭什么？';
    document.querySelector('#xji-form').requestSubmit();
    'sent'
  `)
  await sleep(2600)
  await shot(`${prefix}-reply.png`)

  await evalJs(`(() => {
    const b = document.querySelector('#xji-log .ev-btn');
    if (!b) return 'no-evidence';
    b.click();
    const ev = document.querySelector('#xji-log .ev');
    ev.scrollIntoView({ block: 'start' });
    return 'opened';
  })()`)
  await sleep(700)
  await shot(`${prefix}-evidence.png`)

  const probe = await evalJs(`JSON.stringify({
    panel: !!document.querySelector('#xji'),
    open: document.body.classList.contains('xji-open'),
    read: document.querySelector('#xji-read').textContent.slice(0, 80),
    msgs: document.querySelectorAll('#xji-log .m').length,
    evLayers: document.querySelectorAll('#xji-log .ev-layer').length,
    evItems: document.querySelectorAll('#xji-log .ev-item').length,
    errs: document.querySelectorAll('#xji-log .err').length
  })`)
  console.log('probe', probe)
  ws.close()
} finally {
  browser.kill()
}
