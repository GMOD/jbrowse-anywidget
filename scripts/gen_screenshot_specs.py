"""Build the example widgets with the real API and dump their traits to
scripts/screenshot_specs.json, for scripts/screenshot_examples.mjs to render.

Every spec is a single declarative config blob — assemblies are the flat
`{"name", "uri"}` shorthand core expands itself, tracks are bare data-file URIs
or config dicts, views are `{"type", "init"}` — so the screenshots show exactly
what a notebook types, with no Python-side assembly or track building. The one
exception is the bioframe figure, which is the point of `add_features`: a
DataFrame computed in Python becomes a track. Run:
    .venv/bin/python scripts/gen_screenshot_specs.py
"""

import json
import random
from pathlib import Path

import anywidget
import bioframe as bf
import pandas as pd

from jbrowse_anywidget import (
    JBrowseApp,
    LinearGenomeView,
)

# the flat assembly shorthand: core picks the adapter from the extension,
# derives the .fai/.gzi siblings, and builds the reference sequence track
HG38 = {
    "name": "hg38",
    "uri": "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",
    "aliases": ["GRCh38"],
    "refNameAliases": {"uri": "https://jbrowse.org/genomes/GRCh38/hg38_aliases.txt"},
}
REFSEQ_GFF = (
    "https://jbrowse.org/genomes/GRCh38/ncbi_refseq/"
    "GCA_000001405.15_GRCh38_full_analysis_set.refseq_annotation.sorted.gff.gz"
)

VOLVOX = {"name": "volvox", "uri": "https://jbrowse.org/genomes/volvox/volvox.fa.gz"}

VOLVOX_DATA = (
    "https://raw.githubusercontent.com/GMOD/jbrowse-components/main/test_data/volvox/"
)


def traits_of(widget):
    """Every trait the widget itself syncs to JS, read off the widget.

    Derived rather than listed: the harness fakes the anywidget model, so a
    trait missing from the spec reads back as `undefined` in the bundle and the
    render dies — which is exactly what happened when `plugins` was added and
    the hand-written lists here weren't. Scope is our own classes: walk up to
    (not into) AnyWidget, since ipywidgets' inherited `layout`/`tabbable`/
    `tooltip` are not ours and not JSON. anywidget subclasses each instance to
    hold `_esm`/`_css`, hence the underscore filter.
    """
    names = set()
    for cls in type(widget).__mro__:
        if cls is anywidget.AnyWidget:
            break
        names |= set(cls.class_own_traits(sync=True))
    return {
        name: getattr(widget, name)
        for name in sorted(names)
        if not name.startswith("_")
    }


FIXTURES = Path("scripts/fixtures")


def externalize_local_files(traits):
    """Move kernel-local file bytes out of the JSON spec and onto disk.

    `local_files` holds raw bytes, which the spec JSON cannot carry. They are
    written as fixtures instead and named in `localFileUrls`, which the harness
    fetches and hands over as DataViews — the shape anywidget's binary channel
    delivers, so the blob/byte-range path is exercised exactly as in a notebook.
    """
    files = traits.get("local_files")
    if not files:
        return None
    FIXTURES.mkdir(exist_ok=True)
    for name, data in files.items():
        (FIXTURES / name).write_bytes(data)
    traits["local_files"] = {}
    return {name: f"/{FIXTURES}/{name}" for name in files}


def lgv_spec(view, caption):
    traits = traits_of(view)
    spec = {"bundle": "index.js", "caption": caption, "traits": traits}
    urls = externalize_local_files(traits)
    if urls:
        spec["localFileUrls"] = urls
    return spec


def app_spec(app, caption, headed=False):
    return {
        "bundle": "app.js",
        "caption": caption,
        # molstar's 3D canvas needs a real GPU, so this one renders in a window
        "headed": headed,
        "traits": traits_of(app),
    }


def quickstart():
    # a bare data-file URI is a whole track: core infers bigWig from .bw
    return lgv_spec(
        LinearGenomeView(
            assembly=HG38,
            location="10:29,838,565..29,838,850",
            tracks=[
                "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/"
                "hg38.phyloP100way.bw"
            ],
        ),
        "01 · quickstart: an assembly and a bigWig",
    )


