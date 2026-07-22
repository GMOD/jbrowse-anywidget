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

import bioframe as bf
import pandas as pd

from jbrowse_anywidget import (
    JBrowseApp,
    LinearGenomeView,
    dotplot_view,
    synteny_view,
)

# the flat assembly shorthand: core picks the adapter from the extension,
# derives the .fai/.gzi siblings, and builds the reference sequence track
HG38 = {
    "name": "hg38",
    "uri": "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",
    "aliases": ["GRCh38"],
    "refNameAliases": {"uri": "https://jbrowse.org/genomes/GRCh38/hg38_aliases.txt"},
}
HG19 = {
    "name": "hg19",
    "uri": "https://jbrowse.org/genomes/hg19/fasta/hg19.fa.gz",
    "refNameAliases": {
        "uri": "https://jbrowse.org/genomes/hg19/hg19_aliases.txt"
    },
}
VOLVOX = {"name": "volvox", "uri": "https://jbrowse.org/genomes/volvox/volvox.fa.gz"}

VOLVOX_DATA = (
    "https://raw.githubusercontent.com/GMOD/jbrowse-components/main/test_data/volvox/"
)


def lgv_spec(view, caption):
    return {
        "bundle": "index.js",
        "caption": caption,
        "traits": {
            "assembly": view.assembly,
            "tracks": view.tracks,
            "default_session": view.default_session,
            "location": view.location,
            "aggregate_text_search_adapters": view.aggregate_text_search_adapters,
            "plugins": view.plugins,
            "selected_feature": None,
        },
    }


def app_spec(app, caption):
    return {
        "bundle": "app.js",
        "caption": caption,
        "traits": {
            "assemblies": app.assemblies,
            "tracks": app.tracks,
            "views": app.views,
            "plugins": app.plugins,
            "view_locations": [],
            "selected_feature": None,
        },
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
    cols = "bin chrom start end name length cpgNum gcNum perCpg perGc obsExp".split()
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
            assembly=HG19,
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
                synteny_view(
                    STRAINS,
                    tracks=[["ecoli_ava"]] * 3,
                    drawCurves=False,
                    minAlignmentLength=10000,
                )
            ]
        ),
        "11 · synteny: four E. coli strains (JBrowseApp)",
    )


def dotplot():
    return app_spec(
        ecoli_app([dotplot_view(STRAINS[:2], tracks=["ecoli_ava"])]),
        "the same alignment as a dotplot",
    )


specs = {
    "01_quickstart": quickstart(),
    "02_bioframe": bioframe_track(),
    "03_alignments": alignments(),
    "04_variants": multisample_variants(),
    "11_synteny": synteny(),
    "12_dotplot": dotplot(),
    "13_manhattan": manhattan(),
}
with open("scripts/screenshot_specs.json", "w") as f:
    json.dump(specs, f, indent=2)
print("wrote scripts/screenshot_specs.json:", ", ".join(specs))
