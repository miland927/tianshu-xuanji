// 奇门九宫验收：DOM 上的九宫与 API 逐格对照，直符直使落宫、成格数都要对得上。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const AT = process.argv[2] ?? '2026-11-03 15:00'
const port = 9344
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-qimen-'))
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
  const api = await (await fetch(`http://127.0.0.1:8788/api/qimen?at=${encodeURIComponent(AT)}`)).json()

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
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/qimen.html' })
  await sleep(1600)
  await evalJs(`(() => {
    document.querySelector('#at').value = ${JSON.stringify(AT)};
    document.querySelector('#go').click();
    return 'ok';
  })()`)
  await sleep(900)

  const dom = JSON.parse(await evalJs(`JSON.stringify({
    cells: [...document.querySelectorAll('#grid .gong')].map(e => ({
      gong: +e.dataset.gong, tian: e.dataset.tian, di: e.dataset.di,
      door: e.dataset.door, star: e.dataset.star, shen: e.dataset.shen,
      zhifu: e.classList.contains('zhifu'), zhishi: e.classList.contains('zhishi')
    })),
    ju: document.body.dataset.ju,
    sizhu: document.querySelector('#kv').textContent.slice(0, 60)
  })`))

  let bad = 0
  for (const c of dom.cells) {
    const p = api.pan.palaces[String(c.gong)] || {}
    const tian = (p.tian || []).join('')
    const di = (p.di || []).join('')
    const diffs = []
    if (c.tian !== tian) diffs.push(`天盘 ${c.tian}≠${tian}`)
    if (c.di !== di) diffs.push(`地盘 ${c.di}≠${di}`)
    if (c.door !== (p.door || '')) diffs.push(`门 ${c.door}≠${p.door || ''}`)
    if (c.star !== (p.star || '')) diffs.push(`星 ${c.star}≠${p.star || ''}`)
    if (c.shen !== (p.shen || '')) diffs.push(`神 ${c.shen}≠${p.shen || ''}`)
    if (c.zhifu !== (api.pan.zhifu_gong === c.gong)) diffs.push('直符标记')
    if (c.zhishi !== (api.pan.zhishi_gong === c.gong)) diffs.push('直使标记')
    if (diffs.length) { bad++; console.log(`  ${c.gong}宫：`, diffs.join('；')) }
  }

  console.log('九宫：', dom.cells.length, '处不一致：', bad)
  console.log('ju:', dom.ju, '| API:', `${api.ju.dun}|${api.ju.ju}|${api.pan.zhifu_gong}|${api.pan.zhishi_gong}|${(api.geju || []).length}`)
  console.log('四柱显示:', dom.sizhu.replace(/\s+/g, ' ').trim().slice(0, 40))

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('qimen-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved qimen-shot.png')
  ws.close()
} finally {
  browser.kill()
}