def bioframe_track():
    cols = [
        "bin",
        "chrom",
        "start",
        "end",
        "name",
        "length",
        "cpgNum",
        "gcNum",
        "perCpg",
        "perGc",
        "obsExp",
    ]
    islands = pd.read_csv(
        "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/cpgIslandExt.txt.gz",
        sep="\t",
        names=cols,
    )
    islands = islands[islands.chrom == "chr17"].assign(chrom="17")
    shores = bf.merge(bf.subtract(bf.expand(islands, pad=2000), islands))
    view = LinearGenomeView(assembly=HG38, location="17:7,660,000..7,700,000")
    view.add_features(
        islands,
        name="CpG islands (by GC%)",
        color="jexl:get(feature,'perGc') > 65 ? '#00695c' : '#4db6ac'",
    )
    view.add_features(shores, name="CpG shores", color="#f9a825")
    return lgv_spec(view, "02 · bioframe result: CpG islands + shores")


def alignments():
    # the most declarative assembly of all: a hub name the view fetches and
    # resolves (sequence, refName aliases, cytobands) with nothing local
    return lgv_spec(
        LinearGenomeView(
            assembly="hg38",
            location="17:43,044,295..43,048,000",
            tracks=[
                "https://jbrowse.org/genomes/GRCh38/alignments/"
                "NA12878/NA12878.alt_bwamem_GRCh38DH.20150826.CEU.exome.cram"
            ],
        ),
        "03 · GPU-rendered CRAM alignments",
    )


def multisample_variants():
    # a display block is the only non-shorthand part: it presets the band
    # display and colors each sample row by its cohort
    return lgv_spec(
        LinearGenomeView(
            assembly=VOLVOX,
            location="ctgA:1..50,000",
            tracks=[
                {
                    "type": "VariantTrack",
                    "trackId": "sv-band",
                    "name": "multi-sample SV",
                    "adapter": {
                        "type": "VcfTabixAdapter",
                        "uri": VOLVOX_DATA + "volvox.sv.vcf.gz",
                        "samplesTsvLocation": {
                            "uri": VOLVOX_DATA + "volvox.sv.samples.tsv"
                        },
                    },
                    "displays": [
                        {
                            "type": "LinearMultiSampleVariantDisplay",
                            "colorBy": "population",
                        }
                    ],
                }
            ],
        ),
        "04 · multi-sample variants, colored by cohort",
    )


def manhattan():
    return lgv_spec(
        LinearGenomeView(
            assembly="hg19",
            location="2",
            tracks=[
                {
                    "type": "GWASTrack",
                    "trackId": "gwas_track",
                    "name": "GWAS",
                    "adapter": {
                        "type": "GWASAdapter",
                        "scoreColumn": "neg_log_pvalue",
                        "uri": "https://jbrowse.org/genomes/hg19/"
                        "gwas/summary_stats.txt.gz",
                    },
                    "displays": [{"type": "LinearManhattanDisplay", "height": 250}],
                }
            ],
        ),
        "GWAS summary stats as a Manhattan plot",
    )


ECOLI = "https://jbrowse.org/demos/ecoli_pangenome"
STRAINS = ["K12", "Sakai", "CFT073", "NCTC86"]
ECOLI_AVA = {
    "type": "SyntenyTrack",
    "trackId": "ecoli_ava",
    "name": "E. coli all-vs-all (minimap2 PAF)",
    "assemblyNames": STRAINS,
    "adapter": {
        "type": "AllVsAllPAFAdapter",
        "assemblyNames": STRAINS,
        "pafLocation": {"uri": f"{ECOLI}/all_vs_all.paf.gz"},
    },
}


