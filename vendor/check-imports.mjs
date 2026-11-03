// Verifies that every ES module reachable from index.html resolves over HTTP.
// Mimics the browser: import map applies only to bare specifiers.
const BASE = process.argv[2] ?? 'http://127.0.0.1:8788/'
const root = new URL(BASE)

const html = await (await fetch(root)).text()

// import map
const mapJson = JSON.parse(html.match(/<script type="importmap">([\s\S]*?)<\/script>/)[1])
const imports = mapJson.imports ?? {}
const resolveBare = (spec) => {
  if (imports[spec]) return imports[spec]
  // longest trailing-slash prefix
  const prefixes = Object.keys(imports).filter((k) => k.endsWith('/')).sort((a, b) => b.length - a.length)
  for (const p of prefixes) if (spec.startsWith(p)) return imports[p] + spec.slice(p.length)
  return null
}

const IMPORT_RE = /(?:^|\n)\s*(?:import|export)[\s\S]{0,400}?from\s*['"]([^'"]+)['"]/g
const seen = new Set()
const problems = []
const queue = []

// module scripts inside index.html: the inline one plus any src=
for (const m of html.matchAll(/<script[^>]*type="module"[^>]*>([\s\S]*?)<\/script>/g)) {
  for (const i of m[1].matchAll(IMPORT_RE)) queue.push([i[1], 'index.html (inline)'])
}
for (const m of html.matchAll(/<script[^>]*type="module"[^>]*src="([^"]+)"/g)) queue.push([m[1], 'index.html'])

while (queue.length) {
  const [spec, fromDoc] = queue.shift()
  const base = fromDoc === 'index.html' || fromDoc === 'index.html (inline)' ? root : new URL(fromDoc)
  const mapped = spec.startsWith('.') || spec.startsWith('/') ? spec : resolveBare(spec)
  if (!mapped) { problems.push(`unmapped bare specifier "${spec}" in ${fromDoc}`); continue }
  // Per spec the import map's addresses resolve against the *document* base URL,
  // not against the importing module.
  const url = spec.startsWith('.') || spec.startsWith('/') ? new URL(mapped, base) : new URL(mapped, root)
  if (seen.has(url.href)) continue
  seen.add(url.href)
  const res = await fetch(url)
  if (!res.ok) { problems.push(`${res.status} ${url.pathname}  (from ${new URL(fromDoc, root).pathname})`); continue }
  const body = await res.text()
  for (const i of body.matchAll(IMPORT_RE)) queue.push([i[1], url.href])
}

console.log(`checked ${seen.size} module URLs`)
if (problems.length) { console.log('PROBLEMS:'); for (const p of problems) console.log('  ' + p); process.exit(1) }
console.log('OK: every import resolves and returns 200')
