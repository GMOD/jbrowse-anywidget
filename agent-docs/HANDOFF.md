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
`localFiles.test.ts`.

**`score` is the magic column.** `add_features` builds a `QuantitativeTrack` — a
real wiggle with a value axis — only when a column is literally named `score`.
`depth`/`signal` render as boxes. `quantitative=` overrides.

**Screenshot images are timing-dependent.** Re-rendering produces byte-different
PNGs even with no code change. Don't commit regenerated figures in a change that
isn't about them; `git checkout images/` after a verification run.

## Known broken / unresolved

- **No browser render job in CI.** `test.yml` builds and typechecks the bundle;
  nothing renders it. The harness exists (`scripts/screenshot_examples.mjs`) and
  is the only thing that exercises the blob read path, but it needs
  `gen_screenshot_specs.py` run first (specs are gitignored),
  `PUPPETEER_FROM=<workspace>/jbrowse-components/package.json`, and real network
  to jbrowse.org and UCSC — so it is the flaky one. Nightly-only would suit it.

## Work that exists but did not land

Tagged locally as **`wip/embedded-session-work`** (`bde1fd6`), cut before main
diverged, so it does _not_ apply cleanly — it predates the TypeScript entrypoint
migration and the generic `view()`. Treat it as a reference, not a patch:

- `examples/12_large_data.ipynb` — 2.1M NCBI RefSeq exons, measuring ~207MB
  inlined against 3.9MB as tabix. Executes clean.
- `examples/13_large_wiggle.ipynb` — the three routes for signal, measured on
  one chr1 track: inlined ~233MB, bigWig 21MB, recompute-per-region ~9–148KB
  _per view_ with no ceiling.
- `examples/marimo/large_wiggle.py` — the reactive case, where reading
  `view.location` in a cell _is_ the subscription, so the observe/callback
  wiring disappears. `marimo export html <file>` runs every cell headless, which
  is a better widget check than nbconvert. Verified working.

Both notebooks depend on `add_local_file`, which is on main, so they port with
only import/API updates.

**marimo WASM (`export html-wasm`) was tried and abandoned.** Wheel builds,
micropip installs it, marimo boots — widget never renders, no error surfaced.
Blocked for real deployment anyway (not on PyPI). If anyone retries: serve with
`Cross-Origin-Opener-Policy: same-origin` +
`Cross-Origin-Embedder-Policy: require-corp`; `micropip.install("./x.whl")`
resolves against Pyodide's virtual CWD not the page origin (use an absolute
URL); and Pyodide runs in a **web worker**, so its errors never reach
`page.on('console')` — attach via `page.on('workercreated')`.

## Correction to IDEAS.md

The "Verify the committed bundle in CI" entry says a CI job is blocked because
`pnpm install` can't run without the sibling checkout. That is not true — CI can
check the monorepo out alongside:

```yaml
- uses: actions/checkout@v4
  with: { path: jbrowse-anywidget }
- uses: actions/checkout@v4
  with: { repository: GMOD/jbrowse-components, path: jbrowse-components }
- run: pnpm install --frozen-lockfile=false
  working-directory: jbrowse-components # linked pkgs resolve react/mobx here
- run: pnpm install --frozen-lockfile=false
  working-directory: jbrowse-anywidget
- run: pnpm build
```

Worth running on a **nightly cron**, not just push/PR: the break is normally
caused by a monorepo commit, so no event in this repo would fire. The render job
needs `scripts/gen_screenshot_specs.py` first (specs are gitignored) and
`PUPPETEER_FROM=<workspace>/jbrowse-components/package.json`.
