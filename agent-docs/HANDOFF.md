# Handoff

State as of the API-reduction work. Read `IDEAS.md` for deferred features; this
is the "what just changed, what will bite you" file.

## The design rule now in force

**Python adds only what JSON cannot express itself.** Everything else is a plain
dict handed to JBrowse.

The public surface is six names, and each earns its place by that bar:

|                                   | why it survives             |
| --------------------------------- | --------------------------- |
| `LinearGenomeView`, `JBrowseApp`  | the widgets                 |
| `add_features` / `features_track` | a DataFrame is not JSON     |
| `add_local_file`                  | bytes are not JSON          |
| `fetch_hub`, `plugin`             | a network fetch is not JSON |

A **trait** is not a helper and does not count against that bar —
`configuration` is JBrowse's root config block handed straight over, so `theme`,
`preferences`, `rpc` and `formatDetails` all arrived without a Python name each.
Adding a trait that passes a config dict through is the shape to reach for;
adding a function that _shapes_ one is not.

`track`, `view`, `linear_view`, `synteny_view`, `dotplot_view`, `synteny_track`,
`make_assembly` and `protein_view` were all deleted: each returned a dict
literal, and each had to grow whenever JBrowse gained a type. If you are about
to add a helper that shapes config, don't — put the dict in the docs instead.
The payoff is that a view type, adapter or display JBrowse adds needs
**nothing** here.

## Traps

**CI builds against upstream `main`; you build against your checkout.** The
`link:` deps point at a sibling `jbrowse-components` working tree, and `tsc`
follows them into its _source_ — so `pnpm build` and `pnpm typecheck` passing
here says nothing about CI, which clones `GMOD/jbrowse-components` main instead.
Anything you just added to the monorepo has to be pushed before this repo's jobs
can go green, and the failure names the missing export rather than the cause.
This is not hypothetical: `localFiles`, `addLocalFiles`, `getSessionSnapshot`,
`setSession` and `CreateAppOptions.session` sat unpushed behind ~370 monorepo
commits while `bundle` and `typecheck` were red for them. Check
`git log origin/main..HEAD` in the monorepo before concluding a job is broken.

**`resolve.dedupe` makes this repo's version win.** `mobx` is deduped against
the linked monorepo checkout, so the version in `package.json` is not a local
preference — it must track the monorepo's. A monorepo bump breaks `pnpm build`
here and nothing else notices. This is exactly how mobx 6-vs-7 sat broken for
two weeks (`"compareStructural" is not exported`).

**No Node polyfills, on purpose.** The bundle has no `Buffer` and every
`process` read is behind a `typeof process` guard, so
`vite-plugin-node-polyfills` was deleted; only
`define: {'process.env.NODE_ENV'}` remains. It cost ~1.3MB. Don't reinstate it
on a "process is not defined" — check the guard first. If you add an assertion
for this, note that `grep 'Buffer\.'` matches `ArrayBuffer.isView` and
`dataBuffer.destroy`; use `grep -E '(^|[^A-Za-z0-9_$])Buffer\.'`.

**esbuild does not typecheck.** `pnpm build` succeeding proves nothing about
types — a missing import ships happily and fails at runtime. That happened this
session (`getSessionSnapshot` unimported in `src/app.ts`, caught only once
`pnpm typecheck` was repaired). Run `pnpm typecheck`; it works now.

**`assemblyNames` is the view's job, not Python's.** The view stamps its own
resolved assembly onto any track that omits it, and knows that name even when
`assembly=` was a hub name it had to fetch. Stamping it here cannot survive
`view.assembly = ...`, because the view only fills an _absent_ `assemblyNames` —
the stale stamp wins and the track silently stops displaying. There is a test.

