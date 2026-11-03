// 奇门方阵（3D 透视）验收：九宫数据与 API 一致，点宫能出细节。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const AT = process.argv[2] ?? '2026-11-03 15:00'
const port = 9357
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-qm3d-'))
const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1400,900',
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
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1400, height: 900, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/qimen3d.html' })
  await sleep(1800)

  await evalJs(`(() => {
    document.querySelector('#at').value = ${JSON.stringify(AT)};
    document.querySelector('#go').click();
    return 'ok';
  })()`)
  await sleep(900)

  const dom = JSON.parse(await evalJs(`JSON.stringify({
    cells: [...document.querySelectorAll('.cell')].map(c => ({
      gong: +c.dataset.gong, tian: c.dataset.tian, door: c.dataset.door,
      star: c.dataset.star, shen: c.dataset.shen,
      zhifu: c.classList.contains('zhifu'), zhishi: c.classList.contains('zhishi')
    })),
    ju: document.body.dataset.ju,
    detail: document.querySelector('#detail').textContent.slice(0, 40)
  })`))

  let bad = 0
  for (const c of dom.cells) {
    const p = api.pan.palaces[String(c.gong)] || {}
    const diffs = []
    if (c.tian !== (p.tian || []).join('')) diffs.push('天盘')
    if (c.door !== (p.door || '')) diffs.push('门')
    if (c.star !== (p.star || '')) diffs.push('星')
    if (c.shen !== (p.shen || '')) diffs.push('神')
    if (c.zhifu !== (api.pan.zhifu_gong === c.gong)) diffs.push('直符标记')
    if (c.zhishi !== (api.pan.zhishi_gong === c.gong)) diffs.push('直使标记')
    if (diffs.length) { bad++; console.log(`  ${c.gong}宫：${diffs.join('、')}`) }
  }
  console.log('九宫：', dom.cells.length, '处不一致：', bad)
  console.log('局标记：', dom.ju, '| 详情初始：', dom.detail)

  const clicked = await evalJs(`(() => {
    const c = document.querySelector('.cell:not(.center)');
    c.click();
    return document.querySelector('#detail').textContent.slice(0, 60);
  })()`)
  console.log('点宫后：', clicked)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('qimen3d-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved qimen3d-shot.png')
  ws.close()
} finally {
  browser.kill()
}
