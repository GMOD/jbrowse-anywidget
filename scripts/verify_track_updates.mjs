// Check that changing the `tracks` trait updates the live browser instead of
// rebuilding it, against the built bundle in a real browser.
//
// This is the one trait whose handler is not a one-liner. The controller has no
// bulk setter for tracks (setTracks was removed upstream — it reconciled a list
// the user may have opened their own tracks into), so `change:tracks` diffs by
// trackId and calls addTrack/removeTrack. That exists for a specific loop:
// 09_interactive_controls sets `view.tracks = []` and then adds one, twice per
// slider step, and rebuilding each time would re-resolve the assembly and start
// a new RPC worker while the user is still dragging.
//
// The assertion is unmount counting. A rebuild tears the React root down, which
// empties the container element; a diff never does. Watching for that is the
// only signal available from outside the bundle — DOM node identity is not one,
// because React legitimately replaces nodes when a track list changes.
//
// Needs network, like every other harness run here: the tracks are the local
// peaks fixture, but the assembly is the hosted hg38 the screenshot specs use
// (there is no FASTA fixture in this repo). puppeteer resolves from the sibling
// jbrowse-components checkout (override with PUPPETEER_FROM=/path/to/pkg-dir).
// Run:  node scripts/verify_track_updates.mjs
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { extname, join } from 'node:path'
import { createRequire } from 'node:module'

const from =
  process.env.PUPPETEER_FROM ??
  new URL('../../jbrowse-components/package.json', import.meta.url).pathname
const puppeteer = createRequire(from)('puppeteer')

const REPO = new URL('..', import.meta.url).pathname
const TYPES = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.html': 'text/html',
  '.json': 'application/json',
  '.gz': 'application/octet-stream',
  '.tbi': 'application/octet-stream',
  '.bw': 'application/octet-stream',
}

// The same hosted assembly the screenshot specs use, and the same shorthand a
// notebook types. The peaks fixture is chr17, so the window below is over it.
const ASSEMBLY = {
  name: 'hg38',
  uri: 'https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz',
  aliases: ['GRCh38'],
}

const track = (trackId, name) => ({
  type: 'FeatureTrack',
  trackId,
  name,
  assemblyNames: ['hg38'],
  adapter: {
    type: 'BedTabixAdapter',
    bedGzLocation: { uri: '/scripts/fixtures/peaks.bed.gz' },
    index: { location: { uri: '/scripts/fixtures/peaks.bed.gz.tbi' } },
  },
})

// The fake model the bundle sees, with a real event bus this time: the
// screenshot harness stubs `on` out, so nothing there ever exercises a change
// handler.
const harness = `<!doctype html><html><head><meta charset="utf8">
<link rel="stylesheet" href="/jbrowse_anywidget/static/jbrowse-anywidget.css">
<style>html,body{margin:0}#root{width:1000px}</style></head><body>
<div id="root"></div>
<script type="module">
// A rebuild unmounts the React root, which empties this element. Count that.
window.__unmounts = 0
new MutationObserver(() => {
  if (!document.getElementById('root').children.length) { window.__unmounts++ }
}).observe(document.getElementById('root'), { childList: true })
const mod = await import('/jbrowse_anywidget/static/index.js')
const store = { ...window.__traits }
const listeners = {}
window.__model = {
  get: k => store[k],
  set: (k, v) => { store[k] = v },
  save_changes: () => {},
  on: (event, fn) => { (listeners[event] ??= []).push(fn) },
  off: (event, fn) => {
    listeners[event] = (listeners[event] ?? []).filter(f => f !== fn)
  },
  // what a kernel-side assignment does: write the trait, then notify
  emit: (k, v) => {
    store[k] = v
    for (const fn of listeners['change:' + k] ?? []) { fn() }
  },
}
await mod.default.render({ model: window.__model, el: document.getElementById('root') })
window.__rendered = true
</script></body></html>`

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  if (url.pathname === '/harness.html') {
    res.setHeader('content-type', 'text/html')
    res.end(harness)
    return
  }
  try {
    const body = await readFile(join(REPO, url.pathname))
    res.setHeader(
      'content-type',
      TYPES[extname(url.pathname)] ?? 'application/octet-stream',
    )
    res.end(body)
  } catch {
    res.statusCode = 404
    res.end('not found')
  }
})
await new Promise(r => {
  server.listen(0, r)
})
const port = server.address().port

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

const failures = []
function check(ok, what) {
  console.log(`${ok ? '✓' : '✗'} ${what}`)
  if (!ok) {
    failures.push(what)
  }
}

const page = await browser.newPage()
const errors = []
page.on('pageerror', e => {
  errors.push(String(e))
})
// One element per open track: trackRenderingContainer-<viewId>-<trackId>
const trackSelector = id => `[data-testid$="-${id}"]`
const shownTracks = () =>
  page.evaluate(() =>
    [
      ...document.querySelectorAll('[data-testid^="trackRenderingContainer-"]'),
    ].map(el => el.getAttribute('data-testid').split('-').at(-1)),
  )

try {
  await page.setViewport({ width: 1000, height: 600 })
  await page.evaluateOnNewDocument(
    traits => {
      window.__traits = traits
    },
    {
      assembly: ASSEMBLY,
      tracks: [track('first', 'First')],
      session: {},
      aggregate_text_search_adapters: [],
      local_files: {},
      plugins: [],
      location: '17:7,600,000..7,601,000',
      selected_feature: null,
    },
  )
  await page.goto(`http://localhost:${port}/harness.html?x=1`, {
    waitUntil: 'load',
    timeout: 60000,
  })
  await page.waitForFunction(() => window.__rendered === true, {
    timeout: 30000,
  })
  await page.waitForSelector(trackSelector('first'), { timeout: 60000 })

  // Ignore the unmount the first render itself causes on an empty container.
  await page.evaluate(() => {
    window.__unmounts = 0
  })

  // The 09_interactive_controls sequence: clear, then add the recomputed track.
  await page.evaluate(() => {
    window.__model.emit('tracks', [])
  })
  await page.evaluate(
    t => {
      window.__model.emit('tracks', [t])
    },
    track('second', 'Second'),
  )
  await page.waitForSelector(trackSelector('second'), { timeout: 60000 })

  const unmounts = await page.evaluate(() => window.__unmounts)
  check(
    unmounts === 0,
    `the engine survives a tracks change (${unmounts} unmounts)`,
  )
  const shown = await shownTracks()
  check(
    shown.includes('second') && !shown.includes('first'),
    `the declared set is what is open (${shown.join(', ') || 'nothing'})`,
  )

  // A loose spec has no trackId to diff on, so this one must fall back to a
  // rebuild rather than silently doing nothing.
  await page.evaluate(() => {
    window.__model.emit('tracks', [{ uri: '/scripts/fixtures/signal.bw' }])
  })
  await page.waitForFunction(
    () => !document.querySelector('[data-testid$="-second"]'),
    { timeout: 60000 },
  )
  const rebuilt = await page.evaluate(() => window.__unmounts)
  check(rebuilt > 0, `a track list with no trackIds rebuilds instead`)
} finally {
  await page.close()
  await browser.close()
  server.close()
}

if (errors.length) {
  console.error('page errors:', errors.slice(0, 5).join(' | '))
}
if (failures.length) {
  console.error(`\n${failures.length} check(s) failed`)
  process.exit(1)
}
console.log('\ntrack updates verified')
