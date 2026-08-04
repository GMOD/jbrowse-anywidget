# jbrowse-anywidget

JBrowse 2 linear genome view as an [anywidget](https://anywidget.dev), drawn on
the GPU (WebGPU, with WebGL and Canvas2D fallbacks). One bundle renders in
Jupyter, JupyterLab, VS Code, Colab, and marimo, with two-way sync of the
visible region between Python and the view.

This is the modern replacement for the Dash-based `jbrowse-jupyter` +
`dash_jbrowse` stack: no Dash server, no `dash-generate-components`, no webpack
— just a Vite-bundled ESM file loaded by anywidget.

## Install

```bash
pip install jbrowse-anywidget
```

The JS bundle ships prebuilt inside the wheel, so there is no Node toolchain to
set up. Until the first PyPI release, install from git:

```bash
pip install "jbrowse-anywidget @ git+https://github.com/GMOD/jbrowse-anywidget"
```

```python
from jbrowse_anywidget import LinearGenomeView

LinearGenomeView(assembly="hg38", location="chr1:1,000,000..1,100,000")
```

## What it looks like

Every figure below is rendered headless from the built bundle by
`scripts/screenshot_examples.mjs`, out of the declarative config in
`scripts/gen_screenshot_specs.py` — so they show what the notebooks actually
produce, not a mock-up.

A linear view with a conservation bigWig
([quickstart notebook](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/01_quickstart.ipynb)):

![quickstart: assembly + phyloP bigWig](images/01_quickstart.png)

A bioframe interval result dropped onto the genome — CpG islands colored by GC%,
plus their shores
([notebook](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/02_dataframe_analysis.ipynb)):

![bioframe result: CpG islands colored by GC%, with their shores](images/02_bioframe.png)

GPU-rendered CRAM alignments over BRCA1, from a hub assembly named by string
([notebook](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/03_alignments.ipynb)):

![NA12878 exome CRAM at BRCA1, coverage plus reads](images/03_alignments.png)

Multi-sample structural variants, one row per sample, colored by cohort
([notebook](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/04_multisample_variants.ipynb)):

![multi-sample SV band display colored by population](images/04_variants.png)

Four E. coli strains compared with an all-vs-all PAF, and the same alignment as
a dotplot — both from `JBrowseApp`
([notebook](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/11_synteny_ecoli.ipynb)):

![synteny: four E. coli strains compared with an all-vs-all PAF](images/11_synteny.png)

![dotplot of K12 vs Sakai from the same PAF](images/12_dotplot.png)

## Try it in Colab

- Quickstart —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/01_quickstart.ipynb)
- bioframe result → track (real CpG islands + shores) —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/02_dataframe_analysis.ipynb)
- GPU alignments (BAM/CRAM) —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/03_alignments.ipynb)
- Multi-sample variants —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/04_multisample_variants.ipynb)
- Read depth from a BAM with pysam (NA12878 exome over BRCA1) —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/05_bam_coverage.ipynb)
- Between-population selection scan (Fst) → view the sweep (Drosophila Cyp6g1,
  real DEST data) —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/06_popgen_selection.ipynb)
- Differential expression → view —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/07_differential_expression.ipynb)
- Easy human data (hosted assembly hub) —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/08_hosted_assembly_hub.ipynb)
- Interactive controls — a slider that re-runs the analysis —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/09_interactive_controls.ipynb)
- Region-reactive — recompute only what's on screen as you pan —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/10_region_reactive.ipynb)
- Compare genomes — four E. coli strains in a linear synteny view —
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/11_synteny_ecoli.ipynb)

05–07 are the core loop — **run an analysis in Python, load the result onto the
genome** — using the tools scientists already reach for (pysam, bioframe,
scipy/statsmodels) on real data. 09–10 close the loop the other way: a widget
control or a pan in the view drives Python to **recompute and repaint**, live.

## Develop

The JS bundle links the GPU-rendered `@jbrowse/react-linear-genome-view2` (v4)
directly from a sibling `jbrowse-components` checkout so it tracks the latest
work — see the `link:` dependency in `package.json`. Clone that repo next to
this one:

```bash
git clone https://github.com/GMOD/jbrowse-components ../jbrowse-components
pnpm install        # resolves the link: dependency to ../jbrowse-components
pnpm build          # writes static/index.js (lgv) and static/app.js (full app)
pip install -e ".[dev]"
```