**jsdom cannot test the blob path.** Its `Blob.slice()` returns an object with
no `arrayBuffer()`, so `generic-filehandle2` cannot read from it. The byte-range
read is covered by notebook 12 — which writes a tabix BED of every human exon
_and_ a bigWig and hands both over with `add_local_file`; the bigWig is the
strong one, since it can only render if the blob is genuinely random-access —
and by product-core's `localFiles.test.ts`. The `render` workflow is what runs
that in CI, nightly and by `workflow_dispatch` on demand. It is deliberately not
on push/PR: it needs real network and links against jbrowse-components `main`,
so it fails for reasons unrelated to the commit that triggered it.

**Figures come from running the notebooks.** `python scripts/run_examples.py`
executes every `examples/*.ipynb` in a real kernel, in a scratch cwd, then runs
one more cell in that same kernel that reads the traits off every widget the
notebook left behind — named, or only displayed, since a notebook ending on a
bare `JBrowseApp(...)` binds no name and IPython's `Out` is the only place it
survives. Those become `scripts/screenshot_specs.json` and
`screenshot_examples.mjs` renders them.

The point is that a figure is the notebook, not a second description of it.
`gen_screenshot_specs.py` used to rebuild each example's config alongside the
notebook that showed it, and the two agreed only while someone kept them
agreeing — the README's claim to show "what the notebooks actually produce"
rested on that. It is deleted. Two figures have no notebook (`12_dotplot`,
`13_manhattan`) and are literals in `run_examples.py`; a figure that grows a
notebook should move out of there into `FIGURES`.

Executing them is also the only check that the notebooks _run_. `pytest` never
opens one.

Three things that bite:

- **Captured files go to `scripts/captured/`, not `scripts/fixtures/`.**
  Notebook 13 writes a `signal.bw` of its own and the fixtures directory has a
  committed one of that name which `verify_bundle_runtime.mjs` reads. Capturing
  into it silently overwrote the fixture, and the verifier then tested different
  bytes. `scripts/captured/` is gitignored and cleared per run.
- **pysam needs a CA bundle pointed out to it.** Its wheels ship their own
  libcurl with no CA path compiled in, so notebooks 05 and 10 die on an https
  BAM with `Libcurl reported error 77 (Problem with the SSL CA cert)` — which
  reads like a bad URL and is not. `run_examples.py` sets `CURL_CA_BUNDLE` and
  `SSL_CERT_FILE` from certifi when they are unset.
- **The whole corpus executes in about 90 seconds.** Every notebook is network
  bound, not compute bound, so this is cheap to run often — which is the point.
  Rendering is what costs, at roughly half a minute a figure.

**A headless figure renders with Canvas2D, not WebGL.** JBrowse steps over a
software rasterizer such as SwiftShader, so the harness exercises the Canvas2D
painters. The Manhattan figure was withdrawn for weeks for that reason: chr2's
217,292 points went into one Canvas2D path, and Chrome silently fills nothing
past about 180,000 discs. jbrowse-components `abc907751d` caps the path. The
same symptom, an axis with no data while every readiness signal says done, is
worth reproducing in jbrowse-web under the harness's Chrome flags before blaming
the config.

**A blank-figure check was tried and does not work.** `screenshot_examples.mjs`
fails a spec that paints no canvas, and deliberately not one that paints an
empty canvas: a track that fetched nothing still draws its axis, ruler and
gridlines. Measured against this very case — the empty Manhattan scored 28.1%
non-background pixels and a _good_ figure, `03_alignments`, scored 14.6%. No
threshold separates them, and restricting the sample to the lower 55% did not
either. Whatever catches a figure that lost its data, it is not pixel counting.

**`score` is the magic column.** `add_features` builds a `QuantitativeTrack` — a
real wiggle with a value axis — only when a column is literally named `score`.
`depth`/`signal` render as boxes. `quantitative=` overrides.

**Screenshot images are timing-dependent.** Re-rendering produces byte-different
PNGs even with no code change. Don't commit regenerated figures in a change that
isn't about them; `git checkout images/` after a verification run.

## The controller takes one declarative `update()`

