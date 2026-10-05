# Notebook 14 (scATAC UMAP lasso) is written and runs; its figure is stale

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
