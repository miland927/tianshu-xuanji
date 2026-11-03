// Vendors the exact subset of three@0.160.0 the project imports,
// following `import ... from '...'` edges from the entry points.
// Usage: node vendor/bundle-three.mjs <extracted-three-package-dir>
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, join, relative, resolve, sep } from 'node:path'

const pkgRoot = resolve(process.argv[2] ?? '')
const here = dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'))
const outRoot = join(here, 'three')

const entries = [
  'examples/jsm/postprocessing/EffectComposer.js',
  'examples/jsm/postprocessing/RenderPass.js',
  'examples/jsm/postprocessing/UnrealBloomPass.js',
  'examples/jsm/postprocessing/OutputPass.js',
]

const IMPORT_RE = /(?:^|\n)\s*(?:import|export)[\s\S]*?from\s*['"]([^'"]+)['"]/g

const seen = new Map() // abs path -> relative-to-pkg path
const queue = []

function enqueue(absPath, fromAbs) {
  if (seen.has(absPath)) return
  if (!existsSync(absPath)) {
    console.warn('MISSING', relative(pkgRoot, absPath), 'imported by', fromAbs && relative(pkgRoot, fromAbs))
    return
  }
  seen.set(absPath, relative(pkgRoot, absPath).split(sep).join('/'))
  queue.push(absPath)
}

// the library itself is always 'three' (resolved by the import map), so it is
// not an edge we follow; everything else must be a relative path.
for (const e of entries) enqueue(join(pkgRoot, e))

while (queue.length) {
  const file = queue.shift()
  const src = readFileSync(file, 'utf8')
  for (const m of src.matchAll(IMPORT_RE)) {
    const spec = m[1]
    if (!spec.startsWith('.')) continue // 'three' or a bare package
    enqueue(resolve(dirname(file), spec), file)
  }
}

const buildSrc = join(pkgRoot, 'build/three.module.js')
if (!existsSync(buildSrc)) throw new Error('build/three.module.js not found in ' + pkgRoot)

const files = [...seen.values()]
files.push('build/three.module.js')
for (const rel of files) {
  const dest = join(outRoot, rel)
  mkdirSync(dirname(dest), { recursive: true })
  writeFileSync(dest, readFileSync(join(pkgRoot, rel)))
}
console.log(`vendored ${files.length} files into ${relative(process.cwd(), outRoot) || outRoot}`)
for (const f of files.sort()) console.log('  ' + f)
