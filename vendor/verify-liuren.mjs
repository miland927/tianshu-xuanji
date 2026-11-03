// 六壬盘验收：DOM 上的十二格对不对得上 API 的天地盘，三传标记落对没有。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const AT = process.argv[2] ?? '2026-11-03 01:30'
const port = 9343
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-liuren-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1400,1000',
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
  const api = await (await fetch(`http://127.0.0.1:8788/api/liuren?at=${encodeURIComponent(AT)}`)).json()

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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/liuren.html' })
  await sleep(1600)

  await evalJs(`(() => {
    document.querySelector('#at').value = ${JSON.stringify(AT)};
    document.querySelector('#go').click();
    return 'ok';
  })()`)
  await sleep(900)

  const dom = JSON.parse(await evalJs(`JSON.stringify({
    cells: [...document.querySelectorAll('#plate path[data-pos]')].map(e => [e.dataset.pos, e.dataset.up]),
    marks: [...document.querySelectorAll('#plate path[data-mark]')].map(e => e.dataset.mark + ':' + e.dataset.pos + '>' + e.dataset.up),
    ke: document.body.dataset.ke
  })`))

  const expected = Object.entries(api.tian_di_pan)
  const mismatched = dom.cells.filter(([pos, up]) => api.tian_di_pan[pos] !== up)
  console.log('十二格：', dom.cells.length, '处不一致：', mismatched.length)
  console.log('三传标记：', dom.marks.join(' '))
  console.log('API 三传：', [api.three_chuan.chu, api.three_chuan.zhong, api.three_chuan.mo].map((c) => c.zhi).join(' '))
  console.log('页眉：', dom.ke)

  // 每个传支都该在天盘上找到一个位置
  for (const c of [api.three_chuan.chu, api.three_chuan.zhong, api.three_chuan.mo]) {
    const pos = expected.find(([, up]) => up === c.zhi)?.[0]
    const hit = dom.marks.find((m) => m.includes('>' + c.zhi))
    console.log(`  ${c.zhi} 应在 ${pos} 格：`, hit ? 'OK ' + hit : 'MISSING')
  }

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('liuren-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved liuren-shot.png')
  ws.close()
} finally {
  browser.kill()
}
