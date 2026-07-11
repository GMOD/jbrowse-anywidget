"""Regenerate the example notebooks in examples/.

Run: .venv/bin/python scripts/build_examples.py
Each notebook installs from PyPI only when the package isn't already importable,
so it runs unchanged in Colab and executes headless against a local editable
install for verification.
"""

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

INSTALL = """\
# Install only if not already available (e.g. in Colab). The GitHub install
# needs no JS toolchain — the built widget bundle is committed in the repo. A
# local editable install is used as-is. (Swap to `jbrowse-anywidget` once it's
# published to PyPI.)
try:
    import jbrowse_anywidget  # noqa: F401
except ImportError:
    %pip install -q "jbrowse-anywidget @ git+https://github.com/GMOD/jbrowse-anywidget" pandas numpy

# Colab requires this to render third-party (anywidget) widgets:
try:
    from google.colab import output

    output.enable_custom_widget_manager()
except ImportError:
    pass"""

COLAB = "https://colab.research.google.com/assets/colab-badge.svg"


def badge(path):
    href = f"https://colab.research.google.com/github/GMOD/jbrowse-anywidget/blob/main/examples/{path}"
    return f"[![Open In Colab]({COLAB})]({href})"


def save(name, cells):
    nb = new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    # Deterministic cell ids so regenerating only diffs cells that changed;
    # new_code_cell/new_markdown_cell otherwise mint a random id every run.
    stem = name.removesuffix(".ipynb")
    for i, cell in enumerate(nb.cells):
        cell["id"] = f"{stem}-{i}"
    with open(f"examples/{name}", "w") as f:
        nbf.write(nb, f)
    print("wrote examples/" + name)


# --- 01 quickstart ----------------------------------------------------------
save(
    "01_quickstart.ipynb",
    [
        new_markdown_cell(
            "# JBrowse 2 in a notebook — quickstart\n\n"
            + badge("01_quickstart.ipynb")
            + "\n\nA JBrowse 2 linear genome view rendered as an "
            "[anywidget](https://anywidget.dev), drawn on the GPU. Works in "
            "Jupyter, JupyterLab, VS Code, and Colab from a single bundle."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## An assembly and a view\n\n"
            "`make_assembly` builds the reference-sequence config for an "
            "indexed (here bgzipped) FASTA. `location` sets the opening region."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly, track\n\n'
            'hg38 = make_assembly(\n'
            '    "hg38",\n'
            '    "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",\n'
            '    aliases=["GRCh38"],\n'
            ')\n\n'
            'view = LinearGenomeView(assembly=hg38, location="10:29,838,565..29,838,850")\n'
            'view'
        ),
        new_markdown_cell(
            "## Add a track\n\n"
            "A bare data-file URL is a track — its type and adapter are inferred "
            "from the extension, the way [@jbrowse/img](https://jbrowse.org/jb2/docs/jbrowse-img)'s "
            "`--bam`/`--bigwig`/`--cram` flags work for the CLI. `track(uri, name=...)` "
            "is the same expansion with a display name and room for extra config; "
            "`assemblyNames` is filled in from the view's assembly. Here, a "
            "conservation bigwig. Any non-default setting (color, height, ...) is "
            "a key you add to the returned config dict."
        ),
        new_code_cell(
            'view.add_track(\n'
            '    track(\n'
            '        "https://hgdownload.cse.ucsc.edu/goldenpath/hg38/phyloP100way/hg38.phyloP100way.bw",\n'
            '        name="phyloP100way",\n'
            '    )\n'
            ')'
        ),
        new_markdown_cell(
            "## Drive the view from Python, read it back\n\n"
            "Setting `location` navigates the view; after panning in the UI, "
            "reading `location` returns the user's current region (two-way sync)."
        ),
        new_code_cell('view.location = "1:1,000,000..1,050,000"'),
        new_code_cell("view.location  # updates as you pan/zoom in the view above"),
    ],
)

