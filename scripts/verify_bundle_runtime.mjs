// The things the built bundle has to do at runtime that nothing else here sees:
// change tracks without rebuilding the engine, run its RPC in a worker, put the
// `configuration` trait's theme on the page, and report the live session back to
// the kernel. All against the real bundle in a real browser.
//
// `change:tracks` states the wanted list through the controller's declarative
// `update()`, which reconciles it against what is open. That matters for a
// specific loop: 09_interactive_controls sets `view.tracks = []` and then adds
// one, twice per slider step, and rebuilding each time would re-resolve the
// assembly and start a new RPC worker while the user is still dragging.
//
// The rebuild assertion is unmount counting. A rebuild tears the React root
// down, which empties the container element; an update never does. Watching for
// that is the only signal available from outside the bundle — DOM node identity
// is not one, because React legitimately replaces nodes when a track list
// changes.
//
// The worker assertion is positive, on the worker's own rpcServer. A worker
// that fails to boot is loud (its driver's boot promise never settles and every
// track hangs), but *no worker at all* is silent: drop makeWorkerInstance and
// every figure still draws, just on the notebook's UI thread.
//
// The theme assertion is an A/B on one colour nothing else on the page uses,
// because `configuration` reaching the engine and its `theme` slot reaching the
// paint are different claims — a trait that arrives and is ignored looks exactly
// like a trait that works.
//
// Needs network, like every other harness run here: the tracks are the local
// peaks fixture, but the assembly is the hosted hg38 the screenshot specs use
// (there is no FASTA fixture in this repo). puppeteer resolves from the sibling
// jbrowse-components checkout (override with PUPPETEER_FROM=/path/to/pkg-dir).
// Run:  node scripts/verify_bundle_runtime.mjs
import { ANYWIDGET_LOADER, launch, serveRepo } from './browser_harness.mjs'

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
${ANYWIDGET_LOADER}
const mod = await loadAsAnywidgetDoes('/jbrowse_anywidget/static/index.js')
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

const { port, close } = await serveRepo(harness)
const browser = await launch()

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
      // secondary, because that is the slot JBrowse's own header paints with
      configuration: { theme: { palette: { secondary: { main: '#ff0000' } } } },
      current_session: {},
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

  // Identified by what it serves, not by being the only worker on the page: with
  // the RPC on the main thread the parsers spawn their own workers *there*, so
  // the count is 4 without an RPC worker and 1 with one (those nest inside it
  // and stop being the page's).
  const registered = await Promise.all(
    page
      .workers()
      .map(w =>
        w
          .evaluate(() => Object.keys(self.rpcServer?.methods ?? {}))
          .catch(() => []),
      ),
  )
  const rpc = registered.find(methods => methods.includes('CoreGetFeatures'))
  check(
    rpc !== undefined,
    `the RPC runs in a worker (${rpc ? `${rpc.length} methods` : `${registered.length} workers, none serving RPC`})`,
  )

  const themed = await page.evaluate(() =>
    [...document.querySelectorAll('*')].some(
      el => getComputedStyle(el).backgroundColor === 'rgb(255, 0, 0)',
    ),
  )
  check(themed, `the configuration trait's theme reaches the paint`)

  // onSessionChange fires when the layout settles, which the track change above
  // is. Its shape is what `session=` takes, so this is the round-trip — and it
  // is `view` singular here, not the app product's `views`, because this is the
  // one-view product.
  const saved = await page.evaluate(() => window.__model.get('current_session'))
  check(
    saved?.view?.type === 'LinearGenomeView',
    `the live session reports back (${Object.keys(saved ?? {}).join(', ') || 'nothing'})`,
  )

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

  // A loose spec — a bare data-file uri, no trackId — is applied live too: the
  // controller expands it through the same guessTrackConf the "Add track" flow
  // uses, so there is nothing for this side to diff on and nothing to rebuild
  // for. This is the case the old addTrack/removeTrack diff could not do.
  await page.evaluate(() => {
    window.__model.emit('tracks', [{ uri: '/scripts/fixtures/signal.bw' }])
  })
  await page.waitForFunction(
    () => !document.querySelector('[data-testid$="-second"]'),
    { timeout: 60000 },
  )
  const stillLive = await page.evaluate(() => window.__unmounts)
  const loose = await shownTracks()
  check(
    stillLive === 0,
    `a loose spec updates live too (${stillLive} unmounts)`,
  )
  check(
    loose.length === 1 && !loose.includes('second'),
    `the loose spec is the one track open (${loose.join(', ') || 'nothing'})`,
  )
} finally {
  await page.close()
  await browser.close()
  close()
}

if (errors.length) {
  console.error('page errors:', errors.slice(0, 5).join(' | '))
}
if (failures.length) {
  console.error(`\n${failures.length} check(s) failed`)
  process.exit(1)
}
console.log('\nbundle runtime verified')