`LinearGenomeViewController` is now `whenReady` / `update(state)` / `destroy`.
The four setters this repo used to call — `addTrack`, `removeTrack`,
`setLocation`, `addLocalFiles` — are gone (upstream `0c999fe484`), and before
that `setAssembly`/`setSession`/`setTracks` went the same way. `update` takes
`{ tracks?, location?, localFiles? }`: each field you state is the complete
wanted value, a field you leave out is left alone, and the engine survives.

What that means here: `change:assembly`, `change:session` and `change:plugins`
call the shell's `rebuild` — a different genome is a different browser, and a
plugin registers types into a live pluginManager. Everything else is one
`update` call, and **the trackId diff that used to live in `src/index.ts` is
gone**: no `appliedTracks` WeakMap, no `trackIds`, no rebuild fallback. The
controller reconciles the wanted list against what is open, `guessTrackConf`
expands a loose spec on the way, so the loose-spec case that used to force a
rebuild now updates live like any other.

Two things follow that are easy to get wrong:

- **`change:tracks` states `localFiles` too**, rather than trusting
  `change:local_files` to have run first. A cell that registers a file and opens
  a track on it changes both traits in one message and the event order is only
  state-dict key order; `update` registers files before it resolves the tracks
  that name them.
- **`optionsFromModel` awaits `loadPlugins` before reading any other trait.** A
  build waiting on a plugin fetch then opens whatever the kernel set while it
  waited — which is what lets the handlers drop an `update` that arrives with no
  controller yet instead of needing a rebuild fallback.

**A build failure needs `onError`.** `createLinearGenomeView` returns
synchronously and resolves the assembly inside itself, so a genome that will not
resolve never reaches the promise `defineWidget` awaits. `defineWidget` hands
`build` a `fail` callback for exactly this; without it the cell stays blank and
the reason is console-only. `createApp` is synchronous throughout and needs
none.

`scripts/verify_bundle_runtime.mjs` covers it in a real browser, on the nightly
render workflow. Note what it does NOT assert: DOM node identity. React
legitimately replaces the header's nodes when the track list changes, so an
identity check reads as a rebuild that never happened — it counts container
unmounts instead. That cost a debugging round; don't reintroduce it.

## The RPC worker is inlined, and it has to be

The bundles pass `makeWorkerInstance`, so data fetching and parsing run off the
notebook's UI thread. Three things about how, each of which builds green and
breaks at runtime if you change it:

- **anywidget hands the page `_esm` as TEXT.** It blobs the string and imports
  the blob, so `import.meta.url` inside our bundle is `blob:<origin>/<uuid>` —
  and a blob URL is **opaque**, so it cannot be a base. Measured in a real
  browser: `new URL('./rpcWorker.js', import.meta.url)` from inside a blob
  module throws `Invalid URL`, before and after the URL is revoked. That call is
  the products' own `makeWorkerInstance` — the portable spelling, and the one to
  prefer everywhere else — so here it does not merely 404, it throws.

  Vite's non-inline `?worker` fails for a second, independent reason: in lib
  mode it emits `new Worker("/assets/rpcWorker-<hash>.js", {type:'module'})`, a
  **root-absolute** path that never involved `import.meta.url` at all. In a
  notebook that resolves against the Jupyter server's origin, where the widget's
  static files are not. Both roads are closed; inlining is the only one left.

- **The worker must not code-split.**
  `worker.rollupOptions.output.inlineDynamicImports` is what forces that.
  Without it Vite emits a self-contained-looking inline worker that still does
  `import('./BamAdapter-<hash>.js')` — resolved against the blob URL it was
  started from, so it 404s at the first BAM read while the build reports
  success. Checked by reading the emitted worker source, not the exit code: the
  only dynamic import that may remain is `fetchESM`'s, which takes an absolute
  plugin URL.
