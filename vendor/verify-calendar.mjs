// 节气历验收：24 行、交节时刻、三候、此刻标记
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9342
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-cal-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1600,1400',
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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1000, height: 1400, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/calendar.html' })
  await sleep(1800)

  const probe = await evalJs(`JSON.stringify({
    rows: document.querySelectorAll('.row').length,
    now: document.querySelector('.row.now .name')?.textContent || null,
    first: document.querySelector('.row .name').textContent,
    last: [...document.querySelectorAll('.row .name')].pop().textContent,
    hou: document.querySelector('.row .hou')?.textContent.trim() || null,
    at: document.querySelector('.row .at')?.textContent || null,
    moons: document.querySelectorAll('#moons .moon').length,
    nextMoon: document.querySelector('#moons .moon.next')?.textContent || null
  })`)
  console.log('probe', probe)

  await evalJs(`document.getElementById('next').click()`)
  await sleep(700)
  console.log('after 下一年:', await evalJs(`document.getElementById('yearLabel').textContent`))

  await evalJs(`document.getElementById('today').click()`)
  await sleep(1000)
  console.log('after 今天:', await evalJs(`JSON.stringify({
    year: document.getElementById('yearLabel').textContent,
    rows: document.querySelectorAll('.row').length,
    nowTop: Math.round(document.querySelector('.row.now')?.getBoundingClientRect().top ?? -1)
  })`))

  await evalJs(`document.querySelector('#moons')?.scrollIntoView({block:'center'})`)
  await sleep(500)
  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('calendar-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved calendar-shot.png')
  ws.close()
} finally {
  browser.kill()
}
