// Minimal static file server, used only when Python is not available.
// usage: node vendor/serve.mjs [port] [root]
import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, join, normalize, resolve } from 'node:path'

const port = Number(process.argv[2] ?? 8788)
const root = resolve(process.argv[3] ?? join(import.meta.dirname, '..'))

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.md': 'text/markdown; charset=utf-8',
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost')
    let file = join(root, normalize(decodeURIComponent(url.pathname)).replace(/^([/\\])+/, ''))
    if (!file.startsWith(root)) { res.writeHead(403).end('forbidden'); return }
    let info = await stat(file).catch(() => null)
    if (info?.isDirectory()) { file = join(file, 'index.html'); info = await stat(file).catch(() => null) }
    if (!info) { res.writeHead(404, { 'content-type': 'text/plain' }).end('not found'); return }
    const body = await readFile(file)
    res.writeHead(200, { 'content-type': TYPES[extname(file).toLowerCase()] ?? 'application/octet-stream', 'cache-control': 'no-cache' })
    res.end(body)
  } catch (err) {
    res.writeHead(500, { 'content-type': 'text/plain' }).end(String(err))
  }
})

server.listen(port, '127.0.0.1', () => {
  console.log(`serving ${root}\n  http://127.0.0.1:${port}/`)
})