`pnpm dev` rebuilds the bundle on change, and `pnpm typecheck` runs tsc. Then
open a notebook from `examples/`. `pytest` covers the Python config builders and
the Python <-> JS trait contract; neither it nor the bundle build needs network.
`ruff check` and `ruff format` lint the Python, `pnpm format` runs prettier over
everything else (all three run in CI); the generated notebooks and the built
bundle are excluded from both.

Regenerating the notebooks and figures needs the extra script dependencies
(`pip install -e ".[dev,scripts]"`):

```bash
python scripts/build_examples.py       # rewrite examples/*.ipynb
python scripts/gen_screenshot_specs.py # -> scripts/screenshot_specs.json
node scripts/screenshot_examples.mjs   # -> images/*.png (puppeteer, resolved
                                       #    from the sibling checkout)
```

## API sketch

A whole view is one declarative call. A `tracks=[...]` entry can be a bare
data-file URL — its track type and adapter are inferred from the extension — and
`assembly="hg38"` fetches a hosted genome by name, so nothing but URLs is
needed:

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
`.cram`, `.bw`/`.bigwig`, `.bb`/`.bigbed`, `.vcf`(`.gz`),
`.gff`(`.gz`)/`.gff3`(`.gz`), `.gtf`(`.gz`), `.bed`(`.gz`), `.hic`, and anything
else a bundled plugin knows. The index defaults to the conventional sibling
(`.bai`/`.crai`/`.tbi`); when your index lives elsewhere — or is a `.csi` index
— give a `(url, index)` pair instead of a bare string. `assemblyNames` is filled
from the view's assembly, so a `tracks=[...]` list needs no per-track
boilerplate.

To set a display name, or anything else, hand over a dict instead of the bare
string. It is merged onto the inferred config, so the adapter, the index
location and `assemblyNames` still come for free, and anything past the defaults
— colors, display settings, even a `type` override — is just another key:

```python
view.add_track({"uri": "https://.../reads.cram", "name": "Tumor"})
```

