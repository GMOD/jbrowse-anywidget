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
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
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
            "`add_track` takes a [JBrowse track "
            "config](https://jbrowse.org/jb2/docs/config_guide/#tracks) — the "
            "same JSON you'd write in a config file — so every track type and "
            "adapter is available directly. Here, a conservation bigwig."
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
            "# Scan for selection (Fst), then view the sweep\n\n"
            + badge("06_popgen_selection.ipynb")
            + "\n\nSame loop, population genetics: compute a windowed **Fst** "
            "between two populations and load it as a track to spot loci that "
            "differ. The synthetic data carries a selective sweep at "
            "*LCT/MCM6* — the lactase-persistence locus."
        ),
        new_code_cell(INSTALL),
        new_markdown_cell(
            "## Simulate allele frequencies in two populations\n\n"
            "Per-SNP alternate-allele frequencies over a stretch of chr2, with "
            "a sweep raising frequencies in population 1 around *LCT*. Swap for "
            "your own frequencies (e.g. from a multi-sample VCF)."
        ),
        new_code_cell(
            'import numpy as np\n'
            'import pandas as pd\n\n'
            'rng = np.random.default_rng(1)\n'
            'chrom, start, end = "2", 135_000_000, 137_000_000\n'
            'pos = np.sort(rng.integers(start, end, size=4000))\n\n'
            'anc = rng.uniform(0.05, 0.95, size=pos.size)  # shared ancestral freq\n'
            'p1 = np.clip(anc + rng.normal(0, 0.05, pos.size), 0.001, 0.999)\n'
            'p2 = np.clip(anc + rng.normal(0, 0.05, pos.size), 0.001, 0.999)\n\n'
            '# selective sweep at LCT/MCM6: push pop-1 frequencies up\n'
            'sweep = (pos >= 135_780_000) & (pos <= 135_860_000)\n'
            'p1[sweep] = np.clip(p1[sweep] + 0.6, 0.001, 0.999)'
        ),
        new_markdown_cell(
            "## Windowed Hudson Fst\n\n"
            "Fst per window as a ratio of summed numerators to denominators "
            "(the Bhatia et al. recommendation), in 20 kb windows."
        ),
        new_code_cell(
            'num = (p1 - p2) ** 2\n'
            'den = p1 * (1 - p2) + p2 * (1 - p1)\n\n'
            'win = 20_000\n'
            'edges = np.arange(start, end + win, win)\n'
            'w = np.searchsorted(edges, pos, side="right") - 1\n\n'
            'rows = []\n'
            'for k in range(len(edges) - 1):\n'
            '    m = w == k\n'
            '    if m.sum() >= 5:\n'
            '        fst = float(num[m].sum() / den[m].sum())\n'
            '        rows.append(\n'
            '            {\n'
            '                "chrom": chrom,\n'
            '                "start": int(edges[k]),\n'
            '                "end": int(edges[k + 1]),\n'
            '                "fst": round(max(fst, 0.0), 3),\n'
            '                "n_snps": int(m.sum()),\n'
            '            }\n'
            '        )\n\n'
            'windows = pd.DataFrame(rows)\n'
            'windows.sort_values("fst", ascending=False).head()'
        ),
        new_markdown_cell(
            "## Load the scan onto the genome\n\n"
            "Windows colored by Fst — orange/red where the populations diverge. "
            "The peak sits over *LCT*."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
            'grch38 = make_assembly(\n'
            '    "GRCh38",\n'
            '    "https://s3.amazonaws.com/jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    aliases=["hg38"],\n'
            ')\n'
            'view = LinearGenomeView(assembly=grch38, location="2:135,000,000..137,000,000")\n'
            'view.add_features(\n'
            '    windows,\n'
            '    name="Fst (pop1 vs pop2)",\n'
            '    color="jexl:get(feature,\'fst\') > 0.25 ? \'#d84315\' : get(feature,\'fst\') > 0.1 ? \'#f9a825\' : \'#90a4ae\'",\n'
            ')\n'
            'view'
        ),
        new_markdown_cell("Zoom to the *LCT* sweep:"),
        new_code_cell('view.location = "2:135,700,000..135,900,000"'),
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

print("done")