# --- 02 dataframe -----------------------------------------------------------
save(
    "02_dataframe_analysis.ipynb",
    [
        new_markdown_cell(
            "# Analysis-ready: a DataFrame becomes a track\n\n"
            + badge("02_dataframe_analysis.ipynb")
            + "\n\nThe point of a notebook genome browser is to **see the "
            "result of a computation in genomic context**. `add_features` turns "
            "a pandas DataFrame straight into a track — no file written, no "
            "server."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## Compute something\n\n"
            "A stand-in analysis: sliding-window mean of a synthetic signal, "
            "producing scored intervals. Swap this for your real pipeline "
            "output — peaks, coverage, methylation — as long as it has "
            "`refName`/`chrom`, `start`, `end` columns."
        ),
        new_code_cell(
            'import numpy as np\n'
            'import pandas as pd\n\n'
            'rng = np.random.default_rng(0)\n'
            'start = 29_838_000\n'
            'positions = np.arange(start, start + 2000)\n'
            'signal = rng.normal(size=positions.size).cumsum()\n\n'
            'win = 100\n'
            'rows = []\n'
            'for i in range(0, positions.size - win, win):\n'
            '    rows.append(\n'
            '        {\n'
            '            "chrom": "10",\n'
            '            "start": int(positions[i]),\n'
            '            "end": int(positions[i + win]),\n'
            '            "score": float(signal[i : i + win].mean()),\n'
            '        }\n'
            '    )\n\n'
            'windows = pd.DataFrame(rows)\n'
            'windows.head()'
        ),
        new_markdown_cell("## Visualize it in genomic context"),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
            'hg38 = make_assembly(\n'
            '    "hg38",\n'
            '    "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",\n'
            '    aliases=["GRCh38"],\n'
            ')\n'
            'view = LinearGenomeView(assembly=hg38, location="10:29,838,000..29,840,000")\n'
            'view.add_features(windows, name="windowed mean")\n'
            'view'
        ),
        new_markdown_cell(
            "Every column beyond `refName`/`start`/`end` is carried onto the "
            "feature, so `score` (and any annotations you add) show up in the "
            "feature details and can drive rendering."
        ),
        new_markdown_cell(
            "## Color by a computed value\n\n"
            "A feature's own columns are addressable from a "
            "[jexl](https://jbrowse.org/jb2/docs/config_guides/customizing_feature_colors/) "
            "color expression, so the track can encode `score` directly — high "
            "windows in red, low in blue."
        ),
        new_code_cell(
            'colored = LinearGenomeView(\n'
            '    assembly=hg38, location="10:29,838,000..29,840,000"\n'
            ')\n'
            'colored.add_features(\n'
            '    windows,\n'
            '    name="windowed mean (colored)",\n'
            '    color="jexl:get(feature,\'score\') > 0 ? \'#c62828\' : \'#1565c0\'",\n'
            ')\n'
            'colored'
        ),
    ],
)

# --- 03 alignments ----------------------------------------------------------
save(
    "03_alignments.ipynb",
    [
        new_markdown_cell(
            "# GPU alignments: a BAM/CRAM pileup\n\n"
            + badge("03_alignments.ipynb")
            + "\n\nAn `AlignmentsTrack` over a BAM or CRAM draws its pileup and "
            "coverage on the GPU, so deep regions stay smooth to pan and zoom. "
            "Here, the 1000 Genomes NA12878 exome (CRAM) over GRCh38."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## Assembly and alignments\n\n"
            "The CRAM's `.crai` index and its reference sequence are resolved "
            "automatically from the `uri`, so the adapter is just the URL."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
            'grch38 = make_assembly(\n'
            '    "GRCh38",\n'
            '    "https://s3.amazonaws.com/jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    aliases=["hg38"],\n'
            ')\n\n'
            'cram = (\n'
            '    "https://s3.amazonaws.com/jbrowse.org/genomes/GRCh38/alignments/NA12878/"\n'
            '    "NA12878.alt_bwamem_GRCh38DH.20150826.CEU.exome.cram"\n'
            ')\n\n'
            'view = LinearGenomeView(\n'
            '    assembly=grch38, location="1:100,987,200..100,987,450"\n'
            ')\n'
            'view.add_track(\n'
            '    {\n'
            '        "type": "AlignmentsTrack",\n'
            '        "trackId": "na12878-exome",\n'
            '        "name": "NA12878 exome",\n'
            '        "assemblyNames": ["GRCh38"],\n'
            '        "adapter": {"type": "CramAdapter", "uri": cram},\n'
            '    }\n'
            ')\n'
            'view'
        ),
        new_markdown_cell(
            "## Color reads, show soft-clips\n\n"
            "A track config can carry a `displays` entry to preset the "
            "display — here color by pair orientation to surface structural "
            "signal, and reveal soft-clipped bases."
        ),
        new_code_cell(
            'view.add_track(\n'
            '    {\n'
            '        "type": "AlignmentsTrack",\n'
            '        "trackId": "na12878-colored",\n'
            '        "name": "NA12878 (pair orientation)",\n'
            '        "assemblyNames": ["GRCh38"],\n'
            '        "adapter": {"type": "CramAdapter", "uri": cram},\n'
            '        "displays": [\n'
            '            {\n'
            '                "type": "LinearAlignmentsDisplay",\n'
            '                "displayId": "na12878-colored-display",\n'
            '                "colorBy": {"type": "pairOrientation"},\n'
            '                "showSoftClipping": True,\n'
            '            }\n'
            '        ],\n'
            '    }\n'
            ')'
        ),
    ],
)

