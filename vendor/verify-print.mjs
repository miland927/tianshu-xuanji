// 年度报告导出验收：切成打印媒体后截图，并真打一份 PDF 看字节数。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9354
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-print-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1200,1400',
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
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/year.html' })
  await sleep(2600)

  // 屏幕上：底部应有「存为 PDF」按钮
  const screen = await evalJs(`JSON.stringify({
    pdfBtn: !!document.querySelector('#pdf'),
    bg: getComputedStyle(document.body).backgroundColor,
    rows: document.querySelectorAll('#tbl tr').length
  })`)
  console.log('屏幕上：', screen)

  // 切成打印媒体
  await send(ws, ++id, 'Emulation.setEmulatedMedia', { media: 'print' })
  await sleep(400)
  const print = await evalJs(`JSON.stringify({
    bg: getComputedStyle(document.body).backgroundColor,
    ink: getComputedStyle(document.body).color,
    controlsHidden: getComputedStyle(document.querySelector('.when')).display === 'none',
    rows: [...document.querySelectorAll('#tbl tr')].length
  })`)
  console.log('打印媒体下：', print)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
  writeFileSync('year-print.png', Buffer.from(shot.data, 'base64'))

  const pdf = await send(ws, ++id, 'Page.printToPDF', { printBackground: true, preferCSSPageSize: true })
  const bytes = Buffer.from(pdf.data, 'base64')
  writeFileSync('year-report.pdf', bytes)
  console.log('PDF 字节数：', bytes.length, '| 头四字节：', bytes.slice(0, 4).toString())
  ws.close()
} finally {
  browser.kill()
}
