# Examples

Each notebook opens in Colab and runs top-to-bottom (it installs the package
from this repo, so no local setup is needed).

## Basics

- **[01 · Quickstart](01_quickstart.ipynb)** — an assembly, a track by URL, and
  two-way location sync between Python and the view.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/01_quickstart.ipynb)
- **[02 · bioframe → track](02_dataframe_analysis.ipynb)** — real UCSC CpG
  islands, one bioframe operation (their shores), both on the genome; any
  bioframe/pandas frame is one `add_features` call away.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/02_dataframe_analysis.ipynb)
- **[03 · GPU alignments](03_alignments.ipynb)** — a BAM/CRAM pileup on the GPU,
  colored by pair orientation, soft-clips shown.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/03_alignments.ipynb)
- **[04 · Multi-sample variants](04_multisample_variants.ipynb)** — a
  multi-sample VCF as a per-sample band and as a genotype matrix.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/04_multisample_variants.ipynb)

## Run an analysis, load the result onto the genome

Compute a result with the tools you already use, then load it with
`add_features` — the core reason to have a genome browser in a notebook.

- **[05 · Read depth from a BAM (pysam) → view](05_bam_coverage.ipynb)** — real
  1000 Genomes NA12878 exome; pysam counts coverage over _BRCA1_, binned onto
  the genome (only the index and the region are fetched, not the 17 GB BAM).
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/05_bam_coverage.ipynb)
- **[06 · Selection scan → view](06_popgen_selection.ipynb)** — a windowed Fst
  scan between two _Drosophila_ populations; the sweep lands over _Cyp6g1_.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/06_popgen_selection.ipynb)
- **[07 · Differential expression → view](07_differential_expression.ipynb)** —
  counts → log2 fold-change / t-test → a gene track colored by call.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/07_differential_expression.ipynb)

## Data access

- **[08 · Hosted assembly hub](08_hosted_assembly_hub.ipynb)** — `fetch_hub`
  pulls a fully configured, CORS-enabled human assembly (sequence, refName
  aliases, cytobands, gene search, a hosted-track catalog); navigate by gene
  name.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/08_hosted_assembly_hub.ipynb)

## Close the loop: the view drives Python

The visible region and control widgets sync back to the kernel, so an
interaction can **re-run the analysis** and repaint the track live.

- **[09 · Interactive controls](09_interactive_controls.ipynb)** — an
  `ipywidgets` slider sets a differential-expression significance threshold;
  moving it reclassifies every gene in Python and repaints the track.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/09_interactive_controls.ipynb)
- **[10 · Region-reactive](10_region_reactive.ipynb)** — observe `location` and
  recompute pysam coverage (real NA12878 exome) only over the window in view, at
  a bin size that follows the zoom; nothing is precomputed genome-wide.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/10_region_reactive.ipynb)

## Comparing genomes

- **[11 · Synteny (four E. coli strains)](11_synteny_ecoli.ipynb)** —
  `JBrowseApp` stacks four assemblies tied by one all-vs-all minimap2 PAF, the
  blocks each pair shares drawn between the rows.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/11_synteny_ecoli.ipynb)

## Scale

- **[12 · Large results](12_large_data.ipynb)** — every NCBI RefSeq exon in the
  human genome (2.1M features). Inlined with `add_features` that is ~207 MB of
  JSON; written as a tabix file and pushed with `add_local_file` it is 3.9 MB,
  read by byte range, with no web server. Also writes a bigWig.
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/12_large_data.ipynb)
- **[13 · Large signal (wiggles)](13_large_wiggle.ipynb)** — the three routes
  for quantitative data, measured against the same chr1 track: inlined (~233
  MB), as a bigWig with zoom levels (21 MB, crosses once), or recomputed per
  region (~9–148 KB per view, _unlimited_ underlying data).
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/13_large_wiggle.ipynb)

## marimo

The widget works in [marimo](https://marimo.io) too, via `mo.ui.anywidget`.

- **[Large signal, reactively](marimo/large_wiggle.py)** — the reactive twin
  of 13. In Jupyter, recomputing for the visible region needs
  `view.observe(handler, "location")`, a callback, and an explicit clear of the
  previous track. In marimo a cell that _reads_ `view.location` re-runs when it
  changes, so the same thing is one cell with no wiring at all.

```bash
marimo edit examples/marimo/large_wiggle.py
```

marimo is worth reaching for exactly where reactivity is the point — anything
driven by the view's location or a control. For everything else the Jupyter
notebooks stay the better on-ramp, because Colab runs them in one click and
marimo notebooks are `.py` files you have to check out first. (They are also
plain Python, so unlike the `.ipynb` files they diff, lint, and need no
generator.)

The `.ipynb` notebooks are generated by
[`../scripts/build_examples.py`](../scripts/build_examples.py) — edit that, not
the `.ipynb` files. The marimo notebooks are their own source.
