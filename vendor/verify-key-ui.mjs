// 网页上配 key 的验收：点开 ⚙ → 填 key → 保存并测试 → 状态变成「已配置」。
import { spawn } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const KEY = process.env.TEST_KEY || ''
const port = 9359
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-key-'))
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

  const before = await (await fetch('http://127.0.0.1:8788/api/config')).json()
  console.log('打开前：', JSON.stringify(before))

  await send(ws, ++id, 'Page.navigate', { url: 'http://127.0.0.1:8788/' })
  await sleep(2400)
  await evalJs(`(() => { document.querySelector('#xji-trigger').click(); document.querySelector('#xji-keybtn').click(); return 'opened' })()`)
  await sleep(700)

  const opened = await evalJs(`JSON.stringify({
    boxVisible: !document.querySelector('#xji-keybox').hidden,
    status: document.querySelector('#xji-kstatus').textContent.trim()
  })`)
  console.log('配置框：', opened)

  if (!KEY) {
    console.log('没有 TEST_KEY，跳过填写')
  } else {
    await evalJs(`(() => {
      document.querySelector('#xji-key').value = ${JSON.stringify(KEY)};
      document.querySelector('#xji-ksave').click();
      return 'saved';
    })()`)
    await sleep(4000)
    const after = await evalJs(`JSON.stringify({
      status: document.querySelector('#xji-kstatus').textContent.trim(),
      msg: document.querySelector('#xji-kmsg').textContent.trim()
    })`)
    console.log('保存后：', after)
    const cfg = await (await fetch('http://127.0.0.1:8788/api/config')).json()
    const health = await (await fetch('http://127.0.0.1:8788/api/health')).json()
    console.log('服务端：', JSON.stringify({ present: cfg.key_present, source: cfg.key_source, mask: cfg.key_mask, mock: health.mock }))
  }

  await evalJs(`document.querySelector('#xji-keybox').scrollIntoView({block:'center'})`)
  await sleep(300)
  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('key-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved key-shot.png')
  ws.close()
} finally {
  browser.kill()
}
