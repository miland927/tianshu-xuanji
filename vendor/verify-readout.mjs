// 读数条验收：有没有读数、点它会不会转环、开面板时会不会让位。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
const port = 9341
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-readout-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1600,900',
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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride',
    { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url })
  await sleep(4000)

  console.log('bar:', await evalJs(`document.querySelector('#ro').textContent.slice(0, 120)`))
  console.log('data:', await evalJs(`document.body.dataset.readout || null`))

  await evalJs(`document.querySelector('#ro .seg[data-ring="六十甲子"]').click()`)
  await sleep(400)
  console.log('after click 日柱:', await evalJs(`document.body.dataset.focus || null`))

  const houClicked = await evalJs(`(() => {
    const el = document.querySelector('#ro .seg[data-ring="七十二候"]');
    if (!el) return 'no-hou';
    el.click();
    return el.textContent.trim();
  })()`)
  await sleep(400)
  console.log('hou segment:', houClicked, '→', await evalJs(`document.body.dataset.focus || null`))

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('readout-click.png', Buffer.from(shot.data, 'base64'))

  const glyph = await evalJs(`(() => {
    const c = document.querySelector('#ro .moonglyph');
    if (!c) return 'no-canvas';
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let lit = 0, disc = 0;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i + 3] > 0) { disc++; if (d[i] > 150) lit++; }
    }
    return JSON.stringify({ disc, lit, ratio: +(lit / disc).toFixed(3) });
  })()`)
  const illum = await evalJs(`window.__readout && window.__readout().moon ? window.__readout().moon.illum : null`)
  console.log('glyph:', glyph, 'illum:', illum)

  const rect = JSON.parse(await evalJs(`JSON.stringify(document.querySelector('#ro').getBoundingClientRect())`))
  const mrect = JSON.parse(await evalJs(`JSON.stringify(document.querySelector('#ro .moonglyph').parentElement.getBoundingClientRect())`))
  const crop = await send(ws, ++id, 'Page.captureScreenshot', {
    format: 'png',
    clip: { x: mrect.x - 24, y: rect.y, width: 300, height: rect.height, scale: 6 },
  })
  writeFileSync('readout-crop.png', Buffer.from(crop.data, 'base64'))
  console.log('saved readout-crop.png')

  await evalJs(`document.querySelector('#xji-trigger').click()`)
  await sleep(800)
  console.log('xji-open:', await evalJs(`document.body.classList.contains('xji-open')`),
              'opacity:', await evalJs(`getComputedStyle(document.querySelector('#ro')).opacity`))
  ws.close()
} finally {
  browser.kill()
}
