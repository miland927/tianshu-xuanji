// 奇门原文验收：点一条成格 → 看《遁甲演义》那节出来没有。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9352
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-qmsrc-'))
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
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/qimen.html' })
  await sleep(2200)

  const before = await evalJs(`JSON.stringify({
    items: document.querySelectorAll('#geju li[data-cite]').length,
    first: document.querySelector('#geju .name')?.textContent || null,
    src: document.querySelectorAll('#geju .src').length
  })`)
  console.log('成格列表：', before)

  const clicked = await evalJs(`(() => {
    const li = document.querySelector('#geju li[data-cite]'); if (!li) return 'no-item';
    li.click(); return 'clicked:' + li.querySelector('.name').textContent;
  })()`)
  await sleep(1300)

  const after = await evalJs(`JSON.stringify({
    clicked: ${JSON.stringify(clicked)},
    src: document.querySelectorAll('#geju .src').length,
    text: document.querySelector('#geju .src')?.textContent.replace(/\\s+/g,' ').trim().slice(0, 110) || null
  })`)
  console.log('点开后：', after)

  await evalJs(`document.querySelector('#geju .src')?.scrollIntoView({block:'center'})`)
  await sleep(400)
  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('qimen-src-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved qimen-src-shot.png')
  ws.close()
} finally {
  browser.kill()
}
