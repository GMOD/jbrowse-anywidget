// Render the built widget bundles in a headless browser with a fake anywidget
// model and screenshot them, so the README can show the widget actually working
// (and so we verify the bundle renders at all). Reads scripts/screenshot_specs.json
// (from gen_screenshot_specs.py); writes images/<name>.png.
//
// puppeteer resolves from the sibling jbrowse-components checkout, so run:
//   node --experimental-vm-modules \
//     $(cd ../jbrowse-components && pwd)/node_modules/.bin/.. -e ... (see package.json)
// or simply:  node scripts/screenshot_examples.mjs   (with puppeteer on NODE_PATH)
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { mkdir } from 'node:fs/promises'
import { extname, join } from 'node:path'
import { createRequire } from 'node:module'

// puppeteer isn't a dep of this repo; resolve it from the sibling
// jbrowse-components checkout (override with PUPPETEER_FROM=/path/to/pkg-dir).
const from =
  process.env.PUPPETEER_FROM ??
  new URL('../../jbrowse-components/package.json', import.meta.url).pathname
const puppeteer = createRequire(from)('puppeteer')

// readiness waits come from the same checkout's @jbrowse/browser-test-utils, so
// a capture here uses the identical signals the jbrowse-web browser tests and
// the website screenshot generator use (display `-done` test-ids, the loading
// overlay, visible "Loading…" banners) instead of a bespoke sleep
const { waitForDisplaysDone, waitForLoadingComplete, waitForQuiescent } =
  await import(
    new URL('packages/browser-test-utils/src/waits.ts', `file://${from}`).href
  )

const REPO = new URL('..', import.meta.url).pathname
const specs = JSON.parse(
  await readFile(join(REPO, 'scripts/screenshot_specs.json'), 'utf8'),
)

const TYPES = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.html': 'text/html',
  '.json': 'application/json',
}

// A page that imports a built bundle and renders it with a fake anywidget model
// seeded from window.__traits — the same {get,set,on,off,save_changes} surface
// src/index.jsx and src/app.jsx use.
const harness = `<!doctype html><html><head><meta charset="utf8">
<link rel="stylesheet" href="/jbrowse_anywidget/static/jbrowse-anywidget.css">
<style>html,body{margin:0}#root{width:1000px}</style></head><body>
<div id="root"></div>
<script type="module">
const p = new URLSearchParams(location.search)
const mod = await import('/jbrowse_anywidget/static/' + p.get('bundle'))
const store = { ...window.__traits }
const model = {
  get: k => store[k],
  set: (k, v) => { store[k] = v },
  save_changes: () => {},
  on: () => {},
  off: () => {},
}
await mod.default.render({ model, el: document.getElementById('root') })
window.__rendered = true
</script></body></html>`

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  if (url.pathname === '/harness.html') {
    res.setHeader('content-type', 'text/html')
    res.end(harness)
  } else {
    try {
      const body = await readFile(join(REPO, url.pathname))
      res.setHeader('content-type', TYPES[extname(url.pathname)] ?? 'application/octet-stream')
      res.end(body)
    } catch {
      res.statusCode = 404
      res.end('not found')
    }
  }
})
await new Promise(r => server.listen(0, r))
const port = server.address().port

await mkdir(join(REPO, 'images'), { recursive: true })
const browser = await puppeteer.launch({
  headless: true,
  args: [
    '--no-sandbox',
    '--enable-unsafe-swiftshader',
    '--use-gl=angle',
    '--use-angle=swiftshader',
    '--ignore-gpu-blocklist',
  ],
})

// name arguments re-shoot just those specs: node scripts/screenshot_examples.mjs 03_alignments
const only = new Set(process.argv.slice(2))

let failed = 0
for (const [name, spec] of Object.entries(specs)) {
  if (only.size && !only.has(name)) {
    continue
  }
  const tall = spec.bundle === 'app.js'
  const page = await browser.newPage()
  await page.setViewport({ width: 1000, height: tall ? 760 : 440, deviceScaleFactor: 2 })
  const errors = []
  page.on('pageerror', e => errors.push(String(e)))
  await page.evaluateOnNewDocument(t => { window.__traits = t }, spec.traits)
  await page.goto(`http://localhost:${port}/harness.html?bundle=${spec.bundle}`, {
    waitUntil: 'load',
    timeout: 60000,
  })
  try {
    await page.waitForFunction(() => window.__rendered === true, { timeout: 30000 })
    await page.waitForSelector('#root canvas', { timeout: 45000 })
  } catch (e) {
    console.error(`✗ ${name}: never rendered — ${e.message}`)
    if (errors.length) console.error('  page errors:', errors.slice(0, 3).join(' | '))
    failed++
    await page.close()
    continue
  }
  // ready when the loading overlay is gone, no "Downloading…"/"Loading…" status
  // text remains, and every display has flipped to its `-done` test-id
  await waitForLoadingComplete(page, { waitForDownloads: true, timeout: 90000 })
  await waitForQuiescent(page, { timeout: 90000 })
  await waitForDisplaysDone(page, 90000)
  const out = join(REPO, 'images', `${name}.png`)
  await page.screenshot({ path: out })
  console.log(`✓ ${name} -> images/${name}.png${errors.length ? `  (${errors.length} page errors)` : ''}`)
  if (errors.length) console.error('  ', errors.slice(0, 2).join(' | '))
  await page.close()
}

await browser.close()
server.close()
process.exit(failed ? 1 : 0)
