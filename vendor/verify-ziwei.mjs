// 紫微盘验收：十二宫对得上 API，生年四化落在对的星上，命宫/身宫标对。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const BIRTH = process.argv[2] ?? '1996-04-18 13:46'
const SEX = process.argv[3] ?? '0'
const port = 9345
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-ziwei-'))
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
  const api = await (await fetch(`http://127.0.0.1:8788/api/ziwei?birth=${encodeURIComponent(BIRTH)}&gender=${SEX}`)).json()

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
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/ziwei.html' })
  await sleep(1600)
  await evalJs(`(() => {
    document.querySelector('#birth').value = ${JSON.stringify(BIRTH)};
    document.querySelector('#sex').value = ${JSON.stringify(SEX)};
    document.querySelector('#go').click();
    return 'ok';
  })()`)
  await sleep(900)

  const dom = JSON.parse(await evalJs(`JSON.stringify({
    cells: [...document.querySelectorAll('.palace')].map(e => ({
      zhi: e.dataset.zhi, name: e.dataset.name, mains: e.dataset.mains,
      ming: e.classList.contains('ming'), shen: e.classList.contains('shen'),
      hua: [...e.querySelectorAll('.hua')].map(h => h.parentElement.textContent.trim().replace(/\\s+/g, ' '))
    })),
    data: document.body.dataset.ziwei,
    center: document.querySelector('.center')?.textContent.replace(/\\s+/g, ' ').trim().slice(0, 80)
  })`))

  let bad = 0
  for (const c of dom.cells) {
    const p = api.palaces.find((x) => x.zhi === c.zhi)
    if (!p) { bad++; console.log('  缺宫', c.zhi); continue }
    const mains = (p.stars || []).filter((s) => s.kind === 'main').map((s) => s.name).join(',')
    const diffs = []
    if (c.name !== p.name) diffs.push(`宫名 ${c.name}≠${p.name}`)
    if (c.mains !== mains) diffs.push(`主星 ${c.mains}≠${mains}`)
    if (c.ming !== (p.zhi === api.ming)) diffs.push('命宫标记')
    if (c.shen !== Boolean(p.is_shen)) diffs.push('身宫标记')
    if (diffs.length) { bad++; console.log(`  ${c.zhi}宫：`, diffs.join('；')) }
  }

  const apiHua = api.palaces.flatMap((p) => (p.stars || []).filter((s) => s.hua).map((s) => `${s.name}${s.hua}`))
  console.log('十二宫：', dom.cells.length, '处不一致：', bad)
  console.log('API 生年四化：', apiHua.join(' '))
  console.log('DOM 上的四化：', dom.cells.flatMap((c) => c.hua).join(' | ') || '（无）')
  console.log('中宫：', dom.center)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('ziwei-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved ziwei-shot.png')
  ws.close()
} finally {
  browser.kill()
}
