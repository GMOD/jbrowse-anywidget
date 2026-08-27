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
read is covered by `scripts/screenshot_examples.mjs` (`05_local_file`, which
draws a tabix BED _and_ a bigWig — the bigWig is the strong one, since it can
only render if the blob is genuinely random-access) and by product-core's
`localFiles.test.ts`. The `render` workflow is what runs that harness in CI —
nightly, and by `workflow_dispatch` on demand. It is deliberately not on
push/PR: it needs real network and links against jbrowse-components `main`, so
it fails for reasons unrelated to the commit that triggered it. It fails the run
if any example never paints a canvas, and uploads the images as an artifact
either way. To run it locally: `python scripts/gen_screenshot_specs.py` (specs
are gitignored), then
`PUPPETEER_FROM=<workspace>/jbrowse-components/package.json node scripts/screenshot_examples.mjs`.

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

`scripts/verify_track_updates.mjs` covers it in a real browser, on the nightly
render workflow. Note what it does NOT assert: DOM node identity. React
legitimately replaces the header's nodes when the track list changes, so an
identity check reads as a rebuild that never happened — it counts container
unmounts instead. That cost a debugging round; don't reintroduce it.

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

Nothing outstanding.

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
