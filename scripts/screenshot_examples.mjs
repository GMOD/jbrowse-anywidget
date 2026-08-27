// Render the built widget bundles in a headless browser with a fake anywidget
// model and screenshot them, so the README can show the widget actually working
// (and so we verify the bundle renders at all). Reads scripts/screenshot_specs.json
// (from run_examples.py); writes images/<name>.png.
//
// Run:  node scripts/screenshot_examples.mjs [name ...]
// puppeteer resolves from the sibling jbrowse-components checkout; override with
// PUPPETEER_FROM=/path/to/pkg-dir.
import { mkdir, readFile } from 'node:fs/promises'
import { join } from 'node:path'

import {
  ANYWIDGET_LOADER,
  REPO,
  fromMonorepo,
  launch,
  serveRepo,
} from './browser_harness.mjs'

// readiness waits come from the same checkout's @jbrowse/capture, so a capture
// here uses the identical signals jb2capture and the website screenshot
// generator use (per-display paint attributes, the loading overlay, visible
// "Loading…" banners) instead of a bespoke sleep
const { waitForDisplaysDone, waitForLoadingComplete, waitForQuiescent } =
  await import(fromMonorepo('products/jbrowse-capture/src/index.ts'))

const specs = JSON.parse(
  await readFile(join(REPO, 'scripts/screenshot_specs.json'), 'utf8'),
)

// A page that imports a built bundle and renders it with a fake anywidget model
// seeded from window.__traits — the same {get,set,on,off,save_changes} surface
// src/index.ts and src/app.ts read.
const harness = `<!doctype html><html><head><meta charset="utf8">
<link rel="stylesheet" href="/jbrowse_anywidget/static/jbrowse-anywidget.css">
<style>html,body{margin:0}#root{width:1000px}</style></head><body>
<div id="root"></div>
<script type="module">
${ANYWIDGET_LOADER}
const p = new URLSearchParams(location.search)
const mod = await loadAsAnywidgetDoes('/jbrowse_anywidget/static/' + p.get('bundle'))
const store = { ...window.__traits }
// Kernel-local files reach the widget as binary buffers, which anywidget hands
// to JS as DataViews. Rebuild that shape by fetching the fixtures, so the
// blob/byte-range read path is exercised exactly as it is in a notebook.
if (window.__localFileUrls) {
  store.local_files = Object.fromEntries(
    await Promise.all(
      Object.entries(window.__localFileUrls).map(async ([name, url]) => [
        name,
        new DataView(await (await fetch(url)).arrayBuffer()),
      ]),
    ),
  )
}
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

const { port, close } = await serveRepo(harness)

await mkdir(join(REPO, 'images'), { recursive: true })

// One browser per mode, launched on first use. `headed` is normalized because a
// spec that never mentions it and one that sets it false are the same request —
// keyed raw, `undefined` and `false` were two entries and two chromes.
const browsers = new Map()
async function browserFor(headed = false) {
  if (!browsers.has(headed)) {
    browsers.set(headed, await launch(headed))
  }
  return browsers.get(headed)
}

const READY_TIMEOUT = 90000

// ready when the loading overlay is gone, no "Downloading…"/"Loading…" status
// text remains, and every display has flipped to its `-done` test-id
async function waitForReady(page) {
  await waitForLoadingComplete(page, {
    waitForDownloads: true,
    timeout: READY_TIMEOUT,
  })
  await waitForQuiescent(page, { timeout: READY_TIMEOUT })
  await waitForDisplaysDone(page, READY_TIMEOUT)
}

// Render one spec in a fresh page and write its figure. Returns the page errors
// it collected, or null when the widget never painted a canvas at all.
async function capture(name, spec) {
  const tall = spec.bundle === 'app.js'
  const page = await (await browserFor(spec.headed)).newPage()
  const errors = []
  try {
    await page.setViewport({
      width: 1000,
      height: tall ? 760 : 440,
      deviceScaleFactor: 2,
    })
    page.on('pageerror', e => errors.push(String(e)))
    await page.evaluateOnNewDocument(
      (t, f) => {
        window.__traits = t
        window.__localFileUrls = f
      },
      spec.traits,
      spec.localFileUrls ?? null,
    )
    await page.goto(
      `http://localhost:${port}/harness.html?bundle=${spec.bundle}`,
      {
        waitUntil: 'load',
        timeout: 60000,
      },
    )
    try {
      await page.waitForFunction(() => window.__rendered === true, {
        timeout: 30000,
      })
      await page.waitForSelector('#root canvas', { timeout: 45000 })
    } catch (e) {
      console.error(`✗ ${name}: never rendered — ${e.message}`)
      if (errors.length)
        console.error('  page errors:', errors.slice(0, 3).join(' | '))
      return null
    }
    await waitForReady(page)
    // The element, not the page: a view's height is its own — one track or six
    // — so a fixed viewport leaves a band of dead white under the short ones
    // and crops the tall ones. The widget knows how tall it is.
    const root = await page.$('#root')
    await root.screenshot({ path: join(REPO, 'images', `${name}.png`) })
    return errors
  } finally {
    await page.close()
  }
}

// name arguments re-shoot just those specs: node scripts/screenshot_examples.mjs 03_alignments
const only = new Set(process.argv.slice(2))
let failed = 0

for (const [name, spec] of Object.entries(specs)) {
  if (only.size && !only.has(name)) {
    continue
  }
  const errors = await capture(name, spec)
  if (errors === null) {
    failed++
  } else {
    console.log(
      `✓ ${name} -> images/${name}.png${errors.length ? `  (${errors.length} page errors)` : ''}`,
    )
    if (errors.length) console.error('  ', errors.slice(0, 2).join(' | '))
  }
}

for (const browser of browsers.values()) {
  await browser.close()
}
close()
process.exit(failed ? 1 : 0)
