# jbrowse-anywidget

JBrowse 2 linear genome view as an [anywidget](https://anywidget.dev), drawn on
the GPU (WebGPU, with WebGL and Canvas2D fallbacks). One bundle renders in
Jupyter, JupyterLab, VS Code, Colab, and marimo, with two-way sync of the
visible region between Python and the view.

This is the modern replacement for the Dash-based `jbrowse-jupyter` +
`dash_jbrowse` stack: no Dash server, no `dash-generate-components`, no webpack —
just a Vite-bundled ESM file loaded by anywidget.

## Try it in Colab

- Quickstart — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/01_quickstart.ipynb)
- DataFrame → track (analysis-ready) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/02_dataframe_analysis.ipynb)
- GPU alignments (BAM/CRAM) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/03_alignments.ipynb)
- Multi-sample variants — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/04_multisample_variants.ipynb)
- Call CNVs → view them (ERBB2 amplification) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/05_cnv_calling.ipynb)
- Between-population selection scan (Fst) → view the sweep (Drosophila Cyp6g1, real DEST data) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/06_popgen_selection.ipynb)
- Differential expression → view — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/07_differential_expression.ipynb)
- Easy human data (hosted assembly hub) — [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/08_hosted_assembly_hub.ipynb)

05–07 are the core loop — **run an analysis in Python, load the result onto the
genome** — with everything computed in the notebook (no downloads).

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

A whole view is one declarative call. A `tracks=[...]` entry can be a bare
data-file URL — its track type and adapter are inferred from the extension — and
`assembly="hg38"` fetches a hosted genome by name, so nothing but URLs is needed:

```python
from jbrowse_anywidget import LinearGenomeView

view = LinearGenomeView(
    assembly="hg38",
    location="10:29,838,565..29,838,850",
    tracks=[
        "https://.../ncbiRefSeq.sort.gff.gz",
        "https://.../phyloP100way.bw",
        "https://.../reads.cram",
    ],
)
view            # display
view.location   # read back the user's current region
```

The track type and adapter are inferred from the file extension by the view
itself — using JBrowse's own format plugins, the same inference the "Add track"
flow uses — so there's no extension table in Python to fall behind: `.bam`,
`.cram`, `.bw`/`.bigwig`, `.bb`/`.bigbed`, `.vcf`(`.gz`), `.gff`(`.gz`)/`.gff3`(`.gz`),
`.gtf`(`.gz`), `.bed`(`.gz`), `.hic`, and anything else a bundled plugin knows.
The index defaults to the conventional sibling (`.bai`/`.crai`/`.tbi`); when your
index lives elsewhere — or is a `.csi` index — give a `(url, index)` pair instead
of a bare string. `assemblyNames` is filled from the view's assembly, so a
`tracks=[...]` list needs no per-track boilerplate.

`track(uri, name=..., ...)` is the same thing made explicit — reach for it to set
a display name or extra config. It returns a loose spec (`{"uri": ...}` plus
whatever you pass) that the view expands, so anything past the defaults (colors,
display settings, even a `type=` override) is just a keyword you add — the same
JBrowse config JSON, not a Python wrapper around it:

```python
from jbrowse_anywidget import track

view.add_track(track("https://.../reads.cram", name="Tumor"))
```

Under the shorthand it's all JBrowse's own config. Assemblies, tracks, and
sessions are the same [JSON-like dicts](https://jbrowse.org/jb2/docs/config_guide/)
JBrowse uses everywhere, handed straight to the view, so any track type or
adapter `track()` doesn't cover you write as a dict — the exact JSON from a
config file:

```python
view.add_track({
    "type": "AlignmentsTrack", "trackId": "reads", "name": "reads",
    "assemblyNames": ["hg38"],
    "adapter": {"type": "CramAdapter", "uri": ".../reads.cram"},
})

# the one thing JSON can't do: an in-memory DataFrame becomes a track, no file
view.add_features(df, name="my peaks", color="jexl:get(feature,'score')>0?'red':'blue'")
```

Python adds only what config JSON can't express itself: `track` (URI → loose
spec the view expands), `add_features` (DataFrame/list of dicts → track) and
`make_assembly` (a little assembly boilerplate). Everything else is `add_track(<config dict>)` — or
pass whole `tracks=[...]` / `default_session={...}` configs to the constructor.
Tracks are opened in the view automatically; removing one from `view.tracks`
closes it.

For a custom genome, `assembly=` also accepts a bare sequence-file URL
(`assembly=".../genome.fa.gz"`, or a `.2bit`) — the view builds the assembly from
it, deriving the name from the file — so `make_assembly` is only needed to add
reference-name aliases or a non-sibling index.

For human/model-organism data, `fetch_hub("hg38")` (also `hg19`, `mm10`, a
GenArk `GCA_...`) returns a ready, CORS-enabled assembly config from
genomes.jbrowse.org — sequence, refName aliases, cytobands, a gene-name search
index, and a catalog of hosted tracks — as plain JSON you pass in. Because the
assembly carries refName aliases, your own tracks line up even when they name
chromosomes differently (`chr17` vs `17`). See `examples/08_hosted_assembly_hub.ipynb`.

## Publishing (to make the Colab links live)

The built JS bundle in `jbrowse_anywidget/static/` is committed, so the package
installs with no JS toolchain:

```bash
pnpm build                       # refresh the bundle after any src/ change
python -m build                  # sdist + wheel (includes static/)
twine upload dist/*              # -> PyPI, so `pip install jbrowse-anywidget` works
```

Then push to `github.com/GMOD/jbrowse-anywidget` and the Colab badges resolve.
Colab renders the widget because each notebook enables the custom widget
manager (`output.enable_custom_widget_manager()`).

## Status

Prototype consolidating two earlier experiments
(`experiments/jbrowse_lgv_widget`, `dont_care/jb2anywidget`), now bundling the
GPU-rendered v4 view. All eight notebooks in `examples/` are verified to execute
headless, and their track configs (bigwig, DataFrame, alignments, variants, CNV
segments, Fst windows, differential expression, hosted hub tracks) are verified
to render in a headless browser.

Next: a matching synteny/dotplot widget (a different view type, so a separate
component), a binary fast-path for large feature sets, and an R wrapper over the
same bundle.