# --- 04 multisample variants ------------------------------------------------
save(
    "04_multisample_variants.ipynb",
    [
        new_markdown_cell(
            "# Multi-sample variants\n\n"
            + badge("04_multisample_variants.ipynb")
            + "\n\nA multi-sample VCF has one genotype column per sample. A "
            "`VariantTrack` can render it as a per-sample band or as a genotype "
            "matrix — that's the display `type` — and a samples TSV lets you "
            "group and color samples by metadata."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## A per-sample band, colored by population\n\n"
            "`samplesTsvLocation` maps each sample to attributes (here "
            "`population`); the display's `colorBy` names the column that colors "
            "the rows. The VCF's `.tbi` index is resolved from the `uri`."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
            'volvox = make_assembly(\n'
            '    "volvox",\n'
            '    "https://jbrowse.org/genomes/volvox/volvox.fa.gz",\n'
            ')\n\n'
            'base = (\n'
            '    "https://raw.githubusercontent.com/GMOD/jbrowse-components/main/"\n'
            '    "test_data/volvox/"\n'
            ')\n\n'
            'def sv_track(track_id, name, display_type):\n'
            '    return {\n'
            '        "type": "VariantTrack",\n'
            '        "trackId": track_id,\n'
            '        "name": name,\n'
            '        "assemblyNames": ["volvox"],\n'
            '        "adapter": {\n'
            '            "type": "VcfTabixAdapter",\n'
            '            "uri": base + "volvox.sv.vcf.gz",\n'
            '            "samplesTsvLocation": {"uri": base + "volvox.sv.samples.tsv"},\n'
            '        },\n'
            '        "displays": [\n'
            '            {\n'
            '                "type": display_type,\n'
            '                "displayId": track_id + "-display",\n'
            '                "colorBy": "population",\n'
            '            }\n'
            '        ],\n'
            '    }\n\n'
            'view = LinearGenomeView(assembly=volvox, location="ctgA:1..50,000")\n'
            'view.add_track(\n'
            '    sv_track("sv-band", "multi-sample SV", "LinearMultiSampleVariantDisplay")\n'
            ')\n'
            'view'
        ),
        new_markdown_cell(
            "## The same VCF as a genotype matrix\n\n"
            'Swap the display `type` to `LinearMultiSampleVariantMatrixDisplay` '
            "for a compact grid — one column per variant, one row per sample — "
            "that scales to hundreds of samples."
        ),
        new_code_cell(
            'matrix = LinearGenomeView(assembly=volvox, location="ctgA:1..50,000")\n'
            'matrix.add_track(\n'
            '    sv_track(\n'
            '        "sv-matrix", "genotype matrix",\n'
            '        "LinearMultiSampleVariantMatrixDisplay",\n'
            '    )\n'
            ')\n'
            'matrix'
        ),
    ],
)