- **It costs about 2x, and the 2x is per widget.** index.js went 7.7 -> 15.4MB
  and app.js 9.2 -> 18.1MB, because the worker's copy of the adapters is a
  second copy. Read that as a download and it sounds like a one-off; it is not.
  anywidget does `add_traits(_esm=Unicode(...).tag(sync=True))` **per
  instance**, so the bundle's text crosses the kernel comm once per widget and
  the browser compiles a copy per widget. Measured on the installed wheel:
  `get_state()` is 14.9MB of `_esm` + `_css` for one `LinearGenomeView`, so
  notebook 13's two views are ~30MB, up from ~16MB.

  Still the right trade — a UI frozen for the length of a CRAM parse is worse
  than a slower first paint, and that paint was already dominated by this. But
  it is the number to weigh before adding a third view to an example, and the
  reason a worker entry narrower than `corePlugins` would be worth real effort
  if this ever has to come down.

**The harness loads the bundle the way anywidget does** — fetch its text, blob
it, import the blob, revoke. Both `.mjs` scripts used to `import()` it from its
own `http://` path, which is a friendlier module than a notebook ever gets:
`import.meta.url` resolves there, so the whole reason the worker is inlined went
untested. Don't simplify that back.

**A relative data URI has to be resolved before it reaches the worker.** The
worker's base is that same blob URL, so a `fetch('/data/x.bam')` there throws
`Failed to parse URL` and the track says "Network error fetching …" — which
reads as CORS or a server that ignores range requests, and is neither.
`createLinearGenomeView` and `createApp` stamp `document.baseURI` as the
`baseUri` of every `uri` in their options (jbrowse-components `2854d946b2`), so
the widget passes options through as the kernel sent them.
`verify_bundle_runtime.mjs` passed over the failure while it waited only for the
track container, which a failed fetch still mounts; it waits for a fixture
peak's label now.

`scripts/verify_bundle_runtime.mjs` pins it, and pins it _positively_ — on the
worker's own `self.rpcServer` and its `CoreGetFeatures` method. A worker that
fails to boot is loud (its driver's boot promise never settles and every track
hangs), but **no worker at all is silent**: drop `makeWorkerInstance` and every
figure still draws, just on the UI thread. Don't assert a worker _count_ either
— with the RPC on the main thread the parsers spawn their own workers there, so
the page has 4 without an RPC worker and 1 with one.

## The readiness waits live in @jbrowse/capture now

`scripts/screenshot_examples.mjs` imports them from
`products/jbrowse-capture/src/index.ts`, not the
`packages/browser-test-utils/src/waits.ts` they used to be at — that path no
longer exists and the nightly `render` job died at the import with
`ERR_MODULE_NOT_FOUND`. `scripts/browser_harness.mjs` borrows
`findChromeExecutable` from the same package, so a box with a system Chrome and
no `puppeteer browsers install` runs the harness anyway.

`browser_harness.mjs` is where both `.mjs` scripts get puppeteer, the static
server and the swiftshader launch flags. They had two copies and the copies had
drifted: the screenshot one keyed its browser cache on the raw `headed` field,
so a spec that omitted it and a spec that set it `false` were two entries and
two Chromes.

## Known broken / unresolved

### Notebook 14 (scATAC UMAP lasso) is written and runs; its figure is stale

Stopped mid-step on 2026-08-27. Everything below is uncommitted in the working
tree.

**What it is.** A UMAP with a lasso beside a genome view: select cells, and the
track repaints with the pseudobulk of exactly those cells. Requested as the
thing the `scatac_pseudobulk` tutorial in jbrowse-components cannot do, since a
page cannot be interactive.

**State, file by file:**

- `examples/14_scatac_umap.ipynb` — generated, and regenerated after the fix
  below (it contains `#4682b4`, so it is current).
- `scripts/build_examples.py` — the `14_scatac_umap` entry, appended before
  `print("done")`.
- `scripts/run_examples.py` — a `FIGURES` entry keyed `14_scatac_umap`, with
  `"variable": "view"`. Without it the runner reports `(ran; no figure)` and
  writes no spec, which is what it does for a notebook nobody photographs.