There is no Python wrapper for this because there is nothing to wrap: it's
JBrowse's own config. Assemblies, tracks, and sessions are the same
[JSON-like dicts](https://jbrowse.org/jb2/docs/config_guide/) JBrowse uses
everywhere, handed straight to the view — so a track type or adapter the
shorthand doesn't infer is written out in full, exactly as it would appear in a
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

That is the whole design. Python adds only what JSON cannot express itself — a
DataFrame (`add_features`), bytes from this kernel (`add_local_file`), and a
network fetch (`fetch_hub`, `plugin`). Everything else is
`add_track(<config dict>)`, or whole `tracks=[...]` / `default_session={...}`
configs on the constructor. Nothing here has to grow when JBrowse gains a track
type, an adapter, or a display. Tracks are opened in the view automatically;
removing one from `view.tracks` closes it.

For a custom genome, `assembly=` also accepts a bare sequence-file URL
(`assembly=".../genome.fa.gz"`, or a `.2bit`) — the view builds the assembly
from it, deriving the name from the file. To name it yourself, or to add
reference-name aliases, write the flat shorthand dict; there is no Python
builder because core expands this itself:

```python
LinearGenomeView(assembly={
    "name": "hg19",
    "uri": "https://.../hg19.fa.gz",
    "refNameAliases": {"uri": "https://.../hg19_aliases.txt"},
})
```

For human/model-organism data, `fetch_hub("hg38")` (also `hg19`, `mm10`, a
GenArk `GCA_...`) returns a ready, CORS-enabled assembly config from
genomes.jbrowse.org — sequence, refName aliases, cytobands, a gene-name search
index, and a catalog of hosted tracks — as plain JSON you pass in. Because the
assembly carries refName aliases, your own tracks line up even when they name
chromosomes differently (`chr17` vs `17`). See
`examples/08_hosted_assembly_hub.ipynb`.

## Plots (GWAS Manhattan, and more)

A track's _display_ can plot its data — a
[`GWASTrack`](https://jbrowse.org/jb2/docs/config/gwasadapter/) with a
[`LinearManhattanDisplay`](https://jbrowse.org/jb2/docs/config/linearmanhattandisplay/)
renders genome-wide summary statistics as a Manhattan plot right in the linear
view. The plot is just a `displays` block on the track config, so it needs no
special widget. The adapter's `uri` shorthand finds the `.tbi` index for you,
and JBrowse fills in `displayId`:

```python
LinearGenomeView(
    assembly="hg19",
    location="2",
    tracks=[{
        "type": "GWASTrack",
        "trackId": "gwas_track",
        "name": "GWAS",
        "adapter": {
            "type": "GWASAdapter",
            "scoreColumn": "neg_log_pvalue",
            "uri": ".../summary_stats.txt.gz",
        },
        "displays": [{"type": "LinearManhattanDisplay", "height": 250}],
    }],
)
```

![GWAS summary statistics drawn as a Manhattan plot across chromosome 2](images/13_manhattan.png)

JBrowse's [config guide](https://jbrowse.org/jb2/docs/config_guide/) and the
per-type [config docs](https://jbrowse.org/jb2/docs/config/) cover many such
display-driven plots (Manhattan/LD, Hi-C matrices, multi-wiggle, sashimi) — each
is a track config plus a `displays` choice.

## Comparing genomes (synteny, dotplots)

`LinearGenomeView` is one linear view. For comparative genomics, `JBrowseApp`
drives the full app from a declarative `views=[...]` list — each entry a
`{"type", "init"}` dict (the same shape as JBrowse Web's
[`?session=spec-…` URLs](https://jbrowse.org/jb2/docs/urlparams/); the `init`
fields come from the view's
[state-model docs](https://jbrowse.org/jb2/docs/models/linearsyntenyview/)):

```python
from jbrowse_anywidget import JBrowseApp

JBrowseApp(
    assemblies=[
        {"name": "hg38", "uri": hg38_fa},
        {"name": "mm39", "uri": mm39_fa},
    ],
    tracks=[
        {
            "type": "SyntenyTrack",
            "trackId": "hg38_mm39",
            "name": "hg38 vs mm39",
            "assemblyNames": ["hg38", "mm39"],
            "adapter": {
                "type": "PAFAdapter",
                "targetAssembly": "hg38",
                "queryAssembly": "mm39",
                "uri": "hg38_mm39.paf",
            },
        }
    ],
    views=[
        {
            "type": "LinearSyntenyView",
            "init": {
                # a comparative view's panels are {"assembly", "loc"?} per side
                "views": [{"assembly": "hg38"}, {"assembly": "mm39"}],
                "tracks": ["hg38_mm39"],
            },
        }
    ],
)
```

Longer than a builder call would be, and deliberately so: this is the JBrowse
vocabulary, so it transfers unchanged to a `config.json`, to the state-model
docs, and to a `?session=spec-…` URL — and a view type JBrowse gains, or one a
runtime plugin registers, opens with nothing added to this package. Change
`"type"` to `"DotplotView"` for the same alignment as a dotplot.

It loads a separate, larger bundle (the full app), so the single-view
`LinearGenomeView` stays lean.

`plugins=[...]` loads JBrowse plugins at runtime by name from the
[plugin store](https://jbrowse.org/jb2/plugin_store/), which is how view types
that don't ship in the bundle become available. A plugin's view has its own init
fields, so open it with the generic `view()` rather than a Python wrapper that
would fall out of step with the plugin:

```python
from jbrowse_anywidget import JBrowseApp, view

JBrowseApp(
    assemblies=[hg38],
    plugins=["Protein3d"],
    views=[view("ProteinView", url=".../AF-P04637-F1-model_v6.cif", height=600)],
)
```

## Publishing (to make the Colab links live)

The built JS bundle in `jbrowse_anywidget/static/` is committed, so the package
installs with no JS toolchain:

```bash
pnpm build                       # refresh the bundle after any src/ change
python -m build                  # sdist + wheel (includes static/)
twine upload dist/*              # -> PyPI, so `pip install jbrowse-anywidget` works
```

Then push to `github.com/GMOD/jbrowse-anywidget` and the Colab badges resolve.
Colab renders the widget because each notebook enables the custom widget manager
(`output.enable_custom_widget_manager()`).

## Status

Prototype, bundling the GPU-rendered v4 view. The eleven notebooks in
`examples/` run top-to-bottom in Colab; their analyses use the tools scientists
already work in (bioframe intervals, pysam coverage, scipy/statsmodels DE, DEST
Fst windows) on real data, and their track configs render in a headless browser.
Two of them close the loop the other way — a slider and a pan in the view drive
Python to recompute and repaint.

Synteny and dotplot views ship today via `JBrowseApp` (see above), and
[JBrowseR](https://github.com/GMOD/JBrowseR) wraps the same bundle for R. Next:
a binary fast-path for large feature sets.