# --- 05 CNV calling ---------------------------------------------------------
save(
    "05_cnv_calling.ipynb",
    [
        new_markdown_cell(
            "# Call CNVs, then see them in context\n\n"
            + badge("05_cnv_calling.ipynb")
            + "\n\nThe notebook loop: **run an analysis, drop the result onto "
            "the genome.** Here we segment binned read-depth into "
            "copy-number gains and losses, then load the calls as a track — no "
            "file written. The synthetic depth carries a focal amplification at "
            "*ERBB2* (HER2), the classic breast-cancer CNV."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## The signal: binned log2 depth ratio\n\n"
            "Stand-in for a tumor/normal coverage ratio over a stretch of "
            "chr17. Swap it for your own binned depth (`cnvkit`, `mosdepth`, …) "
            "as long as it has chrom/start/end and a log2 column."
        ),
        new_code_cell(
            'import numpy as np\n'
            'import pandas as pd\n\n'
            'rng = np.random.default_rng(0)\n'
            'chrom, start, end, binsize = "17", 39_000_000, 40_200_000, 10_000\n'
            'bin_starts = np.arange(start, end, binsize)\n'
            'log2 = rng.normal(0, 0.25, size=bin_starts.size)\n\n'
            '# a focal ERBB2/HER2 amplification, plus a nearby deletion\n'
            'log2[(bin_starts >= 39_680_000) & (bin_starts < 39_740_000)] += 2.4\n'
            'log2[(bin_starts >= 39_180_000) & (bin_starts < 39_260_000)] -= 1.4\n\n'
            'bins = pd.DataFrame(\n'
            '    {\n'
            '        "chrom": chrom,\n'
            '        "start": bin_starts,\n'
            '        "end": bin_starts + binsize,\n'
            '        "log2": log2.round(3),\n'
            '    }\n'
            ')\n'
            'bins.head()'
        ),
        new_markdown_cell(
            "## Call segments\n\n"
            "Smooth, threshold into gain/loss/neutral, and merge adjacent "
            "like-state bins into segments — a toy segmenter standing in for "
            "CBS/HMM."
        ),
        new_code_cell(
            'GAIN, LOSS = 0.4, -0.4\n'
            'smooth = bins["log2"].rolling(5, center=True, min_periods=1).median().to_numpy()\n'
            'state = np.where(smooth > GAIN, "gain", np.where(smooth < LOSS, "loss", "neutral"))\n\n'
            'segments, i = [], 0\n'
            'while i < len(bins):\n'
            '    j = i\n'
            '    while j + 1 < len(bins) and state[j + 1] == state[i]:\n'
            '        j += 1\n'
            '    if state[i] != "neutral":\n'
            '        segments.append(\n'
            '            {\n'
            '                "chrom": chrom,\n'
            '                "start": int(bins["start"][i]),\n'
            '                "end": int(bins["end"][j]),\n'
            '                "state": state[i],\n'
            '                "mean_log2": round(float(smooth[i : j + 1].mean()), 2),\n'
            '            }\n'
            '        )\n'
            '    i = j + 1\n\n'
            'calls = pd.DataFrame(segments)\n'
            'calls'
        ),
        new_markdown_cell(
            "## Load signal + calls onto the genome\n\n"
            "Two `add_features` tracks: the per-bin log2 (red gain / blue loss) "
            "and the called segments on top. `color` is a jexl expression over "
            "each feature's own columns."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
            'grch38 = make_assembly(\n'
            '    "GRCh38",\n'
            '    "https://s3.amazonaws.com/jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    aliases=["hg38"],\n'
            ')\n'
            'view = LinearGenomeView(assembly=grch38, location="17:39,000,000..40,200,000")\n'
            'view.add_features(\n'
            '    bins,\n'
            '    name="log2 depth ratio",\n'
            '    color="jexl:get(feature,\'log2\') > 0.4 ? \'#c62828\' : get(feature,\'log2\') < -0.4 ? \'#1565c0\' : \'#cfcfcf\'",\n'
            ')\n'
            'view.add_features(\n'
            '    calls,\n'
            '    name="CNV calls",\n'
            '    color="jexl:get(feature,\'state\') == \'gain\' ? \'#c62828\' : \'#1565c0\'",\n'
            ')\n'
            'view'
        ),
        new_markdown_cell(
            "Zoom to *ERBB2* to land on the amplified segment (drives the view "
            "from Python):"
        ),
        new_code_cell('view.location = "17:39,650,000..39,770,000"'),
    ],
)

# --- 06 popgen selection scan -----------------------------------------------
save(
    "06_popgen_selection.ipynb",
    [
        new_markdown_cell(
            "# Scan for selection between populations (Fst), then view the sweep\n\n"
            + badge("06_popgen_selection.ipynb")
            + "\n\nThe compute→view loop on real data. Two *Drosophila "
            "melanogaster* populations — ancestral **African** and derived "
            "**cosmopolitan** — carry an insecticide-resistance allele that swept "
            "in the cosmopolitan range but not in Africa. Compute **Fst** from "
            "their allele frequencies and it peaks at *Cyp6g1*, right where the "
            "cosmopolitan population's diversity collapses. A differentiation peak "
            "sitting on a population-specific diversity valley is the signature of "
            "local adaptation — no single statistic proves it, their overlap does.\n\n"
            "Frequencies are [DEST](https://dest.bio) Pool-Seq; the diversity "
            "bigWigs come from the same "
            "[population-genomics tutorial](https://jbrowse.org/jb2/docs/tutorials/population_genomics/#between-populations)."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## Compute windowed Fst\n\n"
            "Load the per-SNP African and cosmopolitan allele frequencies, then "
            "take Hudson Fst per 10 kb window (summed numerators over summed "
            "denominators). Swap the CSV for your own two frequency columns."
        ),
        new_code_cell(
            'import pandas as pd\n\n'
            'freqs = pd.read_csv("https://jbrowse.org/demos/popgen/dest_cyp6g1_freqs.csv")\n'
            'p1, p2 = freqs.afr_freq, freqs.cosmo_freq\n'
            'freqs["num"] = (p1 - p2) ** 2                 # Hudson Fst numerator\n'
            'freqs["den"] = p1 * (1 - p2) + p2 * (1 - p1)  # ... denominator\n'
            'freqs["w"] = freqs.pos // 10_000 * 10_000\n\n'
            'g = freqs.groupby("w")\n'
            'windows = pd.DataFrame({\n'
            '    "chrom": "chr2R",\n'
            '    "start": g.size().index.astype(int),\n'
            '    "end": g.size().index.astype(int) + 10_000,\n'
            '    "fst": (g.num.sum() / g.den.sum()).clip(lower=0).round(3).values,\n'
            '    "n_snps": g.size().values,\n'
            '})\n'
            'windows = windows[windows.n_snps >= 20]\n'
            'windows.sort_values("fst", ascending=False).head()'
        ),
        new_markdown_cell(
            "## View the sweep on dm6\n\n"
            "`fetch_hub(\"dm6\")` pulls the fly genome, refName aliases, and a "
            "gene-name search index from the hosted hub. The computed Fst windows "
            "redden at the peak; the per-population diversity loads as a two-line "
            "wiggle — cosmopolitan collapses at the sweep while African holds."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n'
            'BW = "https://jbrowse.org/demos/popgen/dest_cyp6g1_div_%s.bw"\n'
            'div = lambda label, color, pop: {\n'
            '    "type": "BigWigAdapter", "source": label, "color": color,\n'
            '    "bigWigLocation": {"uri": BW % pop},\n'
            '}\n\n'
            'dm6 = fetch_hub("dm6")\n'
            'view = LinearGenomeView(\n'
            '    assembly=dm6["assemblies"][0],\n'
            '    aggregate_text_search_adapters=dm6["aggregateTextSearchAdapters"],\n'
            '    location="chr2R:11,900,000..12,450,000",  # or a gene name: "Cyp6g1"\n'
            ')\n'
            'view.add_features(\n'
            '    windows,\n'
            '    name="Fst (African vs cosmopolitan)",\n'
            '    color="jexl:get(feature,\'fst\') > 0.25 ? \'#d84315\' : get(feature,\'fst\') > 0.12 ? \'#f9a825\' : \'#90a4ae\'",\n'
            ')\n'
            'view.add_track({\n'
            '    "type": "MultiQuantitativeTrack",\n'
            '    "trackId": "diversity",\n'
            '    "name": "Nucleotide diversity (African vs cosmopolitan)",\n'
            '    "adapter": {"type": "MultiWiggleAdapter", "subadapters": [\n'
            '        div("African (ancestral)", "#377eb8", "african"),\n'
            '        div("Cosmopolitan (derived)", "#e41a1c", "cosmopolitan"),\n'
            '    ]},\n'
            '    "displays": [{"type": "MultiLinearWiggleDisplay",\n'
            '                  "displayId": "diversity-d", "defaultRendering": "multiline"}],\n'
            '})\n'
            'view.add_track(next(t for t in dm6["tracks"] if t["trackId"] == "dm6-ncbiRefSeqCurated"))\n'
            'view'
        ),
    ],
)

