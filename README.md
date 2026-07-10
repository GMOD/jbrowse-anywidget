# jbrowse-anywidget

JBrowse 2 linear genome view as an [anywidget](https://anywidget.dev), drawn on
the GPU (WebGPU, with WebGL and Canvas2D fallbacks). One bundle renders in
Jupyter, JupyterLab, VS Code, Colab, and marimo, with two-way sync of the
visible region between Python and the view.

This is the modern replacement for the Dash-based `jbrowse-jupyter` +
`dash_jbrowse` stack: no Dash server, no `dash-generate-components`, no webpack —
just a Vite-bundled ESM file loaded by anywidget.

## Try it in Colab

- Quickstart — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cmdcolin/jbrowse-anywidget/blob/main/examples/01_quickstart.ipynb)
- DataFrame → track (analysis-ready) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cmdcolin/jbrowse-anywidget/blob/main/examples/02_dataframe_analysis.ipynb)
- GPU alignments (BAM/CRAM) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cmdcolin/jbrowse-anywidget/blob/main/examples/03_alignments.ipynb)
- Multi-sample variants — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cmdcolin/jbrowse-anywidget/blob/main/examples/04_multisample_variants.ipynb)
- Call CNVs → view them (ERBB2 amplification) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cmdcolin/jbrowse-anywidget/blob/main/examples/05_cnv_calling.ipynb)
- Selection scan (Fst) → view the sweep (LCT) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cmdcolin/jbrowse-anywidget/blob/main/examples/06_popgen_selection.ipynb)

The last two are the core loop — **run an analysis in Python, load the result
onto the genome** — with everything computed in the notebook (no downloads).

## Develop

The JS bundle links the GPU-rendered `@jbrowse/react-linear-genome-view2` (v4)
directly from a sibling `jbrowse-components` checkout so it tracks the latest
work — see the `link:` dependency in `package.json`. Clone that repo next to this
one:

```bash
git clone https://github.com/GMOD/jbrowse-components ../jbrowse-components
pnpm install        # resolves the link: dependency to ../jbrowse-components
pnpm build          # writes jbrowse_anywidget/static/index.js
pip install -e ".[dev]"
```

`pnpm dev` rebuilds the bundle on change. Then open a notebook from `examples/`.
Regenerate the notebooks with `python scripts/build_examples.py`.

## API sketch

The interface is JBrowse's own config. Assemblies, tracks, and sessions are the
same [JSON-like dicts](https://jbrowse.org/jb2/docs/config_guide/) JBrowse uses
everywhere, handed straight to the view — so every track type and adapter works
with no Python wrapper to keep in sync.

```python
from jbrowse_anywidget import LinearGenomeView, make_assembly

view = LinearGenomeView(
    assembly=make_assembly("hg38", ".../hg38.fa.gz"),
    location="10:29,838,565..29,838,850",
)

# any JBrowse track config — the same JSON you'd put in a config file
view.add_track({
    "type": "AlignmentsTrack",
    "trackId": "reads",
    "name": "reads",
    "assemblyNames": ["hg38"],
    "adapter": {"type": "CramAdapter", "uri": ".../reads.cram"},  # GPU pileup
})

# the one thing JSON can't do: an in-memory DataFrame becomes a track, no file
view.add_features(df, name="my peaks", color="jexl:get(feature,'score')>0?'red':'blue'")

view            # display
view.location   # read back the user's current region
```

Python adds only what config JSON can't express itself: `add_features`
(DataFrame/list of dicts → track) and `make_assembly` (a little assembly
boilerplate). Everything else is `add_track(<config dict>)` — or pass whole
`tracks=[...]` / `default_session={...}` configs to the constructor. Tracks are
opened in the view automatically; removing one from `view.tracks` closes it.

## Publishing (to make the Colab links live)

The built JS bundle in `jbrowse_anywidget/static/` is committed, so the package
installs with no JS toolchain:

```bash
pnpm build                       # refresh the bundle after any src/ change
python -m build                  # sdist + wheel (includes static/)
twine upload dist/*              # -> PyPI, so `pip install jbrowse-anywidget` works
```

Then push to `github.com/cmdcolin/jbrowse-anywidget` and the Colab badges resolve.
Colab renders the widget because each notebook enables the custom widget
manager (`output.enable_custom_widget_manager()`).

## Status

Prototype consolidating two earlier experiments
(`experiments/jbrowse_lgv_widget`, `dont_care/jb2anywidget`), now bundling the
GPU-rendered v4 view. All six notebooks in `examples/` are verified to execute
headless, and their track configs (bigwig, DataFrame, alignments, variants, CNV
segments, Fst windows) are verified to render in a headless browser.

Next: a matching synteny/dotplot widget (a different view type, so a separate
component), a binary fast-path for large feature sets, and an R wrapper over the
same bundle.
