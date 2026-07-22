"""Tests for the declarative multi-view helpers used with JBrowseApp."""

from jbrowse_anywidget import (
    JBrowseApp,
    dotplot_view,
    linear_view,
    protein_view,
    synteny_track,
    synteny_view,
    view,
)


def test_view_assembles_a_generic_type_init_spec():
    assert view("CircularView", assembly="hg19", tracks=["pairs"]) == {
        "type": "CircularView",
        "init": {"assembly": "hg19", "tracks": ["pairs"]},
    }


def test_view_drops_unset_init_fields():
    assert view("LinearGenomeView", assembly="hg38", loc=None)["init"] == {
        "assembly": "hg38"
    }


def test_protein_view_carries_only_what_was_set():
    spec = protein_view(uniprot_id="P04637", transcript_id="NM_000546.6")
    assert spec == {
        "type": "ProteinView",
        "init": {"uniprotId": "P04637", "transcriptId": "NM_000546.6"},
    }


def test_linear_view_builds_a_type_init_spec():
    assert linear_view("hg38", loc="chr1:1-1000", tracks=["genes"]) == {
        "type": "LinearGenomeView",
        "init": {"assembly": "hg38", "loc": "chr1:1-1000", "tracks": ["genes"]},
    }


def test_linear_view_extra_kwargs_ride_onto_init():
    spec = linear_view("hg38", colorByCDS=True)
    assert spec["init"] == {"assembly": "hg38", "colorByCDS": True}


def test_synteny_view_expands_assembly_names_into_panels():
    assert synteny_view(["hg38", "mm39"], tracks=["paf"], cigar_mode="full") == {
        "type": "LinearSyntenyView",
        "init": {
            "views": [{"assembly": "hg38"}, {"assembly": "mm39"}],
            "tracks": ["paf"],
            "cigarMode": "full",
        },
    }


def test_synteny_view_accepts_panel_dicts_with_loc():
    spec = synteny_view(
        [{"assembly": "hg38", "loc": "chr1"}, {"assembly": "mm39", "loc": "chr1"}]
    )
    assert spec["init"]["views"] == [
        {"assembly": "hg38", "loc": "chr1"},
        {"assembly": "mm39", "loc": "chr1"},
    ]


def test_dotplot_view_builds_a_dotplot_spec():
    assert dotplot_view(["a", "b"], tracks=["paf"])["type"] == "DotplotView"


def test_synteny_track_builds_a_paf_config():
    track = synteny_track("data/hg38_mm39.paf", "hg38", "mm39", name="hg38 vs mm39")
    assert track == {
        "type": "SyntenyTrack",
        "trackId": "hg38-vs-mm39",
        "name": "hg38 vs mm39",
        "assemblyNames": ["hg38", "mm39"],
        "adapter": {
            "type": "PAFAdapter",
            "targetAssembly": "hg38",
            "queryAssembly": "mm39",
            "uri": "data/hg38_mm39.paf",
        },
    }


def test_jbrowse_app_stores_declarative_config():
    app = JBrowseApp(
        assemblies=[{"name": "hg38"}, {"name": "mm39"}],
        tracks=[synteny_track("x.paf", "hg38", "mm39")],
        views=[synteny_view(["hg38", "mm39"], tracks=["x-paf"])],
    )
    assert [a["name"] for a in app.assemblies] == ["hg38", "mm39"]
    assert app.views[0]["type"] == "LinearSyntenyView"