def local_file():
    """A real bgzipped+tabixed file and a bigWig, built here, read in the browser.

    The point is the read path, not the picture: these are BlobLocations, so
    JBrowse seeks into them through their own indexes exactly as it would a
    remote file. Rendering them at all proves the chain — binary trait -> File
    -> BlobFile -> tabix/bigWig seek — works in a real browser, which is the one
    thing jsdom cannot check (its Blob.slice() has no arrayBuffer()).
    """
    import pyBigWig
    import pysam

    FIXTURES.mkdir(exist_ok=True)
    rng = random.Random(0)
    starts = [7_600_000 + i * 100 for i in range(2000)]
    values = [rng.randint(1, 1000) for _ in starts]

    bed = FIXTURES / "peaks.bed"
    with bed.open("w") as fh:
        for i, (start, value) in enumerate(zip(starts, values)):
            fh.write(f"17\t{start}\t{start + 60}\tpeak{i}\t{value}\n")
    pysam.tabix_compress(str(bed), f"{bed}.gz", force=True)
    pysam.tabix_index(f"{bed}.gz", preset="bed", force=True)
    bed.unlink()

    # a much heavier read path: a bigWig is seeked through its own header, chrom
    # B-tree and R-tree index, so rendering one proves the blob is genuinely
    # random-access rather than something read whole
    bw = pyBigWig.open(str(FIXTURES / "signal.bw"), "w")
    bw.addHeader([("17", 83_257_441)])
    bw.addEntries(
        ["17"] * len(starts),
        starts,
        ends=[s + 100 for s in starts],
        values=[float(v) for v in values],
    )
    bw.close()

    view = LinearGenomeView(assembly=HG38, location="17:7,660,000..7,700,000")
    view.add_track(view.add_local_file(f"{bed}.gz"))
    view.add_track(view.add_local_file(FIXTURES / "signal.bw"))
    return lgv_spec(view, "05 · a tabix file and a bigWig built in Python")


def wiggle():
    """An in-memory signal as a real wiggle, not boxes.

    A `score` column makes add_features build a QuantitativeTrack, so an array
    from the kernel gets a value axis and autoscaling. Pinned because
    QuantitativeTrack + FromConfigAdapter is an unusual enough pairing to be
    worth asserting actually drives the wiggle display.
    """
    rng = random.Random(0)
    view = LinearGenomeView(assembly=HG38, location="17:7,660,000..7,700,000")
    view.add_features(
        [
            {
                "refName": "17",
                "start": 7_660_000 + i * 40,
                "end": 7_660_000 + (i + 1) * 40,
                "score": round(rng.gammavariate(2, 3), 2),
            }
            for i in range(1000)
        ],
        name="signal from a numpy array",
    )
    return lgv_spec(view, "06 · an in-memory signal as a real wiggle")


def ecoli_app(views):
    return JBrowseApp(
        assemblies=[{"name": s, "uri": f"{ECOLI}/{s}.fa.gz"} for s in STRAINS],
        tracks=[ECOLI_AVA],
        views=views,
    )


def synteny():
    return app_spec(
        ecoli_app(
            [
                {
                    "type": "LinearSyntenyView",
                    "init": {
                        # one panel per strain, one band per adjacent pair
                        "views": [{"assembly": s} for s in STRAINS],
                        "tracks": [["ecoli_ava"]] * 3,
                        "drawCurves": False,
                        "minAlignmentLength": 10000,
                    },
                }
            ]
        ),
        "11 · synteny: four E. coli strains (JBrowseApp)",
    )


def dotplot():
    return app_spec(
        ecoli_app(
            [
                {
                    "type": "DotplotView",
                    "init": {
                        "views": [{"assembly": s} for s in STRAINS[:2]],
                        "tracks": ["ecoli_ava"],
                    },
                }
            ]
        ),
        "the same alignment as a dotplot",
    )


specs = {
    "01_quickstart": quickstart(),
    "02_bioframe": bioframe_track(),
    "03_alignments": alignments(),
    "04_variants": multisample_variants(),
    "05_local_file": local_file(),
    "06_wiggle": wiggle(),
    "11_synteny": synteny(),
    "12_dotplot": dotplot(),
    "13_manhattan": manhattan(),
}
out = Path(__file__).resolve().parent / "screenshot_specs.json"
with out.open("w") as f:
    json.dump(specs, f, indent=2)
print(f"wrote {out}:", ", ".join(specs))
