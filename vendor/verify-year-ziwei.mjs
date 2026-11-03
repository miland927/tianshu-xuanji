// 年度报告里的紫微块：数字与 /api/ziwei/year 对得上，且能滚到眼前。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const BIRTH = '1996-04-18 14:06'
const YEAR = 2026
const port = 9358
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-year-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1200,1200',
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
  const api = await (await fetch(`http://127.0.0.1:8788/api/ziwei/year?birth=${encodeURIComponent(BIRTH)}&gender=0&year=${YEAR}`)).json()

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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1200, height: 1200, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/year.html' })
  await sleep(2200)
  await evalJs(`(() => {
    document.querySelector('#birth').value = ${JSON.stringify(BIRTH)};
    document.querySelector('#year').value = '${YEAR}';
    document.querySelector('#go').click();
    return 'ok';
  })()`)
  await sleep(1200)

  const dom = JSON.parse(await evalJs(`JSON.stringify({
    cells: [...document.querySelectorAll('#zw div')].map(d => d.textContent.replace(/\\s+/g, ' ').trim()),
    monthRows: document.querySelectorAll('#tbl tr').length
  })`))

  const want = [String(api.age), api.daxian.name + '宫', api.liunian.name, api.xiaoxian.name, api.ming.name]
  const joined = dom.cells.join(' | ')
  const missing = want.filter((w) => !joined.includes(w))
  console.log('紫微块：', joined.slice(0, 120))
  console.log('期望值：', want.join(' / '), '| 缺失：', missing.length ? missing : '无')
  console.log('月份行数：', dom.monthRows)

  await evalJs(`document.querySelector('#zw').scrollIntoView({block:'center'})`)
  await sleep(400)
  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('year-ziwei-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved year-ziwei-shot.png')
  ws.close()
} finally {
  browser.kill()
}
