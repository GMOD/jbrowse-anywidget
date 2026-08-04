"""Regenerate the example notebooks in examples/.

Run: .venv/bin/python scripts/build_examples.py
Each notebook installs from PyPI only when the package isn't already importable,
so it runs unchanged in Colab and executes headless against a local editable
install for verification.
"""

from pathlib import Path

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def install(extra=""):
    """The first cell of every notebook: install in Colab, no-op locally.

    `extra` names any analysis libraries the notebook uses beyond pandas/numpy
    (e.g. "bioframe", "pysam", "scipy statsmodels") so the Colab install pulls
    them too; a local editable checkout already has them and is used as-is.
    """
    pkgs = ("pandas numpy " + extra).strip()
    return f"""\
# Install only if not already available (e.g. in Colab). The GitHub install
# needs no JS toolchain — the built widget bundle is committed in the repo. A
# local editable install is used as-is. (Swap to `jbrowse-anywidget` once it's
# published to PyPI.)
try:
    import jbrowse_anywidget  # noqa: F401
except ImportError:
    %pip install -q "jbrowse-anywidget @ git+https://github.com/GMOD/jbrowse-anywidget" {pkgs}

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
    with (EXAMPLES / name).open("w") as f:
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
        new_code_cell(install()),
        new_markdown_cell(
            "## An assembly and a view\n\n"
            "An assembly is the flat `{name, uri}` shorthand — core picks the adapter "
            "from the extension and derives the index files. This reference names chromosomes `1`, "
            "`2`, … but the UCSC bigWig below uses `chr1`, `chr2`, …; "
            "`refname_aliases_uri` points at UCSC's alias table so the two line "
            "up. `location` sets the opening region."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            "hg38 = {\n"
            '    "name": "hg38",\n'
            '    "uri": "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",\n'
            '    "aliases": ["GRCh38"],\n'
            '    "refNameAliases": {\n'
            '        "uri": "https://jbrowse.org/genomes/GRCh38/hg38_aliases.txt"\n'
            "    },\n"
            "}\n\n"
            'view = LinearGenomeView(assembly=hg38, location="10:29,838,565..29,838,850")\n'
            "view"
        ),
        new_markdown_cell(
            "## Add a track\n\n"
            "A bare data-file URL is a track — its type and adapter are inferred "
            "from the extension, the way [@jbrowse/img](https://jbrowse.org/jb2/docs/jbrowse-img)'s "
            "`--bam`/`--bigwig`/`--cram` flags work for the CLI. To set a display "
            "name or anything else, hand over a dict instead of the bare string — "
            "it is merged onto the inferred config, so `assemblyNames`, the "
            "adapter and the index location still come for free. Any non-default "
            "setting (color, height, ...) is just another key."
        ),
        new_code_cell(
            "view.add_track(\n"
            "    {\n"
            '        "uri": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",\n'
            '        "name": "phyloP100way",\n'
            "    }\n"
            ")"
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
            "# From a bioframe result to a track\n\n"
            + badge("02_dataframe_analysis.ipynb")
            + "\n\n[bioframe](https://bioframe.readthedocs.io) is the "
            "pandas-native toolkit for genomic intervals, and a bioframe frame is "
            "just a DataFrame with `chrom`/`start`/`end`. That's exactly what "
            "`add_features` takes — so any interval analysis you already do in "
            "bioframe is **one call from the genome**, no file written."
        ),
        new_code_cell(install("bioframe")),
        new_markdown_cell(
            "## Real intervals, one real operation\n\n"
            "UCSC's hg38 **CpG islands** (read straight from UCSC with pandas), "
            "then their **shores** — the 2 kb flanks where most differential "
            "methylation sits. In bioframe that's `expand` minus the islands, one "
            "line. This assembly names chromosomes `17` (no `chr`), so match it."
        ),
        new_code_cell(
            "import bioframe as bf\n"
            "import pandas as pd\n\n"
            'cols = "bin chrom start end name length cpgNum gcNum perCpg perGc obsExp".split()\n'
            "islands = pd.read_csv(\n"
            '    "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/cpgIslandExt.txt.gz",\n'
            '    sep="\\t", names=cols,\n'
            ")\n"
            'islands = islands[islands.chrom == "chr17"].assign(chrom="17")\n'
            "shores = bf.merge(bf.subtract(bf.expand(islands, pad=2000), islands))\n"
            'print(len(islands), "islands ->", len(shores), "shores")\n'
            "shores.head()"
        ),
        new_markdown_cell(
            "## Both on the genome\n\n"
            "One `add_features` per frame. Islands are colored by GC% — a column "
            "that rides along and shows in each feature's details; any column "
            "does. This lands on *TP53*."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            "hg38 = {\n"
            '    "name": "hg38",\n'
            '    "uri": "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",\n'
            '    "aliases": ["GRCh38"],\n'
            "}\n"
            'view = LinearGenomeView(assembly=hg38, location="17:7,660,000..7,700,000")\n'
            "view.add_features(\n"
            '    islands, name="CpG islands (by GC%)",\n'
            "    color=\"jexl:get(feature,'perGc') > 65 ? '#00695c' : '#4db6ac'\",\n"
            ")\n"
            'view.add_features(shores, name="CpG shores", color="#f9a825")\n'
            "view"
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
        new_code_cell(install()),
        new_markdown_cell(
            "## Assembly and alignments\n\n"
            "The CRAM's `.crai` index and its reference sequence are resolved "
            "automatically from the `uri`, so the adapter is just the URL."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            "grch38 = {\n"
            '    "name": "GRCh38",\n'
            '    "uri": "https://jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    "aliases": ["hg38"],\n'
            "}\n\n"
            "cram = (\n"
            '    "https://jbrowse.org/genomes/GRCh38/alignments/NA12878/"\n'
            '    "NA12878.alt_bwamem_GRCh38DH.20150826.CEU.exome.cram"\n'
            ")\n\n"
            "view = LinearGenomeView(\n"
            '    assembly=grch38, location="1:100,987,200..100,987,450"\n'
            ")\n"
            "view.add_track(\n"
            "    {\n"
            '        "type": "AlignmentsTrack",\n'
            '        "trackId": "na12878-exome",\n'
            '        "name": "NA12878 exome",\n'
            '        "assemblyNames": ["GRCh38"],\n'
            '        "adapter": {"type": "CramAdapter", "uri": cram},\n'
            "    }\n"
            ")\n"
            "view"
        ),
        new_markdown_cell(
            "## Color reads, show soft-clips\n\n"
            "A track config can carry a `displays` entry to preset the "
            "display — here color by pair orientation to surface structural "
            "signal, and reveal soft-clipped bases."
        ),
        new_code_cell(
            "view.add_track(\n"
            "    {\n"
            '        "type": "AlignmentsTrack",\n'
            '        "trackId": "na12878-colored",\n'
            '        "name": "NA12878 (pair orientation)",\n'
            '        "assemblyNames": ["GRCh38"],\n'
            '        "adapter": {"type": "CramAdapter", "uri": cram},\n'
            '        "displays": [\n'
            "            {\n"
            '                "type": "LinearAlignmentsDisplay",\n'
            '                "displayId": "na12878-colored-display",\n'
            '                "colorBy": {"type": "pairOrientation"},\n'
            '                "showSoftClipping": True,\n'
            "            }\n"
            "        ],\n"
            "    }\n"
            ")"
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
        new_code_cell(install()),
        new_markdown_cell(
            "## A per-sample band, colored by population\n\n"
            "`samplesTsvLocation` maps each sample to attributes (here "
            "`population`); the display's `colorBy` names the column that colors "
            "the rows. The VCF's `.tbi` index is resolved from the `uri`."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            "volvox = {\n"
            '    "name": "volvox",\n'
            '    "uri": "https://jbrowse.org/genomes/volvox/volvox.fa.gz",\n'
            "}\n\n"
            "base = (\n"
            '    "https://raw.githubusercontent.com/GMOD/jbrowse-components/main/"\n'
            '    "test_data/volvox/"\n'
            ")\n\n"
            "def sv_track(track_id, name, display_type):\n"
            "    return {\n"
            '        "type": "VariantTrack",\n'
            '        "trackId": track_id,\n'
            '        "name": name,\n'
            '        "assemblyNames": ["volvox"],\n'
            '        "adapter": {\n'
            '            "type": "VcfTabixAdapter",\n'
            '            "uri": base + "volvox.sv.vcf.gz",\n'
            '            "samplesTsvLocation": {"uri": base + "volvox.sv.samples.tsv"},\n'
            "        },\n"
            '        "displays": [\n'
            "            {\n"
            '                "type": display_type,\n'
            '                "displayId": track_id + "-display",\n'
            '                "colorBy": "population",\n'
            "            }\n"
            "        ],\n"
            "    }\n\n"
            'view = LinearGenomeView(assembly=volvox, location="ctgA:1..50,000")\n'
            "view.add_track(\n"
            '    sv_track("sv-band", "multi-sample SV", "LinearMultiSampleVariantDisplay")\n'
            ")\n"
            "view"
        ),
        new_markdown_cell(
            "## The same VCF as a genotype matrix\n\n"
            "Swap the display `type` to `LinearMultiSampleVariantMatrixDisplay` "
            "for a compact grid — one column per variant, one row per sample — "
            "that scales to hundreds of samples."
        ),
        new_code_cell(
            'matrix = LinearGenomeView(assembly=volvox, location="ctgA:1..50,000")\n'
            "matrix.add_track(\n"
            "    sv_track(\n"
            '        "sv-matrix", "genotype matrix",\n'
            '        "LinearMultiSampleVariantMatrixDisplay",\n'
            "    )\n"
            ")\n"
            "matrix"
        ),
    ],
)

# --- 05 pysam read depth ----------------------------------------------------
save(
    "05_bam_coverage.ipynb",
    [
        new_markdown_cell(
            "# Read depth from a BAM, straight from pysam\n\n"
            + badge("05_bam_coverage.ipynb")
            + "\n\n[pysam](https://pysam.readthedocs.io) is how Python reads BAM "
            "and CRAM. `count_coverage` over a region, bin it, and `add_features` "
            "puts it on the genome — no intermediate file, no bigWig conversion. "
            "The data is the real 1000 Genomes **NA12878 exome** (a 17 GB BAM, "
            "but pysam fetches only the index and the region you ask for)."
        ),
        new_code_cell(install("pysam")),
        new_markdown_cell(
            "## Coverage over BRCA1\n\n"
            "Open the remote BAM (its `.bai` is fetched automatically), sum the "
            "per-base A/C/G/T counts, and average into 100 bp bins. This BAM is "
            "aligned to GRCh37 and names the chromosome `17`; we relabel to "
            "`chr17` to match the hg19 hub below."
        ),
        new_code_cell(
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pysam\n\n"
            "BAM = (\n"
            '    "https://s3.amazonaws.com/1000genomes/phase3/data/NA12878/"\n'
            '    "exome_alignment/NA12878.mapped.ILLUMINA.bwa.CEU.exome.20121211.bam"\n'
            ")\n"
            'CHROM, START, END = "17", 41_196_312, 41_277_500  # BRCA1, GRCh37\n\n'
            "bam = pysam.AlignmentFile(BAM)\n"
            "depth = np.array(bam.count_coverage(CHROM, START, END)).sum(0)\n\n"
            "binsize = 100\n"
            "n = depth.size // binsize * binsize\n"
            "binned = depth[:n].reshape(-1, binsize).mean(1).round(1)\n"
            "starts = START + np.arange(binned.size) * binsize\n"
            "coverage = pd.DataFrame(\n"
            '    {"chrom": "chr17", "start": starts, "end": starts + binsize, "depth": binned}\n'
            ")\n"
            "coverage.head()"
        ),
        new_markdown_cell(
            "## See it on hg19, opened at the gene by name\n\n"
            '`fetch_hub("hg19")` brings the genome and a gene-name search index, '
            'so `location="BRCA1"` just works. Exome capture concentrates reads '
            "on the exons — the depth track peaks there and drops between."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n"
            'hg19 = fetch_hub("hg19")\n'
            "view = LinearGenomeView(\n"
            '    assembly=hg19["assemblies"][0],\n'
            '    aggregate_text_search_adapters=hg19["aggregateTextSearchAdapters"],\n'
            '    location="BRCA1",\n'
            ")\n"
            "view.add_features(\n"
            '    coverage, name="NA12878 exome depth",\n'
            "    color=\"jexl:get(feature,'depth') > 40 ? '#c62828' : get(feature,'depth') > 10 ? '#f9a825' : '#cfcfcf'\",\n"
            ")\n"
            "view"
        ),
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
        new_code_cell(install()),
        new_markdown_cell(
            "## Compute windowed Fst\n\n"
            "Load the per-SNP African and cosmopolitan allele frequencies, then "
            "take Hudson Fst per 10 kb window (summed numerators over summed "
            "denominators). Swap the CSV for your own two frequency columns."
        ),
        new_code_cell(
            "import pandas as pd\n\n"
            'freqs = pd.read_csv("https://jbrowse.org/demos/popgen/dest_cyp6g1_freqs.csv")\n'
            "p1, p2 = freqs.afr_freq, freqs.cosmo_freq\n"
            'freqs["num"] = (p1 - p2) ** 2                 # Hudson Fst numerator\n'
            'freqs["den"] = p1 * (1 - p2) + p2 * (1 - p1)  # ... denominator\n'
            'freqs["w"] = freqs.pos // 10_000 * 10_000\n\n'
            'g = freqs.groupby("w")\n'
            "windows = pd.DataFrame({\n"
            '    "chrom": "chr2R",\n'
            '    "start": g.size().index.astype(int),\n'
            '    "end": g.size().index.astype(int) + 10_000,\n'
            '    "fst": (g.num.sum() / g.den.sum()).clip(lower=0).round(3).values,\n'
            '    "n_snps": g.size().values,\n'
            "})\n"
            "windows = windows[windows.n_snps >= 20]\n"
            'windows.sort_values("fst", ascending=False).head()'
        ),
        new_markdown_cell(
            "## View the sweep on dm6\n\n"
            '`fetch_hub("dm6")` pulls the fly genome, refName aliases, and a '
            "gene-name search index from the hosted hub. The computed Fst windows "
            "redden at the peak; the per-population diversity loads as a two-line "
            "wiggle — cosmopolitan collapses at the sweep while African holds."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n"
            'BW = "https://jbrowse.org/demos/popgen/dest_cyp6g1_div_%s.bw"\n'
            "div = lambda label, color, pop: {\n"
            '    "type": "BigWigAdapter", "source": label, "color": color,\n'
            '    "bigWigLocation": {"uri": BW % pop},\n'
            "}\n\n"
            'dm6 = fetch_hub("dm6")\n'
            "view = LinearGenomeView(\n"
            '    assembly=dm6["assemblies"][0],\n'
            '    aggregate_text_search_adapters=dm6["aggregateTextSearchAdapters"],\n'
            '    location="chr2R:11,900,000..12,450,000",  # or a gene name: "Cyp6g1"\n'
            ")\n"
            "view.add_features(\n"
            "    windows,\n"
            '    name="Fst (African vs cosmopolitan)",\n'
            "    color=\"jexl:get(feature,'fst') > 0.25 ? '#d84315' : get(feature,'fst') > 0.12 ? '#f9a825' : '#90a4ae'\",\n"
            ")\n"
            "view.add_track({\n"
            '    "type": "MultiQuantitativeTrack",\n'
            '    "trackId": "diversity",\n'
            '    "name": "Nucleotide diversity (African vs cosmopolitan)",\n'
            '    "adapter": {"type": "MultiWiggleAdapter", "subadapters": [\n'
            '        div("African (ancestral)", "#377eb8", "african"),\n'
            '        div("Cosmopolitan (derived)", "#e41a1c", "cosmopolitan"),\n'
            "    ]},\n"
            '    "displays": [{"type": "MultiLinearWiggleDisplay",\n'
            '                  "displayId": "diversity-d", "defaultRendering": "multiline"}],\n'
            "})\n"
            'view.add_track(next(t for t in dm6["tracks"] if t["trackId"] == "dm6-ncbiRefSeqCurated"))\n'
            "view"
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
            "up-regulated red, down-regulated blue."
        ),
        new_code_cell(install("scipy statsmodels")),
        new_markdown_cell(
            "## Counts → log2 fold-change, Welch t-test, FDR\n\n"
            "Simulated control vs treatment counts stand in for a counts matrix "
            "(a few genes truly differential). The stats are the real tools — "
            "`scipy.stats.ttest_ind` (Welch) and Benjamini-Hochberg FDR from "
            "`statsmodels` — so swapping in your own counts, or a DESeq2/edgeR "
            "results table joined to gene coordinates, changes nothing downstream."
        ),
        new_code_cell(
            "import numpy as np\n"
            "import pandas as pd\n"
            "from scipy.stats import ttest_ind\n"
            "from statsmodels.stats.multitest import multipletests\n\n"
            "rng = np.random.default_rng(7)\n"
            "n_genes, n_rep = 80, 4\n"
            "starts = 1_000_000 + np.arange(n_genes) * 40_000\n\n"
            "base = rng.uniform(20, 400, n_genes)  # baseline expression per gene\n"
            "true_lfc = np.zeros(n_genes)\n"
            "up = rng.choice(n_genes, 6, replace=False)\n"
            "down = rng.choice(np.setdiff1d(np.arange(n_genes), up), 6, replace=False)\n"
            "true_lfc[up] = rng.uniform(1.5, 3.0, 6)\n"
            "true_lfc[down] = -rng.uniform(1.5, 3.0, 6)\n"
            "ctrl = rng.poisson(base[:, None], size=(n_genes, n_rep))\n"
            "treat = rng.poisson((base * 2.0**true_lfc)[:, None], size=(n_genes, n_rep))\n\n"
            "lc, lt = np.log2(ctrl + 1), np.log2(treat + 1)\n"
            "lfc = lt.mean(1) - lc.mean(1)\n"
            "padj = multipletests(ttest_ind(lt, lc, axis=1, equal_var=False).pvalue,\n"
            '                     method="fdr_bh")[1]\n\n'
            "de = pd.DataFrame(\n"
            "    {\n"
            '        "chrom": "7",\n'
            '        "start": starts,\n'
            '        "end": starts + 6_000,\n'
            '        "name": [f"GENE{i:04d}" for i in range(n_genes)],\n'
            '        "log2fc": lfc.round(2),\n'
            '        "padj": padj.round(4),\n'
            "    }\n"
            ")\n"
            'de["sig"] = np.where(\n'
            "    (de.padj < 0.05) & (de.log2fc.abs() > 1),\n"
            '    np.where(de.log2fc > 0, "up", "down"),\n'
            '    "ns",\n'
            ")\n"
            'de.sort_values("padj").head()'
        ),
        new_markdown_cell(
            "## Load the DE table onto the genome\n\n"
            "Each gene is colored by call; `log2fc`/`padj` ride along and show "
            "in the feature details."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            "grch38 = {\n"
            '    "name": "GRCh38",\n'
            '    "uri": "https://jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    "aliases": ["hg38"],\n'
            "}\n"
            'view = LinearGenomeView(assembly=grch38, location="7:1,000,000..4,300,000")\n'
            "view.add_features(\n"
            "    de,\n"
            '    name="differential expression",\n'
            "    color=\"jexl:get(feature,'sig') == 'up' ? '#c62828' : get(feature,'sig') == 'down' ? '#1565c0' : '#cfcfcf'\",\n"
            ")\n"
            "view"
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
        new_code_cell(install()),
        new_markdown_cell(
            "## Pull hg38 and open it at a gene\n\n"
            "The hub config carries a gene-name search index, so `location` "
            "accepts a symbol like `BRCA1`, not just a locstring."
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n"
            'hg38 = fetch_hub("hg38")  # sequence + refName aliases + cytobands + search\n\n'
            "view = LinearGenomeView(\n"
            '    assembly=hg38["assemblies"][0],\n'
            '    aggregate_text_search_adapters=hg38["aggregateTextSearchAdapters"],\n'
            '    location="BRCA1",\n'
            ")\n"
            "view"
        ),
        new_markdown_cell(
            "## Add a hosted track\n\n"
            '`hg38["tracks"]` is a catalog of ready-to-use hosted tracks. Pick '
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
            "view.add_track(\n"
            "    {\n"
            '        "type": "QuantitativeTrack",\n'
            '        "trackId": "phyloP100way",\n'
            '        "name": "phyloP100way",\n'
            '        "assemblyNames": ["hg38"],\n'
            '        "adapter": {\n'
            '            "type": "BigWigAdapter",\n'
            '            "uri": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",\n'
            "        },\n"
            "    }\n"
            ")"
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
        new_code_cell(install("scipy")),
        new_markdown_cell(
            "## The analysis\n\n"
            "The same small DE table as the DE example — genes with a log2 "
            "fold-change and a p-value. `classify` is the part a slider re-runs: "
            "it labels each gene up / down / not-significant at a chosen p-value "
            "cutoff. Swap in your own DESeq2/edgeR table joined to coordinates."
        ),
        new_code_cell(
            "import numpy as np\n"
            "import pandas as pd\n"
            "from scipy.stats import ttest_ind\n\n"
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
            "pval = ttest_ind(lt, lc, axis=1, equal_var=False).pvalue\n\n"
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
            "        (de.pvalue < pvalue_cutoff) & (de.log2fc.abs() > lfc_cutoff),\n"
            '        np.where(de.log2fc > 0, "up", "down"),\n'
            '        "ns",\n'
            "    )\n"
            "    return de.assign(sig=sig)\n\n\n"
            "classify(0.01).sig.value_counts()"
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
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            "grch38 = {\n"
            '    "name": "GRCh38",\n'
            '    "uri": "https://jbrowse.org/genomes/GRCh38/fasta/GRCh38.fa.gz",\n'
            '    "aliases": ["hg38"],\n'
            "}\n"
            'view = LinearGenomeView(assembly=grch38, location="7:1,000,000..4,300,000")\n\n'
            "COLOR = \"jexl:get(feature,'sig') == 'up' ? '#c62828' : get(feature,'sig') == 'down' ? '#1565c0' : '#cfcfcf'\"\n\n\n"
            "def render(pvalue_cutoff):\n"
            "    view.tracks = []  # replace, don't stack\n"
            "    view.add_features(\n"
            "        classify(pvalue_cutoff),\n"
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
            "# Region-reactive: compute coverage only for what's on screen\n\n"
            + badge("10_region_reactive.ipynb")
            + "\n\nThe view syncs its visible region back to Python, so you can "
            "**observe `location` and recompute as the user pans** — the loop a "
            "static browser can't close. Here [pysam](https://pysam.readthedocs.io) "
            "counts coverage from the real NA12878 exome BAM only over the window "
            "in view, at a bin size that follows the zoom. Nothing is precomputed "
            "genome-wide; the kernel answers for exactly what's asked, so zooming "
            "in *raises* the resolution instead of cropping a fixed file."
        ),
        new_code_cell(install("pysam")),
        new_markdown_cell(
            "## Coverage for one window\n\n"
            "Open the remote BAM once — only its index and the regions you query "
            "are fetched. `coverage` counts per-base depth over `start..end` and "
            "bins to ~400 points across the view. The BAM names the chromosome "
            "`17`; the hg19 hub uses `chr17`, so we strip the prefix on the way in."
        ),
        new_code_cell(
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pysam\n\n"
            "BAM = (\n"
            '    "https://s3.amazonaws.com/1000genomes/phase3/data/NA12878/"\n'
            '    "exome_alignment/NA12878.mapped.ILLUMINA.bwa.CEU.exome.20121211.bam"\n'
            ")\n"
            "bam = pysam.AlignmentFile(BAM)\n\n\n"
            "def coverage(chrom, start, end):\n"
            '    depth = np.array(bam.count_coverage(chrom.removeprefix("chr"), start, end)).sum(0)\n'
            "    binsize = max(20, (end - start) // 400)\n"
            "    n = depth.size // binsize * binsize\n"
            "    binned = depth[:n].reshape(-1, binsize).mean(1).round(1)\n"
            "    starts = start + np.arange(binned.size) * binsize\n"
            "    return pd.DataFrame(\n"
            '        {"chrom": chrom, "start": starts, "end": starts + binsize, "depth": binned}\n'
            "    )\n\n\n"
            'coverage("chr17", 41_196_312, 41_277_500).head()  # BRCA1'
        ),
        new_markdown_cell(
            "## Recompute on every pan\n\n"
            "`on_location` parses the view's locstring and re-renders coverage for "
            'that window. `view.observe(..., "location")` fires it whenever the '
            "region changes — dragging in the UI or setting `view.location` from "
            "code. A gene-name or whole-chromosome location doesn't parse, and a "
            "window wider than 5 Mb is skipped to keep each per-pan query snappy."
        ),
        new_code_cell(
            "import re\n\n"
            "from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n"
            'hg19 = fetch_hub("hg19")\n'
            "COLOR = \"jexl:get(feature,'depth') > 40 ? '#c62828' : get(feature,'depth') > 10 ? '#f9a825' : '#cfcfcf'\"\n\n\n"
            "def parse_loc(loc):\n"
            '    m = re.match(r"^\\s*([^:\\s]+)\\s*:\\s*([\\d,]+)\\s*\\.\\.\\s*([\\d,]+)", loc or "")\n'
            '    return (m[1], int(m[2].replace(",", "")), int(m[3].replace(",", ""))) if m else None\n\n\n'
            "def render_region(chrom, start, end):\n"
            "    if end - start <= 5_000_000:\n"
            "        view.tracks = []  # replace with the freshly computed window\n"
            "        view.add_features(\n"
            "            coverage(chrom, start, end),\n"
            '            name="NA12878 exome depth (visible region)",\n'
            '            track_id="depth",\n'
            "            color=COLOR,\n"
            "        )\n\n\n"
            "def on_location(change):\n"
            '    region = parse_loc(change["new"])\n'
            "    if region:\n"
            "        render_region(*region)\n\n\n"
            "view = LinearGenomeView(\n"
            '    assembly=hg19["assemblies"][0],\n'
            '    aggregate_text_search_adapters=hg19["aggregateTextSearchAdapters"],\n'
            '    location="BRCA1",\n'
            ")\n"
            'view.observe(on_location, "location")\n'
            "view  # pan or zoom — the depth track recomputes for the new window"
        ),
        new_markdown_cell(
            "Driving `location` from code fires the same observer, so the track "
            "recomputes for the new window. Zooming out widens the bins; zooming "
            "in sharpens them — the resolution follows the view:"
        ),
        new_code_cell(
            'view.location = "chr17:7,560,000..7,595,000"  # jump to TP53\n'
            'len(view.tracks[0]["adapter"]["features"]), "bins computed for this window"'
        ),
    ],
)

# --- 11 comparative synteny (E. coli all-vs-all) ----------------------------
save(
    "11_synteny_ecoli.ipynb",
    [
        new_markdown_cell(
            "# Compare genomes: four E. coli strains in a linear synteny view\n\n"
            + badge("11_synteny_ecoli.ipynb")
            + "\n\n`JBrowseApp` drives the full app, so a `views=[...]` list can "
            "hold a `LinearSyntenyView` — several genomes stacked, the blocks "
            "each pair shares drawn between the rows. Here are four *E. coli* "
            "strains (K12, Sakai, CFT073, NCTC86) tied together by one "
            "all-vs-all minimap2 alignment, the same data as the "
            "[all-vs-all synteny tutorial](https://jbrowse.org/jb2/docs/tutorials/allvsall_synteny/). "
            "Everything below is hosted, so this cell runs as-is."
        ),
        new_code_cell(install()),
        new_markdown_cell(
            "## Stack the four strains, one all-vs-all track between them\n\n"
            "Each genome is the flat `{name, uri}` shorthand — JBrowse derives the "
            "`.fai`/`.gzi` from the URL. The single "
            "`AllVsAllPAFAdapter` track serves every pair from one PAF, so the "
            "three bands between the four rows are all the same trackId "
            '(`tracks=[["ecoli_ava"]] * 3`, one entry per adjacent pair). '
            "`drawCurves=False` draws straight ribbons; `minAlignmentLength` "
            "hides short noisy blocks."
        ),
        new_code_cell(
            "from jbrowse_anywidget import JBrowseApp\n\n"
            'BASE = "https://jbrowse.org/demos/ecoli_pangenome"\n'
            'STRAINS = ["K12", "Sakai", "CFT073", "NCTC86"]\n\n'
            'assemblies = [{"name": s, "uri": f"{BASE}/{s}.fa.gz"} for s in STRAINS]\n\n'
            "ecoli_ava = {\n"
            '    "type": "SyntenyTrack",\n'
            '    "trackId": "ecoli_ava",\n'
            '    "name": "E. coli all-vs-all (minimap2 PAF)",\n'
            '    "assemblyNames": STRAINS,\n'
            '    "adapter": {\n'
            '        "type": "AllVsAllPAFAdapter",\n'
            '        "assemblyNames": STRAINS,\n'
            '        "pafLocation": {"uri": f"{BASE}/all_vs_all.paf.gz"},\n'
            "    },\n"
            "}\n\n"
            "JBrowseApp(\n"
            "    assemblies=assemblies,\n"
            "    tracks=[ecoli_ava],\n"
            "    views=[\n"
            "        {\n"
            '            "type": "LinearSyntenyView",\n'
            '            "init": {\n'
            '                "views": [{"assembly": s} for s in STRAINS],\n'
            '                "tracks": [["ecoli_ava"]] * 3,  # one band per adjacent pair\n'
            '                "drawCurves": False,\n'
            '                "minAlignmentLength": 10000,\n'
            "            },\n"
            "        }\n"
            "    ],\n"
            ")"
        ),
        new_markdown_cell(
            "The same PAF also opens as a **dotplot** — change the view's `type` "
            'to `"DotplotView"` and give it two panels to see any one pair '
            "whole-genome. A view spec is only ever `{type, init}`, the same "
            "vocabulary JBrowse Web puts in its `?session=spec-…` URLs, so any "
            "view type works without anything being added to this package. To build the PAF from your own genomes "
            "(`minimap2 -c -x asm20 --eqx`) and load per-strain gene tracks "
            "alongside, follow the "
            "[tutorial](https://jbrowse.org/jb2/docs/tutorials/allvsall_synteny/)."
        ),
    ],
)

save(
    "12_large_data.ipynb",
    [
        new_markdown_cell(
            "# Large results: write a file, don't inline a table\n\n"
            + badge("12_large_data.ipynb")
            + "\n\n`add_features` puts every row into the widget's state as JSON. "
            "That is the right thing for a few thousand peaks, and the wrong "
            "thing by a hundred thousand — the whole table has to be serialized, "
            "pushed through the notebook's comm channel, and held in the "
            "browser's memory whether or not you ever look at it.\n\n"
            "The alternative is what genome browsers have always done: write a "
            "**real indexed file** and read it *by byte range*. `add_local_file` "
            "pushes one from this kernel into the browser, where JBrowse seeks "
            "into it through its index exactly as it would a file on a web "
            "server — but with no server, no CORS, and no public bucket. Only "
            "the bytes for the region on screen are ever touched.\n\n"
            "We'll build a real one: every **NCBI RefSeq exon in the human "
            "genome**, straight from UCSC."
        ),
        new_code_cell(install("pysam pyBigWig")),
        new_markdown_cell(
            "## The analysis\n\n"
            "One download of the RefSeq transcript table, exploded into exons. "
            "This is ordinary pandas — nothing here knows about JBrowse yet."
        ),
        new_code_cell(
            "import numpy as np\n"
            "import pandas as pd\n\n"
            'COLS = ("bin name chrom strand txStart txEnd cdsStart cdsEnd exonCount "\n'
            '        "exonStarts exonEnds score name2 cdsStartStat cdsEndStat exonFrames").split()\n'
            "tx = pd.read_csv(\n"
            '    "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/ncbiRefSeq.txt.gz",\n'
            '    sep="\\t",\n'
            "    names=COLS,\n"
            ")\n"
            'tx = tx[tx.chrom.str.match(r"^chr(\\d+|X|Y)$")]\n\n'
            "# one row per exon\n"
            "exons = pd.DataFrame(\n"
            "    {\n"
            '        "chrom": tx.chrom.str.removeprefix("chr").repeat(tx.exonCount).values,\n'
            '        "start": np.concatenate(\n'
            '            [np.fromstring(s.rstrip(","), sep=",", dtype=np.int64) for s in tx.exonStarts]\n'
            "        ),\n"
            '        "end": np.concatenate(\n'
            '            [np.fromstring(e.rstrip(","), sep=",", dtype=np.int64) for e in tx.exonEnds]\n'
            "        ),\n"
            '        "name": tx.name2.repeat(tx.exonCount).values,\n'
            "    }\n"
            ').sort_values(["chrom", "start"], kind="stable")\n\n'
            'print(f"{len(exons):,} exons")'
        ),
        new_markdown_cell(
            "## What inlining would cost\n\n"
            "`features_track` builds the config `add_features` would send, so we "
            "can price a row before committing to two million of them."
        ),
        new_code_cell(
            "import json\n\n"
            "from jbrowse_anywidget import features_track\n\n"
            'sample = features_track(exons.head(20_000).to_dict("records"), name="sample")\n'
            "per_row = len(json.dumps(sample)) / 20_000\n"
            'print(f"inlined: ~{per_row * len(exons) / 1e6:,.0f} MB of JSON")'
        ),
        new_markdown_cell(
            "Around **200 MB** — through a websocket, into browser memory, to "
            "draw a few hundred exons at a time. Now the same data as a file."
        ),
        new_markdown_cell(
            "## As a tabix file\n\n"
            "BED, bgzipped and indexed — the same pair of files you'd host on a "
            "server. `pysam` writes both.\n\n"
            "`add_local_file` registers the bytes under the file's name and "
            "picks up the `.tbi` sibling automatically. After that the name "
            "**is** the URL: `add_track` infers `BedTabixAdapter` from the "
            "`.bed.gz` extension and finds the index by name, exactly as it "
            "would for a remote file."
        ),
        new_code_cell(
            "import os\n\n"
            "import pysam\n\n"
            'exons.to_csv("exons.bed", sep="\\t", header=False, index=False)\n'
            'pysam.tabix_compress("exons.bed", "exons.bed.gz", force=True)\n'
            'pysam.tabix_index("exons.bed.gz", preset="bed", force=True)\n\n'
            'size = (os.path.getsize("exons.bed.gz") + os.path.getsize("exons.bed.gz.tbi")) / 1e6\n'
            'print(f"tabix: {size:.1f} MB, and the view reads only the part it shows")'
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            'view = LinearGenomeView(assembly="hg38", location="17:7,668,400..7,687,500")\n'
            'view.add_track(view.add_local_file("exons.bed.gz"))\n'
            "view"
        ),
        new_markdown_cell(
            "That's TP53, drawn from a two-million-feature file that never left "
            "this kernel. Pan or zoom and the view fetches the next slice through "
            "the tabix index — the cost of moving is the same as it would be for "
            "a file on a server."
        ),
        new_markdown_cell(
            "## As a bigWig\n\n"
            "For a quantitative signal, bigWig is the better container: it stores "
            "**precomputed zoom levels**, so viewing a whole chromosome reads a "
            "summary rather than every underlying point. Here that's exon density "
            "per 100 kb — a crude gene-density map of the genome."
        ),
        new_code_cell(
            "import pyBigWig\n\n"
            "BIN = 100_000\n"
            'chrom_len = exons.groupby("chrom").end.max()\n'
            'order = [str(c) for c in range(1, 23)] + ["X", "Y"]\n'
            "order = [c for c in order if c in chrom_len.index]\n\n"
            'bw = pyBigWig.open("exon_density.bw", "w")\n'
            "bw.addHeader([(c, int(chrom_len[c]) + BIN) for c in order])\n"
            "for c in order:\n"
            "    binned = (exons.loc[exons.chrom == c, 'start'] // BIN * BIN).value_counts().sort_index()\n"
            "    bw.addEntries(\n"
            "        [c] * len(binned),\n"
            "        binned.index.astype(int).tolist(),\n"
            "        ends=(binned.index + BIN).astype(int).tolist(),\n"
            "        values=binned.values.astype(float).tolist(),\n"
            "    )\n"
            "bw.close()\n"
            'size = os.path.getsize("exon_density.bw") / 1e6\n'
            'print(f"bigWig: {size:.1f} MB, with zoom levels baked in")'
        ),
        new_code_cell(
            'view.add_track(view.add_local_file("exon_density.bw"))\n'
            'view.location = "17"\n'
            "view"
        ),
        new_markdown_cell(
            "## Which to use\n\n"
            "| | `add_features` | `add_local_file` |\n"
            "|---|---|---|\n"
            "| data | a DataFrame or list of dicts | a real file you wrote |\n"
            "| cost | whole table as JSON, always resident | bytes for the visible region |\n"
            "| good to | a few thousand rows | as large as you like |\n"
            "| formats | features only | anything JBrowse reads |\n\n"
            "`add_local_file` is not limited to the two formats above — a "
            "sorted+indexed BAM or CRAM, a bgzipped VCF, a `.hic`, a bigBed all "
            "work the same way, because the browser is opening them with the same "
            "adapters it uses for remote files. Register the index under its "
            "conventional sibling name (`reads.bam` + `reads.bam.bai`) and the "
            "adapter finds it.\n\n"
            "The files here are written to the notebook's working directory; "
            "nothing keeps them afterwards, and nothing was uploaded anywhere."
        ),
    ],
)

save(
    "13_large_wiggle.ipynb",
    [
        new_markdown_cell(
            "# Large signal: three ways to get a wiggle onto the genome\n\n"
            + badge("13_large_wiggle.ipynb")
            + "\n\nCoverage, conservation, methylation, a ChIP fold-change — "
            "quantitative signal is the data type that gets big fastest, because "
            "there's a value for every base or every bin. This notebook lays the "
            "three routes side by side and measures each, so you can pick by "
            "size rather than by guess.\n\n"
            "| | how it travels | good to |\n"
            "|---|---|---|\n"
            "| `add_features` | every point inlined as JSON | ~100k points |\n"
            "| bigWig + `add_local_file` | the file crosses once, then byte ranges | tens of MB |\n"
            "| recompute per region | only what's on screen, every pan | **unlimited** |\n\n"
            "Throughout, `signal` stands in for whatever your pipeline produced — "
            "see [05](05_bam_coverage.ipynb) for real pysam depth and "
            "[06](06_popgen_selection.ipynb) for a real scan."
        ),
        new_code_cell(install("pyBigWig")),
        new_markdown_cell(
            "## The signal\n\n"
            "Binned values along hg38 chr1 — the shape of a coverage track."
        ),
        new_code_cell(
            "import numpy as np\n\n"
            'CHROM, CHROM_LEN = "1", 248_956_422\n'
            "BIN = 100\n"
            "rng = np.random.default_rng(0)\n"
            "starts = np.arange(0, CHROM_LEN - BIN, BIN, dtype=np.int64)\n"
            "signal = rng.gamma(2.0, 3.0, starts.size).astype(np.float32)\n"
            'print(f"{starts.size:,} bins at {BIN}bp across chr1")'
        ),
        new_markdown_cell(
            "## 1. Inline it — `add_features`\n\n"
            "A **`score`** column is what makes this a wiggle rather than boxes: "
            "the track comes back as a `QuantitativeTrack` with a value axis and "
            "autoscaling. (That's JBrowse's own name for the plotted value, so "
            "call the column `score`, not `depth` or `signal`.)\n\n"
            "Every point is serialized into the widget's state, so this is priced "
            "per point — fine for a region, hopeless for a chromosome."
        ),
        new_code_cell(
            "import json\n\n"
            "from jbrowse_anywidget import features_track\n\n\n"
            "def rows(start_arr, value_arr):\n"
            "    return [\n"
            '        {"refName": CHROM, "start": int(s), "end": int(s) + BIN, "score": round(float(v), 2)}\n'
            "        for s, v in zip(start_arr, value_arr)\n"
            "    ]\n\n\n"
            "per_point = len(json.dumps(features_track(rows(starts[:5000], signal[:5000])))) / 5000\n"
            'print(f"inlined: ~{per_point * starts.size / 1e6:,.0f} MB for the whole chromosome")'
        ),
        new_markdown_cell(
            "Too much. But for a **window** it's exactly right — one call, no "
            "file, and it renders as a real wiggle:"
        ),
        new_code_cell(
            "from jbrowse_anywidget import LinearGenomeView\n\n"
            'view = LinearGenomeView(assembly="hg38", location="1:1,000,000..1,200,000")\n'
            "window = (starts >= 1_000_000) & (starts < 1_200_000)\n"
            'view.add_features(rows(starts[window], signal[window]), name="signal (inlined window)")\n'
            "view"
        ),
        new_markdown_cell(
            "## 2. Write a bigWig — `add_local_file`\n\n"
            "bigWig is the format built for this. It stores **precomputed zoom "
            "levels**, so viewing a whole chromosome reads a summary instead of "
            "every underlying point, and it's indexed, so any region is a seek. "
            "`add_local_file` pushes it into the browser once and JBrowse reads "
            "byte ranges out of it — no web server."
        ),
        new_code_cell(
            "import os\n\n"
            "import pyBigWig\n\n"
            'bw = pyBigWig.open("signal.bw", "w")\n'
            "bw.addHeader([(CHROM, CHROM_LEN)])\n"
            "CHUNK = 2_000_000  # addEntries is happier in batches\n"
            "for i in range(0, starts.size, CHUNK):\n"
            "    s = starts[i : i + CHUNK]\n"
            "    bw.addEntries(\n"
            "        [CHROM] * s.size,\n"
            "        s.tolist(),\n"
            "        ends=(s + BIN).tolist(),\n"
            "        values=signal[i : i + CHUNK].astype(float).tolist(),\n"
            "    )\n"
            "bw.close()\n"
            'print(f"bigWig: {os.path.getsize("signal.bw") / 1e6:.0f} MB, zoom levels included")'
        ),
        new_code_cell(
            'view.add_track(view.add_local_file("signal.bw"))\n'
            'view.location = "1"  # whole chromosome: served from a zoom level\n'
            "view"
        ),
        new_markdown_cell(
            "Zoom in and the view switches to the underlying data automatically. "
            "The whole file crossed the comm once, though — at 10 bp bins rather "
            "than 100 this same chromosome is ~200 MB, and a genome is ~3 GB. "
            "That's where this route stops."
        ),
        new_markdown_cell(
            "## 3. Recompute per region\n\n"
            "The observation that removes the ceiling: a wiggle is only ever "
            "drawn at **screen resolution** — a couple of thousand bins across "
            "the view, however much data is underneath. So bin in the kernel for "
            "the visible window only, and the payload stops depending on the "
            "size of the data entirely.\n\n"
            "The data never moves. It can be an array, a zarr store, a database, "
            "a file on a cluster the browser can't reach — anything Python can "
            "slice."
        ),
        new_code_cell(
            "import re\n\n"
            "SCREEN_BINS = 1500\n\n\n"
            "def parse_loc(loc):\n"
            '    m = re.match(r"^\\s*([^:\\s]+)\\s*:\\s*([\\d,]+)\\s*\\.\\.\\s*([\\d,]+)", loc or "")\n'
            '    return (int(m[2].replace(",", "")), int(m[3].replace(",", ""))) if m else None\n\n\n'
            "def render_window(start, end):\n"
            "    # ceiling division, so SCREEN_BINS is a ceiling not a target\n"
            "    step = max(BIN, -(-(end - start) // SCREEN_BINS))\n"
            "    edges = np.arange(start, end, step, dtype=np.int64)\n"
            "    # mean of the underlying bins falling in each screen bin\n"
            "    idx = np.searchsorted(starts, edges)\n"
            "    values = [\n"
            "        float(signal[a:b].mean()) if b > a else 0.0\n"
            "        for a, b in zip(idx, np.r_[idx[1:], idx[-1]])\n"
            "    ]\n"
            "    live.tracks = []  # replace the previous window\n"
            "    live.add_features(\n"
            '        [{"refName": CHROM, "start": int(s), "end": int(s) + step, "score": round(v, 2)}\n'
            "         for s, v in zip(edges, values)],\n"
            '        name="signal (recomputed for this view)",\n'
            '        track_id="live",\n'
            "    )\n\n\n"
            "def on_location(change):\n"
            '    region = parse_loc(change["new"])\n'
            "    if region:\n"
            "        render_window(*region)\n\n\n"
            'live = LinearGenomeView(assembly="hg38", location="1:1,000,000..1,200,000")\n'
            'live.observe(on_location, "location")\n'
            "render_window(1_000_000, 1_200_000)\n"
            "live"
        ),
        new_markdown_cell(
            "Pan or zoom and the kernel rebins for the new window. Each update is "
            "a fixed ~100-200 KB whether the data behind it is a megabyte or a "
            "terabyte:"
        ),
        new_code_cell(
            "for span in (10_000, 1_000_000, CHROM_LEN):\n"
            "    step = max(BIN, span // SCREEN_BINS)\n"
            "    n = min(SCREEN_BINS, span // step)\n"
            "    payload = len(json.dumps(features_track(\n"
            '        [{"refName": CHROM, "start": int(i * step), "end": int((i + 1) * step), "score": 1.23}\n'
            "         for i in range(n)]\n"
            "    )))\n"
            '    print(f"{span:>12,} bp window -> {payload / 1e3:5.0f} KB")'
        ),
        new_markdown_cell(
            "## Choosing\n\n"
            "- **A region you already have in memory** → `add_features` with a "
            "`score` column. One call, no file.\n"
            "- **A whole chromosome or genome you want to browse freely** → write "
            "a bigWig and `add_local_file`. Real zoom levels, real seeking, and "
            "the track keeps working if you later host the file instead.\n"
            "- **Bigger than that, or not a file at all** → recompute per region. "
            "Constant cost, unlimited data, at the price of a round trip on every "
            "pan.\n\n"
            "The three compose: a bigWig for the overview and a recomputed track "
            "for something expensive you only want for the visible window is a "
            "perfectly good pairing."
        ),
    ],
)

print("done")
