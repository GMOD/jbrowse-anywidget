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

## The controller has no bulk setters any more

`setAssembly`, `setSession` and `setTracks` were removed from
`LinearGenomeViewController` upstream (2026-08-06). The first two were `destroy
and build again` spelled as methods; the third reconciled a track list, which
had to answer what it does to a track the user opened by hand (it closed it).

What that means here: `change:assembly` and `change:session` now call
the shell's `rebuild`, which is exactly what those setters did internally, so
nothing changed for a notebook. `change:tracks` is the one that needed work,
because a notebook drives it in a loop — `09_interactive_controls` sets
`view.tracks = []` and then adds one, twice per slider step, and a rebuild each
time would re-resolve the assembly and start a new RPC worker mid-drag. It now
diffs by trackId and calls `addTrack`/`removeTrack`, falling back to a rebuild
when any entry is a loose spec (no trackId to diff on). That is also better than
the setter was: only tracks this widget declared are closed, so one the user
opened by hand survives a re-run.

**`appliedTracks` is a WeakMap keyed by model, not a plain variable**, because
`defineWidget` takes the build and the handlers once at module scope and calls
them per rendered widget — a closure variable would be shared by two views in
one notebook.

`scripts/verify_track_updates.mjs` covers it in a real browser, on the nightly
render workflow. Note what it does NOT assert: DOM node identity. React
legitimately replaces the header's nodes when the track list changes, so an
identity check reads as a rebuild that never happened — it counts container
unmounts instead. That cost a debugging round; don't reintroduce it.

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
