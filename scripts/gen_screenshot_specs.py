"""Build a few example widgets with the real API and dump their traits to
scripts/screenshot_specs.json, for scripts/screenshot_examples.mjs to render.

Using the actual jbrowse_anywidget API (not hand-written config) keeps the
screenshots faithful to what the notebooks produce. Run:
    .venv/bin/python scripts/gen_screenshot_specs.py
"""

import json

import bioframe as bf
import pandas as pd

from jbrowse_anywidget import (
    JBrowseApp,
    LinearGenomeView,
    make_assembly,
    synteny_view,
)

HG38 = make_assembly(
    "hg38",
    "https://jbrowse.org/genomes/GRCh38/fasta/hg38.prefix.fa.gz",
    aliases=["GRCh38"],
    refname_aliases_uri="https://jbrowse.org/genomes/GRCh38/hg38_aliases.txt",
)


def lgv_spec(bundle, view, caption):
    return {
        "bundle": bundle,
        "caption": caption,
        "traits": {
            "assembly": view.assembly,
            "tracks": view.tracks,
            "default_session": view.default_session,
            "location": view.location,
            "aggregate_text_search_adapters": view.aggregate_text_search_adapters,
            "selected_feature": None,
        },
    }


def quickstart():
    view = LinearGenomeView(assembly=HG38, location="10:29,838,565..29,838,850")
    view.add_track(
        {
            "type": "QuantitativeTrack",
            "trackId": "phyloP100way",
            "name": "phyloP100way",
            "adapter": {
                "type": "BigWigAdapter",
                "uri": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",
            },
        }
    )
    return lgv_spec("index.js", view, "01 · quickstart: an assembly and a bigWig")


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
    return lgv_spec("index.js", view, "02 · bioframe result: CpG islands + shores")


def synteny():
    base = "https://jbrowse.org/demos/ecoli_pangenome"
    strains = ["K12", "Sakai", "CFT073", "NCTC86"]
    assemblies = [make_assembly(s, f"{base}/{s}.fa.gz") for s in strains]
    ava = {
        "type": "SyntenyTrack",
        "trackId": "ecoli_ava",
        "name": "E. coli all-vs-all (minimap2 PAF)",
        "assemblyNames": strains,
        "adapter": {
            "type": "AllVsAllPAFAdapter",
            "assemblyNames": strains,
            "pafLocation": {"uri": f"{base}/all_vs_all.paf.gz"},
        },
    }
    app = JBrowseApp(
        assemblies=assemblies,
        tracks=[ava],
        views=[
            synteny_view(
                strains,
                tracks=[["ecoli_ava"]] * 3,
                drawCurves=False,
                minAlignmentLength=10000,
            )
        ],
    )
    return {
        "bundle": "app.js",
        "caption": "11 · synteny: four E. coli strains (JBrowseApp)",
        "traits": {
            "assemblies": app.assemblies,
            "tracks": app.tracks,
            "views": app.views,
            "view_locations": [],
            "selected_feature": None,
        },
    }


specs = {
    "01_quickstart": quickstart(),
    "02_bioframe": bioframe_track(),
    "11_synteny": synteny(),
}
with open("scripts/screenshot_specs.json", "w") as f:
    json.dump(specs, f, indent=2)
print("wrote scripts/screenshot_specs.json:", ", ".join(specs))