# --- 07 differential expression ---------------------------------------------
save(
    "07_differential_expression.ipynb",
    [
        new_markdown_cell(
            "# Differential expression → view\n\n"
            + badge("07_differential_expression.ipynb")
            + "\n\nAnother analysis→genome loop: run a small DE analysis over "
            "gene counts, then load each gene colored by its result — "
            "up-regulated red, down-regulated blue. All computed in the "
            "notebook (numpy only)."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## Counts → log2 fold-change and a t-test\n\n"
            "Simulate control vs treatment counts for a panel of genes (a few "
            "truly differential), then compute per-gene log2FC and a Welch "
            "t-test — a normal approximation gives the p-value, no scipy needed. "
            "Swap in your own DESeq2/edgeR table joined to gene coordinates."
        ),
        new_code_cell(
            'import math\n'
            'import numpy as np\n'
            'import pandas as pd\n\n'
            'rng = np.random.default_rng(7)\n'
            'n_genes, n_rep = 80, 4\n'
            'chrom, gene_len, gap = "7", 6_000, 40_000\n'
            'starts = 1_000_000 + np.arange(n_genes) * gap\n\n'
            'base = rng.uniform(20, 400, n_genes)  # baseline expression per gene\n'
            'true_lfc = np.zeros(n_genes)\n'
            'up = rng.choice(n_genes, 6, replace=False)\n'
            'down = rng.choice(np.setdiff1d(np.arange(n_genes), up), 6, replace=False)\n'
            'true_lfc[up] = rng.uniform(1.5, 3.0, up.size)\n'
            'true_lfc[down] = -rng.uniform(1.5, 3.0, down.size)\n\n'
            'ctrl = rng.poisson(base[:, None], size=(n_genes, n_rep))\n'
            'treat = rng.poisson((base * 2.0**true_lfc)[:, None], size=(n_genes, n_rep))\n\n'
            'lc, lt = np.log2(ctrl + 1), np.log2(treat + 1)\n'
            'lfc = lt.mean(1) - lc.mean(1)\n'
            'se = np.sqrt(lc.var(1, ddof=1) / n_rep + lt.var(1, ddof=1) / n_rep)\n'
            't = np.divide(lfc, se, out=np.zeros_like(lfc), where=se > 0)\n'
            'pval = np.array([math.erfc(abs(v) / math.sqrt(2)) for v in t])\n\n'
            'de = pd.DataFrame(\n'
            '    {\n'
            '        "chrom": chrom,\n'
            '        "start": starts,\n'
            '        "end": starts + gene_len,\n'
            '        "name": [f"GENE{i:04d}" for i in range(n_genes)],\n'
            '        "log2fc": lfc.round(2),\n'
            '        "pvalue": pval,\n'
            '    }\n'
            ')\n'
            'de["sig"] = np.where(\n'
            '    (de.pvalue < 0.01) & (de.log2fc.abs() > 1),\n'
            '    np.where(de.log2fc > 0, "up", "down"),\n'
            '    "ns",\n'
            ')\n'
            'de.sort_values("pvalue").head()'
        ),
        new_markdown_cell(
            "## Load the DE table onto the genome\n\n"
            "Each gene is colored by call; `log2fc`/`pvalue` ride along and show "
            "in the feature details."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
            'grch38 = make_assembly(\n'
            '    "GRCh38",\n'
            '    "https://s3.amazonaws.com/jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    aliases=["hg38"],\n'
            ')\n'
            'view = LinearGenomeView(assembly=grch38, location="7:1,000,000..4,300,000")\n'
            'view.add_features(\n'
            '    de,\n'
            '    name="differential expression",\n'
            '    color="jexl:get(feature,\'sig\') == \'up\' ? \'#c62828\' : get(feature,\'sig\') == \'down\' ? \'#1565c0\' : \'#cfcfcf\'",\n'
            ')\n'
            'view'
        ),
    ],
)

