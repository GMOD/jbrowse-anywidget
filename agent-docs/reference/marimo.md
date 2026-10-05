# marimo

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
