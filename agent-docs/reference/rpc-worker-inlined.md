# The RPC worker is inlined, and it has to be

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