# --- 08 hosted assembly hub -------------------------------------------------
save(
    "08_hosted_assembly_hub.ipynb",
    [
        new_markdown_cell(
            "# Easy human data: a hosted assembly hub\n\n"
            + badge("08_hosted_assembly_hub.ipynb")
            + "\n\nWiring up a human genome by hand — sequence, refName aliases, "
            "cytobands, a gene-name search index — is the fiddly part. "
            "`fetch_hub` pulls all of it, already configured and CORS-enabled, "
            "from [genomes.jbrowse.org](https://genomes.jbrowse.org): pass a "
            "UCSC name (`hg38`, `hg19`, `mm10`) or a GenArk accession "
            "(`GCA_...`). It returns plain JSON you hand to the view."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## Pull hg38 and open it at a gene\n\n"
            "The hub config carries a gene-name search index, so `location` "
            "accepts a symbol like `BRCA1`, not just a locstring."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n'
            'hg38 = fetch_hub("hg38")  # sequence + refName aliases + cytobands + search\n\n'
            'view = LinearGenomeView(\n'
            '    assembly=hg38["assemblies"][0],\n'
            '    aggregate_text_search_adapters=hg38["aggregateTextSearchAdapters"],\n'
            '    location="BRCA1",\n'
            ')\n'
            'view'
        ),
        new_markdown_cell(
            "## Add a hosted track\n\n"
            "`hg38[\"tracks\"]` is a catalog of ready-to-use hosted tracks. Pick "
            "one by id and hand it to `add_track` — it's just JSON, no special "
            "API."
        ),
        new_code_cell(
            'catalog = {t["trackId"]: t for t in hg38["tracks"]}\n'
            'print(len(catalog), "hosted tracks, e.g.:", list(catalog)[:4])\n\n'
            'view.add_track(catalog["hg38-ncbiRefSeqCurated"])'
        ),
        new_markdown_cell(
            "## Mix in your own data\n\n"
            "Your own tracks drop in next to hosted ones. Because the hub "
            "assembly carries refName aliases, a file that names chromosomes "
            "`chr17` lines up with the reference automatically — no manual "
            "aliasing."
        ),
        new_code_cell(
            'view.add_track(\n'
            '    {\n'
            '        "type": "QuantitativeTrack",\n'
            '        "trackId": "phyloP100way",\n'
            '        "name": "phyloP100way",\n'
            '        "assemblyNames": ["hg38"],\n'
            '        "adapter": {\n'
            '            "type": "BigWigAdapter",\n'
            '            "uri": "https://hgdownload.cse.ucsc.edu/goldenpath/hg38/phyloP100way/hg38.phyloP100way.bw",\n'
            '        },\n'
            '    }\n'
            ')'
        ),
    ],
)

