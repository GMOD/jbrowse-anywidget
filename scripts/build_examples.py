"""Regenerate the example notebooks in examples/.

Run: .venv/bin/python scripts/build_examples.py
Each notebook installs from PyPI only when the package isn't already importable,
so it runs unchanged in Colab and executes headless against a local editable
install for verification.
"""

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

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
        new_code_cell(install()),
        new_markdown_cell(
            "## An assembly and a view\n\n"
            "`make_assembly` builds the reference-sequence config for an "
            "indexed (here bgzipped) FASTA. This reference names chromosomes `1`, "
            "`2`, … but the UCSC bigWig below uses `chr1`, `chr2`, …; "
            "`refname_aliases_uri` points at UCSC's alias table so the two line "
            "up. `location` sets the opening region."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly, track\n\n'
            'hg38 = make_assembly(\n'
            '    "hg38",\n'
            '    "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",\n'
            '    aliases=["GRCh38"],\n'
            '    refname_aliases_uri="https://jbrowse.org/genomes/GRCh38/hg38_aliases.txt",\n'
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
            '        "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",\n'
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
            'import bioframe as bf\n'
            'import pandas as pd\n\n'
            'cols = "bin chrom start end name length cpgNum gcNum perCpg perGc obsExp".split()\n'
            'islands = pd.read_csv(\n'
            '    "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/cpgIslandExt.txt.gz",\n'
            '    sep="\\t", names=cols,\n'
            ')\n'
            'islands = islands[islands.chrom == "chr17"].assign(chrom="17")\n'
            'shores = bf.merge(bf.subtract(bf.expand(islands, pad=2000), islands))\n'
            'print(len(islands), "islands ->", len(shores), "shores")\n'
            'shores.head()'
        ),
        new_markdown_cell(
            "## Both on the genome\n\n"
            "One `add_features` per frame. Islands are colored by GC% — a column "
            "that rides along and shows in each feature's details; any column "
            "does. This lands on *TP53*."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, make_assembly\n\n'
            'hg38 = make_assembly(\n'
            '    "hg38",\n'
            '    "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",\n'
            '    aliases=["GRCh38"],\n'
            ')\n'
            'view = LinearGenomeView(assembly=hg38, location="17:7,660,000..7,700,000")\n'
            'view.add_features(\n'
            '    islands, name="CpG islands (by GC%)",\n'
            '    color="jexl:get(feature,\'perGc\') > 65 ? \'#00695c\' : \'#4db6ac\'",\n'
            ')\n'
            'view.add_features(shores, name="CpG shores", color="#f9a825")\n'
            'view'
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
        new_code_cell(install()),
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
            'import numpy as np\n'
            'import pandas as pd\n'
            'import pysam\n\n'
            'BAM = (\n'
            '    "https://s3.amazonaws.com/1000genomes/phase3/data/NA12878/"\n'
            '    "exome_alignment/NA12878.mapped.ILLUMINA.bwa.CEU.exome.20121211.bam"\n'
            ')\n'
            'CHROM, START, END = "17", 41_196_312, 41_277_500  # BRCA1, GRCh37\n\n'
            'bam = pysam.AlignmentFile(BAM)\n'
            'depth = np.array(bam.count_coverage(CHROM, START, END)).sum(0)\n\n'
            'binsize = 100\n'
            'n = depth.size // binsize * binsize\n'
            'binned = depth[:n].reshape(-1, binsize).mean(1).round(1)\n'
            'starts = START + np.arange(binned.size) * binsize\n'
            'coverage = pd.DataFrame(\n'
            '    {"chrom": "chr17", "start": starts, "end": starts + binsize, "depth": binned}\n'
            ')\n'
            'coverage.head()'
        ),
        new_markdown_cell(
            "## See it on hg19, opened at the gene by name\n\n"
            "`fetch_hub(\"hg19\")` brings the genome and a gene-name search index, "
            "so `location=\"BRCA1\"` just works. Exome capture concentrates reads "
            "on the exons — the depth track peaks there and drops between."
        ),
        new_code_cell(
            'from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n'
            'hg19 = fetch_hub("hg19")\n'
            'view = LinearGenomeView(\n'
            '    assembly=hg19["assemblies"][0],\n'
            '    aggregate_text_search_adapters=hg19["aggregateTextSearchAdapters"],\n'
            '    location="BRCA1",\n'
            ')\n'
            'view.add_features(\n'
            '    coverage, name="NA12878 exome depth",\n'
            '    color="jexl:get(feature,\'depth\') > 40 ? \'#c62828\' : get(feature,\'depth\') > 10 ? \'#f9a825\' : \'#cfcfcf\'",\n'
            ')\n'
            'view'
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
            'import numpy as np\n'
            'import pandas as pd\n'
            'from scipy.stats import ttest_ind\n'
            'from statsmodels.stats.multitest import multipletests\n\n'
            'rng = np.random.default_rng(7)\n'
            'n_genes, n_rep = 80, 4\n'
            'starts = 1_000_000 + np.arange(n_genes) * 40_000\n\n'
            'base = rng.uniform(20, 400, n_genes)  # baseline expression per gene\n'
            'true_lfc = np.zeros(n_genes)\n'
            'up = rng.choice(n_genes, 6, replace=False)\n'
            'down = rng.choice(np.setdiff1d(np.arange(n_genes), up), 6, replace=False)\n'
            'true_lfc[up] = rng.uniform(1.5, 3.0, 6)\n'
            'true_lfc[down] = -rng.uniform(1.5, 3.0, 6)\n'
            'ctrl = rng.poisson(base[:, None], size=(n_genes, n_rep))\n'
            'treat = rng.poisson((base * 2.0**true_lfc)[:, None], size=(n_genes, n_rep))\n\n'
            'lc, lt = np.log2(ctrl + 1), np.log2(treat + 1)\n'
            'lfc = lt.mean(1) - lc.mean(1)\n'
            'padj = multipletests(ttest_ind(lt, lc, axis=1, equal_var=False).pvalue,\n'
            '                     method="fdr_bh")[1]\n\n'
            'de = pd.DataFrame(\n'
            '    {\n'
            '        "chrom": "7",\n'
            '        "start": starts,\n'
            '        "end": starts + 6_000,\n'
            '        "name": [f"GENE{i:04d}" for i in range(n_genes)],\n'
            '        "log2fc": lfc.round(2),\n'
            '        "padj": padj.round(4),\n'
            '    }\n'
            ')\n'
            'de["sig"] = np.where(\n'
            '    (de.padj < 0.05) & (de.log2fc.abs() > 1),\n'
            '    np.where(de.log2fc > 0, "up", "down"),\n'
            '    "ns",\n'
            ')\n'
            'de.sort_values("padj").head()'
        ),
        new_markdown_cell(
            "## Load the DE table onto the genome\n\n"
            "Each gene is colored by call; `log2fc`/`padj` ride along and show "
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
        new_code_cell(install()),
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
            '            "uri": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",\n'
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
            '    return pd.DataFrame(\n'
            '        {"chrom": chrom, "start": starts, "end": starts + binsize, "depth": binned}\n'
            "    )\n\n\n"
            'coverage("chr17", 41_196_312, 41_277_500).head()  # BRCA1'
        ),
        new_markdown_cell(
            "## Recompute on every pan\n\n"
            "`on_location` parses the view's locstring and re-renders coverage for "
            "that window. `view.observe(..., \"location\")` fires it whenever the "
            "region changes — dragging in the UI or setting `view.location` from "
            "code. A gene-name or whole-chromosome location doesn't parse, and a "
            "window wider than 5 Mb is skipped to keep each per-pan query snappy."
        ),
        new_code_cell(
            "import re\n\n"
            "from jbrowse_anywidget import LinearGenomeView, fetch_hub\n\n"
            "hg19 = fetch_hub(\"hg19\")\n"
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
            "len(view.tracks[0][\"adapter\"][\"features\"]), \"bins computed for this window\""
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
            "Each genome is a `make_assembly` from its hosted FASTA. The single "
            "`AllVsAllPAFAdapter` track serves every pair from one PAF, so the "
            "three bands between the four rows are all the same trackId "
            "(`tracks=[[\"ecoli_ava\"]] * 3`, one entry per adjacent pair). "
            "`drawCurves=False` draws straight ribbons; `minAlignmentLength` "
            "hides short noisy blocks."
        ),
        new_code_cell(
            "from jbrowse_anywidget import JBrowseApp, make_assembly, synteny_view\n\n"
            'BASE = "https://jbrowse.org/demos/ecoli_pangenome"\n'
            'STRAINS = ["K12", "Sakai", "CFT073", "NCTC86"]\n\n'
            "assemblies = [make_assembly(s, f\"{BASE}/{s}.fa.gz\") for s in STRAINS]\n\n"
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
            "        synteny_view(\n"
            "            STRAINS,\n"
            '            tracks=[["ecoli_ava"]] * 3,  # one band per adjacent pair\n'
            "            drawCurves=False,\n"
            "            minAlignmentLength=10000,\n"
            "        )\n"
            "    ],\n"
            ")"
        ),
        new_markdown_cell(
            "The same PAF also opens as a **dotplot** — swap `synteny_view` for "
            "`dotplot_view([\"K12\", \"Sakai\"], tracks=[\"ecoli_ava\"])` to see "
            "any one pair whole-genome. To build the PAF from your own genomes "
            "(`minimap2 -c -x asm20 --eqx`) and load per-strain gene tracks "
            "alongside, follow the "
            "[tutorial](https://jbrowse.org/jb2/docs/tutorials/allvsall_synteny/)."
        ),
    ],
)

print("done")
