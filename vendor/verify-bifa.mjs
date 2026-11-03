// 六壬毕法原文验收：打开页面 → 点一条毕法 → 看注出来没有。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9350
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-bifa-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1400,1100',
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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1400, height: 1100, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/liuren.html' })
  await sleep(2200)

  const before = await evalJs(`JSON.stringify({
    items: document.querySelectorAll('#bifa li.item').length,
    first: document.querySelector('#bifa li.item em')?.textContent || null,
    src: document.querySelectorAll('#bifa .src').length
  })`)
  console.log('毕法列表：', before)

  const clicked = await evalJs(`(() => {
    const li = document.querySelector('#bifa li.item'); if (!li) return 'no-item';
    li.click(); return 'clicked:' + li.dataset.no;
  })()`)
  await sleep(1200)

  const after = await evalJs(`JSON.stringify({
    clicked: ${JSON.stringify(clicked)},
    src: document.querySelectorAll('#bifa .src').length,
    text: document.querySelector('#bifa .src')?.textContent.replace(/\\s+/g,' ').trim().slice(0, 100) || null
  })`)
  console.log('点开后：', after)

  await evalJs(`document.querySelector('#bifa .src')?.scrollIntoView({block:'center'})`)
  await sleep(500)
  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('bifa-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved bifa-shot.png')
  ws.close()
} finally {
  browser.kill()
}
