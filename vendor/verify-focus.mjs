// P3 验收：问一句「现在什么节气」，看铜环有没有真的转到那一格。
// usage: node vendor/verify-focus.mjs [url]
import { writeFileSync, readFileSync, existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const url = process.argv[2] ?? 'http://127.0.0.1:8788/'
// 端口让 Edge 自己挑（0），从 profile 里的 DevToolsActivePort 读回来。
// 原先固定 9336：连跑两次时上一个 Edge 还没退干净，新脚本会连到旧实例上，随机失败。
let port = 0
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const profile = mkdtempSync(join(tmpdir(), 'cw-focus-'))

const browser = spawn(edge, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--hide-scrollbars', '--window-size=1600,900',
  '--enable-unsafe-swiftshader', '--use-angle=swiftshader', 'about:blank',
], { stdio: 'ignore' })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const send = (ws, id, method, params = {}) => new Promise((resolve, reject) => {
  const onMessage = (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.id !== id) return
    ws.removeEventListener('message', onMessage)
    msg.error ? reject(new Error(method + ': ' + msg.error.message)) : resolve(msg.result)
  }
  ws.addEventListener('message', onMessage)
  ws.send(JSON.stringify({ id, method, params }))
})

let id = 0
try {
  const portFile = join(profile, 'DevToolsActivePort')
  for (let i = 0; i < 80; i++) {
    if (!port && existsSync(portFile)) port = Number(readFileSync(portFile, 'utf8').split('\n')[0]) || 0
    try { if (port && (await fetch(`http://127.0.0.1:${port}/json/version`)).ok) break } catch { }
    await sleep(250)
  }
  if (!port) throw new Error('Edge 没起来：DevToolsActivePort 没出现')
  const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
  const ws = new WebSocket(tab.webSocketDebuggerUrl)
  await new Promise((r, j) => { ws.addEventListener('open', r); ws.addEventListener('error', j) })

  const evalJs = async (expression) => {
    const r = await send(ws, ++id, 'Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    return r.result?.value
  }

  await send(ws, ++id, 'Page.enable')
  await send(ws, ++id, 'Runtime.enable')
  await send(ws, ++id, 'Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false })
  await send(ws, ++id, 'Page.navigate', { url })
  // 不按固定秒数等：软件渲染（swiftshader）下首帧可能很慢。等到 __wheel 真挂上再测，最多 20 秒。
  // 等不到就把页面实际停在哪里打出来——之前的 no-indexOf 就是页面根本没打开（拒绝连接），不是接口坏了。
  let ready = false
  for (let i = 0; i < 80 && !ready; i++) {
    await sleep(250)
    try { ready = await evalJs(`!!(window.__wheel && typeof window.__wheel.indexOf === 'function' && document.querySelector('#xji-trigger'))`) } catch { }
  }
  if (!ready) console.log('page:', await evalJs(`JSON.stringify({ href: location.href, state: document.readyState, title: document.title })`))

  const ok = await evalJs(`(() => {
    if (!window.__wheel || typeof window.__wheel.indexOf !== 'function') return 'no-indexOf'
    document.querySelector('#xji-trigger').click()
    return 'ok'
  })()`)
  console.log('wheel api:', ok)

  await evalJs(`
    document.querySelector('#xji-input').value = '现在是什么节气？';
    document.querySelector('#xji-form').requestSubmit();
    'sent'
  `)
  await sleep(2200)

  const probe = await evalJs(`JSON.stringify({
    focus: document.body.dataset.focus || null,
    idxCheck: window.__wheel.indexOf('二十四节气', '寒露'),
    chip: [...document.querySelectorAll('#xji-meta i')].map(e => e.textContent)
  })`)
  console.log('probe', probe)

  const shot = await send(ws, ++id, 'Page.captureScreenshot', { format: 'png' })
  writeFileSync('focus-shot.png', Buffer.from(shot.data, 'base64'))
  console.log('saved focus-shot.png')
  ws.close()
} finally {
  browser.kill()
}