# --- 09 interactive controls ------------------------------------------------
save(
    "09_interactive_controls.ipynb",
    [
        new_markdown_cell(
            "# Interactive controls: a slider that re-runs the analysis\n\n"
            + badge("09_interactive_controls.ipynb")
            + "\n\nThe view is wired to a live kernel, so a widget control can "
            "**re-run the computation** and repaint the track — not just filter a "
            "static file. Here an `ipywidgets` slider sets the significance "
            "threshold for a differential-expression call; moving it "
            "reclassifies every gene in Python and pushes the updated track. The "
            "genome view and the control sit side by side, both driven from the "
            "same notebook state."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## The analysis\n\n"
            "The same small DE table as the DE example — genes with a log2 "
            "fold-change and a p-value. `classify` is the part a slider re-runs: "
            "it labels each gene up / down / not-significant at a chosen p-value "
            "cutoff. Swap in your own DESeq2/edgeR table joined to coordinates."
        ),
        new_code_cell(
            "import numpy as np\n"
            "import pandas as pd\n\n"
            "rng = np.random.default_rng(7)\n"
            "n_genes, n_rep = 80, 4\n"
            'chrom, gene_len, gap = "7", 6_000, 40_000\n'
            "starts = 1_000_000 + np.arange(n_genes) * gap\n\n"
            "base = rng.uniform(20, 400, n_genes)\n"
            "true_lfc = np.zeros(n_genes)\n"
            "up = rng.choice(n_genes, 6, replace=False)\n"
            "down = rng.choice(np.setdiff1d(np.arange(n_genes), up), 6, replace=False)\n"
            "true_lfc[up] = rng.uniform(1.5, 3.0, up.size)\n"
            "true_lfc[down] = -rng.uniform(1.5, 3.0, down.size)\n\n"
            "ctrl = rng.poisson(base[:, None], size=(n_genes, n_rep))\n"
            "treat = rng.poisson((base * 2.0**true_lfc)[:, None], size=(n_genes, n_rep))\n"
            "lc, lt = np.log2(ctrl + 1), np.log2(treat + 1)\n"
            "lfc = lt.mean(1) - lc.mean(1)\n"
            "se = np.sqrt(lc.var(1, ddof=1) / n_rep + lt.var(1, ddof=1) / n_rep)\n"
            "t = np.divide(lfc, se, out=np.zeros_like(lfc), where=se > 0)\n"
            "pval = np.exp(-0.717 * np.abs(t) - 0.416 * t**2)  # tail approx, no scipy\n\n"
            "de = pd.DataFrame(\n"
            "    {\n"
            '        "chrom": chrom,\n'
            '        "start": starts,\n'
            '        "end": starts + gene_len,\n'
            '        "name": [f"GENE{i:04d}" for i in range(n_genes)],\n'
            '        "log2fc": lfc.round(2),\n'
            '        "pvalue": pval,\n'
            "    }\n"
            ")\n\n\n"
            "def classify(pvalue_cutoff, lfc_cutoff=1.0):\n"
            "    sig = np.where(\n"
            '        (de.pvalue < pvalue_cutoff) & (de.log2fc.abs() > lfc_cutoff),\n'
            '        np.where(de.log2fc > 0, "up", "down"),\n'
            '        "ns",\n'
            "    )\n"
            '    return de.assign(sig=sig)\n\n\n'
            'classify(0.01).sig.value_counts()'
        ),
        new_markdown_cell(
            "## Wire a slider to the view\n\n"
            "`render` reruns `classify` at the slider's cutoff and replaces the "
            "track (clearing first, so moving the slider repaints in place rather "
            "than stacking tracks). `slider.observe` calls it on every change — "
            "including a programmatic one, which is how this runs headless below. "
            "Drag the slider and the genes recolor live."
        ),
        new_code_cell(
            "import ipywidgets as widgets\n\n"
            "from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n"
            "grch38 = make_assembly(\n"
            '    "GRCh38",\n'
            '    "https://s3.amazonaws.com/jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    aliases=["hg38"],\n'
            ")\n"
            'view = LinearGenomeView(assembly=grch38, location="7:1,000,000..4,300,000")\n\n'
            'COLOR = "jexl:get(feature,\'sig\') == \'up\' ? \'#c62828\' : get(feature,\'sig\') == \'down\' ? \'#1565c0\' : \'#cfcfcf\'"\n\n\n'
            "def render(pvalue_cutoff):\n"
            "    view.tracks = []  # replace, don't stack\n"
            "    view.add_features(\n"
            '        classify(pvalue_cutoff),\n'
            '        name=f"DE (p < {pvalue_cutoff:g})",\n'
            '        track_id="de",\n'
            "        color=COLOR,\n"
            "    )\n\n\n"
            "slider = widgets.FloatLogSlider(\n"
            '    value=0.01, base=10, min=-4, max=-1, step=0.2, description="p <",\n'
            ")\n"
            'slider.observe(lambda change: render(change["new"]), "value")\n'
            "render(slider.value)\n\n"
            "widgets.VBox([slider, view])"
        ),
        new_markdown_cell(
            "Setting the slider from code fires the same observer, so this "
            "tightens the threshold and repaints the track without any manual "
            "interaction:"
        ),
        new_code_cell(
            "slider.value = 1e-4\n"
            'print("significant now:", int((classify(slider.value).sig != "ns").sum()), "genes")'
        ),
    ],
)

