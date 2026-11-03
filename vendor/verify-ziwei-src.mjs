// 紫微原文验收：点一宫 → 看《全书》那段论断出来没有。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9351
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-zwsrc-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1400,1050',
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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1400, height: 1050, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/ziwei.html' })
  await sleep(2000)

  const clicked = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.palace')];
    const ming = cells.find(c => c.classList.contains('ming'));
    if (!ming) return 'no-ming';
    ming.click();
    return 'clicked:' + ming.dataset.name;
  })()`)
  await sleep(1500)

  const got = await evalJs(`JSON.stringify({
    clicked: ${JSON.stringify(clicked)},
    open: document.querySelector('#src')?.classList.contains('on'),
    title: document.querySelector('#src h3')?.textContent || null,
    body: document.querySelector('#src .body')?.textContent.replace(/\\s+/g,' ').trim().slice(0, 90) || null,
    secs: [...document.querySelectorAll('#src .sec b')].map(b => b.textContent)
  })`)
  console.log('点开后：', got)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('ziwei-src-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved ziwei-src-shot.png')
  ws.close()
} finally {
  browser.kill()
}
