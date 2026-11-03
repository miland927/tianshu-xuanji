// 紫微流年验收：点「看流年」→ 大限宫/流年宫描边、条上数字与 API 一致。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9356
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-zlyear-'))
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
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/ziwei.html' })
  await sleep(2200)

  await evalJs(`(() => {
    document.querySelector('#ryear').value = '2026';
    document.querySelector('#rgo').click();
    return 'clicked';
  })()`)
  await sleep(1200)

  const api = await (await fetch('http://127.0.0.1:8788/api/ziwei/year?birth=1996-04-18%2013:46&gender=0&year=2026')).json()
  const dom = JSON.parse(await evalJs(`JSON.stringify({
    open: document.querySelector('#flow')?.classList.contains('on'),
    text: document.querySelector('#flow')?.textContent.replace(/\\s+/g,' ').trim().slice(0, 140),
    daxianCell: document.querySelector('.palace.daxian')?.dataset.zhi || null,
    liunianCell: document.querySelector('.palace.liunian')?.dataset.zhi || null,
    data: document.body.dataset.flow || null
  })`))

  console.log('页面：', JSON.stringify(dom))
  console.log('API ：', JSON.stringify({ daxian: api.daxian.zhi, liunian: api.liunian.zhi, age: api.age }))
  console.log('一致：', dom.daxianCell === api.daxian.zhi && dom.liunianCell === api.liunian.zhi)

  await evalJs(`document.querySelector('#flow')?.scrollIntoView({block:'center'})`)
  await sleep(400)
  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('ziwei-year-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved ziwei-year-shot.png')
  ws.close()
} finally {
  browser.kill()
}