- `scripts/screenshot_specs.json` — carries a `14_scatac_umap` spec, but from
  the run BEFORE the fix.
- `images/14_scatac_umap.png` — **stale, and shows a red error banner.** Its
  mtime (08:26) predates the notebook's (08:27). Re-render it.
- `atac_pbmc_5k_nextgem_fragments.tsv.gz.tbi` — untracked, 787 KB, dropped in
  the repo root by pysam fetching the remote index. Delete it or gitignore it;
  do not commit it.

**To finish:** `.venv/bin/python scripts/run_examples.py 14 --no-render`, then
`node scripts/screenshot_examples.mjs`, then look at the PNG. The last render
failed with `TypeError: Cannot read properties of undefined (reading 'get')` and
the fix is already in — a `jexl:` color on a `score` column. A `score` column
makes `add_features` build a `QuantitativeTrack`, whose display has no
per-feature color callback, so the jexl blew up in the browser while the track
name and cell count rendered fine. It is a plain `#4682b4` now. **Nothing in the
Python run catches this**: the notebook executed green both times, because the
failure is in JBrowse's render and only the screenshot sees it.

**Two new dependencies**, not yet added to `pyproject.toml`'s `scripts` extra
and they must be: `h5py` and `plotly` (3 packages: plotly, narwhals, packaging).
`plotly`'s `FigureWidget` is itself built on anywidget, which is already the
only runtime dep.

**What was ruled out, so nobody re-treads it.** `snapatac2` pulls 29 packages
(MACS3, polars, pyarrow, scikit-learn, kaleido...) and **is not needed**: the
annotated `.h5ad` is spec-compliant, so `h5py` reads `obsm/X_umap`,
`obs/cell_type` and `obs/index` out of the 837 MB file in 7 range requests and
about 3 seconds, downloading none of it. `anndata` is not the light alternative
it used to be either — 25 packages, and `read_h5ad(backed="r")` backs only `X`
while `obsm` loads eagerly, which would materialize a 74M-nnz fragment matrix.

**Measured, so the interactivity claim is not a guess.** Fragments come from
10x's tabix-indexed `atac_pbmc_5k_nextgem_fragments.tsv.gz` (1 GB, remote): one
30 kb window is 0.27s and 1171 fragments, and each reselection after that is
1-50 ms of numpy over what is already in memory. htslib needs
`CURL_CA_BUNDLE=certifi.where()` set before `import pysam` or it fails with
`Libcurl reported error 77`.

**The built-in control, which is the reason the notebook is worth having.** At
MS4A1 (`chr11:60,450,000-60,480,000`, hg38) the two B rows peak at 125 and 267
cut sites, while CD14 Mono peaks at 14 off _more_ cells (658) and NK at 5. So
the track is following the selection rather than its size, and a reader can see
that by lassoing.

Unverified: whether the fixed figure actually shows the B-cell peak. That is the
next thing to look at.

## marimo

`examples/marimo/large_wiggle.py` is the reactive twin of notebook 13: reading
`view.location` in a cell _is_ the subscription, so the `observe`/callback
wiring and the explicit clear of the previous track all disappear. It is
hand-written `.py`, not generated, and is linted and formatted like the rest of
the package — `examples/*.ipynb` is what ruff skips, not `examples/`.
`marimo export html <file>` runs every cell headless, which is a better widget
check than nbconvert.

**marimo WASM (`export html-wasm`) was tried and abandoned.** Wheel builds,
micropip installs it, marimo boots — widget never renders, no error surfaced.
Blocked for real deployment anyway (not on PyPI). If anyone retries: serve with
`Cross-Origin-Opener-Policy: same-origin` +
`Cross-Origin-Embedder-Policy: require-corp`; `micropip.install("./x.whl")`
resolves against Pyodide's virtual CWD not the page origin (use an absolute
URL); and Pyodide runs in a **web worker**, so its errors never reach
`page.on('console')` — attach via `page.on('workercreated')`.
