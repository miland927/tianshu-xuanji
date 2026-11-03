// 出处跳转验收：打开面板 → 问一句 → 展开依据 → 点引用 → 看原文出来没有。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const port = 9349
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-passage-'))
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
  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/' })
  await sleep(2600)

  // 填生日（不然只有历法依据，没有用神，也就没有典籍引用），再问一句
  await evalJs(`(() => {
    document.querySelector('#xji-trigger').click();
    const set = (sel, v) => { const el = document.querySelector(sel); if (el) { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})) } };
    document.querySelector('#xji-birth').open = true;
    set('#xji-b-date', '1996-04-18 14:06');
    set('#xji-b-lon', '114.93');
    set('#xji-input', '我这个盘怎么样？');
    document.querySelector('#xji-send').click();
    return 'sent';
  })()`)
  await sleep(6000)

  const opened = await evalJs(`(() => {
    const b = document.querySelector('.ev-btn'); if (!b) return 'no-ev-btn';
    b.click(); return 'clicked';
  })()`)
  await sleep(400)

  const before = await evalJs(`JSON.stringify({
    opened: ${JSON.stringify(opened)},
    cites: document.querySelectorAll('.ev-cite').length,
    first: document.querySelector('.ev-cite')?.textContent || null,
    passages: document.querySelectorAll('.ev-passage').length
  })`)
  console.log('依据展开：', before)

  const clicked = await evalJs(`(() => {
    const c = document.querySelector('.ev-cite'); if (!c) return 'no-cite';
    c.click(); return 'clicked';
  })()`)
  await sleep(1500)

  const after = await evalJs(`JSON.stringify({
    clicked: ${JSON.stringify(clicked)},
    passages: document.querySelectorAll('.ev-passage').length,
    text: document.querySelector('.ev-passage')?.textContent.replace(/\\s+/g,' ').trim().slice(0, 120) || null
  })`)
  console.log('点开后：', after)

  await evalJs(`document.querySelector('.ev-passage')?.scrollIntoView({block:'center'})`)
  await sleep(500)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('passage-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved passage-shot.png')
  ws.close()
} finally {
  browser.kill()
}