# --- 10 region-reactive computed track --------------------------------------
save(
    "10_region_reactive.ipynb",
    [
        new_markdown_cell(
            "# Region-reactive: compute only what's on screen\n\n"
            + badge("10_region_reactive.ipynb")
            + "\n\nThe view syncs its visible region back to Python, so you can "
            "**observe `location` and recompute as the user pans** — the loop a "
            "static browser can't close. Here a per-base score (stand-in for "
            "coverage from a BAM, a motif scan, GC content, …) is computed only "
            "over the window in view, at a bin size that adapts to the zoom "
            "level. Nothing is precomputed genome-wide; the kernel answers for "
            "exactly what's asked."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## The (expensive) per-base score\n\n"
            "`score` stands in for something you would not want to run across a "
            "whole genome up front — read depth from a `pysam` pileup, a PWM "
            "scan, GC content. `compute_windows` evaluates it only between "
            "`start` and `end` and bins to ~200 points across the view, so "
            "zooming in *raises* the resolution instead of just cropping a "
            "fixed-resolution file."
        ),
        new_code_cell(
            "import numpy as np\n"
            "import pandas as pd\n\n"
            "# two peaks in the score landscape, to have something to find\n"
            "PEAKS = [(29_845_000, 2500, 1.0), (29_905_000, 6000, 0.7)]\n\n\n"
            "def score(pos):\n"
            "    pos = np.asarray(pos, dtype=float)\n"
            "    y = 0.12 * np.sin(pos / 700.0)  # background\n"
            "    for center, width, height in PEAKS:\n"
            "        y = y + height * np.exp(-0.5 * ((pos - center) / width) ** 2)\n"
            "    return y\n\n\n"
            "def compute_windows(chrom, start, end):\n"
            "    span = max(end - start, 1)\n"
            "    binsize = max(50, span // 200)  # ~200 bins across the view\n"
            "    edges = np.arange(start, end, binsize)\n"
            "    rows = [\n"
            "        {\n"
            '            "chrom": chrom,\n'
            '            "start": int(edge),\n'
            '            "end": int(min(edge + binsize, end)),\n'
            '            "score": round(float(score(np.arange(edge, min(edge + binsize, end))).mean()), 3),\n'
            "        }\n"
            "        for edge in edges\n"
            "    ]\n"
            "    return pd.DataFrame(rows)\n\n\n"
            'compute_windows("10", 29_838_000, 29_858_000).head()'
        ),
        new_markdown_cell(
            "## Recompute on every pan\n\n"
            "`on_location` parses the view's current locstring and re-renders the "
            "computed track for that window. `view.observe(..., \"location\")` "
            "fires it whenever the region changes — dragging in the UI, or "
            "setting `view.location` from code. `parse_loc` returns `None` for a "
            "gene-name or empty location, so those are simply skipped."
        ),
        new_code_cell(
            "import re\n\n"
            "from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n"
            "grch38 = make_assembly(\n"
            '    "GRCh38",\n'
            '    "https://s3.amazonaws.com/jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    aliases=["hg38"],\n'
            ")\n\n\n"
            "def parse_loc(loc):\n"
            '    m = re.match(r"^\\s*([^:\\s]+)\\s*:\\s*([\\d,]+)\\s*\\.\\.\\s*([\\d,]+)", loc or "")\n'
            "    if not m:\n"
            "        return None\n"
            '    return m.group(1), int(m.group(2).replace(",", "")), int(m.group(3).replace(",", ""))\n\n\n'
            "def render_region(chrom, start, end):\n"
            "    view.tracks = []  # replace with the freshly computed window\n"
            "    view.add_features(\n"
            "        compute_windows(chrom, start, end),\n"
            '        name="score (visible region)",\n'
            '        track_id="signal",\n'
            "        color=\"jexl:get(feature,'score') > 0.5 ? '#c62828' : get(feature,'score') > 0.25 ? '#f9a825' : '#90a4ae'\",\n"
            "    )\n\n\n"
            "def on_location(change):\n"
            '    region = parse_loc(change["new"])\n'
            "    if region:\n"
            "        render_region(*region)\n\n\n"
            'view = LinearGenomeView(assembly=grch38, location="10:29,838,000..29,858,000")\n'
            'view.observe(on_location, "location")\n'
            "render_region(*parse_loc(view.location))  # initial fill\n"
            "view"
        ),
        new_markdown_cell(
            "Driving `location` from code fires the observer, so the track "
            "recomputes for the new window. Zooming out widens the bins; zooming "
            "in sharpens them — the resolution follows the view:"
        ),
        new_code_cell(
            'view.location = "10:29,890,000..29,920,000"  # zoom to the second peak\n'
            "len(view.tracks[0][\"adapter\"][\"features\"]), \"bins computed for this window\""
        ),
    ],
)

print("done")
