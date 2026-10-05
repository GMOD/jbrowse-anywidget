# Traps

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

**`score` is the magic column.** `features_track` builds a `QuantitativeTrack` —
a real wiggle with a value axis — only when a column is literally named `score`.
`depth`/`signal` render as boxes. `quantitative=` overrides. Any other keyword
is track config merged on top; `displays=[{"type": "LinearMarkDisplay", ...}]`
is how a column becomes a plot with an axis, and notebooks 06, 07 and 09 use it.

**The bundle is what draws the grammar.** The mark display's threshold scales,
reference rules and axis titles landed in the monorepo on 2026-09-20/21; a
bundle built before that renders the same config with a viridis ramp, no rules
and no title, and every readiness signal says done. Rebuild before judging a
figure that ignores part of its encoding.

**Screenshot images are timing-dependent.** Re-rendering produces byte-different
PNGs even with no code change. Don't commit regenerated figures in a change that
isn't about them; `git checkout images/` after a verification run.
