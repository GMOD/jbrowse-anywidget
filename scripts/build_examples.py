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
    %pip install -q "jbrowse-anywidget @ git+https://github.com/cmdcolin/jbrowse-anywidget" pandas numpy

# Colab requires this to render third-party (anywidget) widgets:
try:
    from google.colab import output

    output.enable_custom_widget_manager()
except ImportError:
    pass"""

COLAB = "https://colab.research.google.com/assets/colab-badge.svg"


def badge(path):
    href = f"https://colab.research.google.com/github/cmdcolin/jbrowse-anywidget/blob/main/examples/{path}"
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

print("done")
